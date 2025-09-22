from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Workspace, Spreadsheet, SpreadsheetCell
from ctf_challenge.schema import schema
from graphql.execution import execute
import json
import re
import zipfile
import io

@csrf_exempt
def internal_graphql_view(request):
    """
    VULNERABILITY 2 TARGET: An internal-only GraphQL endpoint that bypasses
    all user-level permission checks. The SSRF will target this.
    """
    if request.method == 'GET':
        query = request.GET.get('query', '')
    elif request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '')
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # We execute the query with a blank context, bypassing all authentication
    # and permission checks that rely on info.context.user
    result = schema.execute(query)

    response_data = {'data': result.data}
    if result.errors:
        response_data['errors'] = [str(e) for e in result.errors]

    return JsonResponse(response_data)

@login_required
def data_export_view(request, workspace_id):
    """
    VULNERABILITY 1: Leaky Data Export
    This view generates a zip file of workspace data but leaks referenced
    spreadsheet UUIDs from other tenants in a metadata log file.
    """
    user = request.user
    try:
        workspace = Workspace.objects.get(id=workspace_id, members=user)
    except Workspace.DoesNotExist:
        return HttpResponse("Workspace not found or access denied.", status=403)

    spreadsheets = Spreadsheet.objects.filter(workspace=workspace)
    export_log = []

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for sheet in spreadsheets:
            sheet_data = f"Spreadsheet Name: {sheet.name}\n\n"
            cells = SpreadsheetCell.objects.filter(spreadsheet=sheet).order_by('row', 'column')
            for cell in cells:
                sheet_data += f"Cell ({cell.row},{cell.column}): {cell.content}\n"
                
                # Check for cross-sheet references
                match = re.search(r"=\['?(.*?)'?\]", cell.content)
                if match:
                    referenced_name = match.group(1)
                    # The vulnerability: it resolves the name globally, not just within the tenant.
                    referenced_sheet = Spreadsheet.objects.filter(name__iexact=referenced_name).first()
                    log_entry = {
                        "timestamp": "...",
                        "source_doc_id": str(sheet.id),
                        "source_doc_name": sheet.name,
                        "referenced_name": referenced_name,
                        "status": "NOT_FOUND"
                    }
                    if referenced_sheet:
                        # Even if access is denied, we log the resolved UUID. This is the leak.
                        log_entry["referenced_doc_id"] = str(referenced_sheet.id)
                        log_entry["status"] = "ACCESS_DENIED" if referenced_sheet.workspace != workspace else "OK"
                    
                    export_log.append(log_entry)

            zip_file.writestr(f"{sheet.name.replace(' ', '_')}.txt", sheet_data)
        
        # Add the leaky log file to the zip
        zip_file.writestr("export_log.json", json.dumps(export_log, indent=2))

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response['Content-Disposition'] = f'attachment; filename=export_{workspace.name}.zip'
    return response

