import os
import django
import uuid

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ctf_challenge.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Workspace, WorkspaceMembership, Spreadsheet, SpreadsheetCell

User = get_user_model()

def run():
    print("Seeding MegaCorp data...")

    # 1. Create MegaCorp Admin User
    megacorp_admin, created_admin = User.objects.get_or_create(
        username="jane.doe",
        defaults={'email': 'jane.doe@megacorp.com', 'is_staff': False, 'is_superuser': False}
    )
    if created_admin:
        megacorp_admin.set_password("aVerySecurePassword123!")
        megacorp_admin.save()
        print(f"Created MegaCorp admin: {megacorp_admin.username}")

    # 2. Create MegaCorp Intern User (for the invitation leak)
    megacorp_intern, created_intern = User.objects.get_or_create(
        username="new.intern",
        defaults={'email': 'new.intern@megacorp.com'}
    )
    if created_intern:
        megacorp_intern.set_password("password")
        megacorp_intern.save()
        print(f"Created MegaCorp intern: {megacorp_intern.username}")


    # 3. Create MegaCorp Workspace
    megacorp_workspace, created_ws = Workspace.objects.get_or_create(
        name="MegaCorp Official",
        defaults={'owner': megacorp_admin}
    )
    if created_ws:
        print(f"Created MegaCorp workspace: {megacorp_workspace.name} (ID: {megacorp_workspace.id})")

    # 4. Add Admin and Intern as members
    WorkspaceMembership.objects.get_or_create(
        user=megacorp_admin,
        workspace=megacorp_workspace,
        defaults={'role': WorkspaceMembership.Role.ADMIN}
    )
    WorkspaceMembership.objects.get_or_create(
        user=megacorp_intern,
        workspace=megacorp_workspace,
        defaults={'role': WorkspaceMembership.Role.VIEWER}
    )
    print("Added members to MegaCorp workspace.")

    # 5. Create the target spreadsheet
    financials_sheet, created_sheet = Spreadsheet.objects.get_or_create(
        workspace=megacorp_workspace,
        name="Financials Q4",
        defaults={'flag': 'flag{GraphQL_And_Race_Conditions_Are_A_Toxic_Mix}'}
    )
    if created_sheet:
        print(f"Created target spreadsheet: {financials_sheet.name} (ID: {financials_sheet.id})")

    # 6. Add some dummy data to the spreadsheet
    SpreadsheetCell.objects.get_or_create(spreadsheet=financials_sheet, row=0, column=0, defaults={'content': 'Revenue'})
    SpreadsheetCell.objects.get_or_create(spreadsheet=financials_sheet, row=0, column=1, defaults={'content': '1,000,000'})
    SpreadsheetCell.objects.get_or_create(spreadsheet=financials_sheet, row=1, column=0, defaults={'content': 'Profit'})
    SpreadsheetCell.objects.get_or_create(spreadsheet=financials_sheet, row=1, column=1, defaults={'content': '250,000'})
    SpreadsheetCell.objects.get_or_create(spreadsheet=financials_sheet, row=31, column=5, defaults={'content': 'flag{GraphQL_And_Race_Conditions_Are_A_Toxic_Mix}'}) # The flag location (F32)

    print("\nMegaCorp data seeding complete!")
    print(f"Target Sheet Name: {financials_sheet.name}")
    print(f"Target Sheet UUID (for reference): {financials_sheet.id}")
    print(f"Target Admin Email: {megacorp_admin.email}")
    print(f"Target Intern Email: {megacorp_intern.email}")

if __name__ == '__main__':
    run()

