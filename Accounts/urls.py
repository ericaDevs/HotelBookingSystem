from django.urls import path
from django.views.generic import TemplateView

app_name = 'accounts'

urlpatterns = [
    path(
        'admin/login/',
        TemplateView.as_view(template_name='accounts/admin_login.html'),
        name='admin_login',
    ),
    path(
        'agent/login/',
        TemplateView.as_view(template_name='accounts/agent_login.html'),
        name='agent_login',
    ),
]
