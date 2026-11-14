from django.urls import path
from django.views.generic import TemplateView

app_name = 'dashboard'

urlpatterns = [
    path(
        'admin/',
        TemplateView.as_view(template_name='admin/overview.html'),
        name='admin_overview',
    ),
    path(
        'agent/',
        TemplateView.as_view(template_name='agent/overview.html'),
        name='agent_overview',
    ),
]
