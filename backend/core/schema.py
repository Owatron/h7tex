import graphene
import graphql_jwt
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model
from .models import Workspace, WorkspaceMembership, Spreadsheet, SpreadsheetCell, Invitation
import re
import requests
import json
import time

# --- Object Types ---

class UserType(DjangoObjectType):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email')

class WorkspaceType(DjangoObjectType):
    class Meta:
        model = Workspace
        fields = ('id', 'name', 'owner', 'members', 'spreadsheets')

class SpreadsheetType(DjangoObjectType):
    class Meta:
        model = Spreadsheet
        fields = ('id', 'name', 'workspace', 'cells', 'flag')
    
    def resolve_flag(self, info):
        # Only admins of the workspace can see the flag.
        user = info.context.user
        if not user.is_authenticated:
            return None
        try:
            membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=user)
            if membership.role == WorkspaceMembership.Role.ADMIN:
                return self.flag
        except WorkspaceMembership.DoesNotExist:
            pass
        return None

class SpreadsheetCellType(DjangoObjectType):
    evaluated_content = graphene.String()

    class Meta:
        model = SpreadsheetCell
        fields = ('id', 'row', 'column', 'content')
    
    def resolve_evaluated_content(self, info):
        # VULNERABILITY 2: SSRF in IMPORT_CSV
        # This function is where the SSRF vulnerability is introduced.
        if self.content.startswith('=IMPORT_CSV("') and self.content.endswith('")'):
            url_match = re.search(r'"(.*?)"', self.content)
            if url_match:
                url = url_match.group(1)
                try:
                    # No validation on the URL, allowing internal network requests
                    response = requests.get(url, timeout=3)
                    if response.status_code == 200:
                        return response.text[:500] # Truncate for display
                    else:
                        return f"#ERROR: Status {response.status_code}"
                except requests.RequestException as e:
                    return f"#ERROR: {str(e)}"
        
        # Non-vulnerable formula examples
        if self.content.startswith('=SUM('):
            return "#SUM_RESULT"
        if self.content.startswith('=AVERAGE('):
            return "#AVG_RESULT"

        return self.content

# --- Queries ---

class Query(graphene.ObjectType):
    current_user = graphene.Field(UserType)
    workspace_by_id = graphene.Field(WorkspaceType, id=graphene.UUID())
    spreadsheet_by_id = graphene.Field(SpreadsheetType, id=graphene.UUID())

    def resolve_current_user(self, info):
        user = info.context.user
        if user.is_authenticated:
            return user
        return None

    def resolve_workspace_by_id(self, info, id):
        user = info.context.user
        if not user.is_authenticated:
            return None
        return Workspace.objects.filter(members=user, id=id).first()

    def resolve_spreadsheet_by_id(self, info, id):
        user = info.context.user
        if not user.is_authenticated:
            return None
        spreadsheet = Spreadsheet.objects.filter(id=id).first()
        if spreadsheet and WorkspaceMembership.objects.filter(workspace=spreadsheet.workspace, user=user).exists():
            return spreadsheet
        return None

# --- Mutations ---

class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)
    token = graphene.String()

    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        email = graphene.String(required=True)

    def mutate(self, info, username, password, email):
        user = get_user_model().objects.create_user(
            username=username,
            email=email,
            password=password
        )
        # Create a personal workspace for the new user
        workspace = Workspace.objects.create(name=f"{username}'s Workspace", owner=user)
        WorkspaceMembership.objects.create(user=user, workspace=workspace, role=WorkspaceMembership.Role.ADMIN)
        
        # Get JWT token
        token = graphql_jwt.ObtainJSONWebToken.as_view()(info.context).data.get('token')

        return CreateUser(user=user, token=token)


class CreateWorkspace(graphene.Mutation):
    workspace = graphene.Field(WorkspaceType)

    class Arguments:
        name = graphene.String(required=True)

    def mutate(self, info, name):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        workspace = Workspace.objects.create(name=name, owner=user)
        WorkspaceMembership.objects.create(user=user, workspace=workspace, role=WorkspaceMembership.Role.ADMIN)
        return CreateWorkspace(workspace=workspace)


class CreateSpreadsheet(graphene.Mutation):
    spreadsheet = graphene.Field(SpreadsheetType)

    class Arguments:
        workspace_id = graphene.UUID(required=True)
        name = graphene.String(required=True)
    
    def mutate(self, info, workspace_id, name):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")

        try:
            membership = WorkspaceMembership.objects.get(user=user, workspace_id=workspace_id)
            if membership.role not in [WorkspaceMembership.Role.ADMIN, WorkspaceMembership.Role.EDITOR]:
                raise Exception("You don't have permission to create spreadsheets in this workspace.")
        except WorkspaceMembership.DoesNotExist:
            raise Exception("You are not a member of this workspace.")
        
        workspace = membership.workspace
        spreadsheet = Spreadsheet.objects.create(workspace=workspace, name=name)
        return CreateSpreadsheet(spreadsheet=spreadsheet)

class UpdateCell(graphene.Mutation):
    cell = graphene.Field(SpreadsheetCellType)

    class Arguments:
        spreadsheet_id = graphene.UUID(required=True)
        row = graphene.Int(required=True)
        column = graphene.Int(required=True)
        content = graphene.String(required=True)

    def mutate(self, info, spreadsheet_id, row, column, content):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        spreadsheet = Spreadsheet.objects.get(id=spreadsheet_id)
        try:
            membership = WorkspaceMembership.objects.get(user=user, workspace=spreadsheet.workspace)
            if membership.role not in [WorkspaceMembership.Role.ADMIN, WorkspaceMembership.Role.EDITOR]:
                raise Exception("You don't have permission to edit this spreadsheet.")
        except WorkspaceMembership.DoesNotExist:
            raise Exception("You are not a member of this workspace.")

        cell, created = SpreadsheetCell.objects.update_or_create(
            spreadsheet=spreadsheet,
            row=row,
            column=column,
            defaults={'content': content}
        )
        return UpdateCell(cell=cell)

class InviteUser(graphene.Mutation):
    invitation = graphene.Field(lambda: InvitationType)

    class Arguments:
        workspace_id = graphene.UUID(required=True)
        email = graphene.String(required=True)
        role = graphene.String(required=True)

    def mutate(self, info, workspace_id, email, role):
        inviter = info.context.user
        if not inviter.is_authenticated:
            raise Exception("Authentication required")

        try:
            membership = WorkspaceMembership.objects.get(user=inviter, workspace_id=workspace_id)
            if membership.role != WorkspaceMembership.Role.ADMIN:
                raise Exception("Only admins can invite users.")
        except WorkspaceMembership.DoesNotExist:
            raise Exception("You are not a member of this workspace.")
            
        # VULNERABILITY 3 (PART A): Information Leak
        # If the user is already a member, don't fail. Instead, leak their original invitation ID.
        # This is the entry point to the race condition attack.
        target_user = get_user_model().objects.filter(email=email).first()
        if target_user and WorkspaceMembership.objects.filter(user=target_user, workspace_id=workspace_id).exists():
             # Find the invitation that was accepted by this user for this workspace.
            original_invitation = Invitation.objects.filter(
                email=email, 
                workspace_id=workspace_id, 
                status=Invitation.Status.ACCEPTED
            ).first()
            if original_invitation:
                # Instead of a clean error, we leak the ID.
                raise Exception(f"User is already a member. Original invitation ID: {original_invitation.id}")

        invitation = Invitation.objects.create(
            workspace_id=workspace_id,
            email=email,
            role=role,
            inviter=inviter,
        )
        return InviteUser(invitation=invitation)


class UpdateInvitation(graphene.Mutation):
    # This mutation is part of the vulnerability chain.
    success = graphene.Boolean()

    class Arguments:
        invitation_id = graphene.UUID(required=True)
        new_role = graphene.String(required=True)
        # Undocumented parameter for the attacker to use
        new_email = graphene.String() 

    def mutate(self, info, invitation_id, new_role, new_email=None):
        # VULNERABILITY 3 (PART B): Broken Authorization + Race Condition
        # This logic is deliberately flawed. It checks for the invitation's existence
        # but fails to re-verify that the CALLER has permissions on the INVITATION'S workspace.
        # An attacker can call this with an ID they leaked from another tenant's workspace.
        
        try:
            invitation = Invitation.objects.get(id=invitation_id, status=Invitation.Status.PENDING)
        except Invitation.DoesNotExist:
            raise Exception("Invitation not found or already actioned.")

        # Artificial delay to make the race condition easier to hit in a CTF context.
        time.sleep(1) 

        invitation.role = new_role
        if new_email:
            invitation.email = new_email
        
        invitation.save()

        return UpdateInvitation(success=True)


class AcceptInvitation(graphene.Mutation):
    workspace_membership = graphene.Field(lambda: WorkspaceMembershipType)

    class Arguments:
        invitation_id = graphene.UUID(required=True)

    def mutate(self, info, invitation_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("You must be logged in to accept an invitation.")
        
        try:
            invitation = Invitation.objects.get(id=invitation_id, email=user.email, status=Invitation.Status.PENDING)
        except Invitation.DoesNotExist:
            raise Exception("Invalid or expired invitation.")

        membership, created = WorkspaceMembership.objects.get_or_create(
            user=user,
            workspace=invitation.workspace,
            defaults={'role': invitation.role}
        )

        invitation.status = Invitation.Status.ACCEPTED
        invitation.save()

        return AcceptInvitation(workspace_membership=membership)


class InvitationType(DjangoObjectType):
    class Meta:
        model = Invitation

class WorkspaceMembershipType(DjangoObjectType):
    class Meta:
        model = WorkspaceMembership


class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    
    create_workspace = CreateWorkspace.Field()
    create_spreadsheet = CreateSpreadsheet.Field()
    update_cell = UpdateCell.Field()
    invite_user = InviteUser.Field()
    update_invitation = UpdateInvitation.Field() # Vulnerable mutation
    accept_invitation = AcceptInvitation.Field()

