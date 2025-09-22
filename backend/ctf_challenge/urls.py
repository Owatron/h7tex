from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from core.views import internal_graphql_view, data_export_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # Public GraphQL endpoint
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    # Internal-only GraphQL endpoint for the SSRF challenge
    path("internal-graphql", csrf_exempt(internal_graphql_view)),
    # Data export endpoint for the IDOR/leak challenge
    path("export/<uuid:workspace_id>", data_export_view, name="data_export"),
]

