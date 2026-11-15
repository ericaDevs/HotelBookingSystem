from django.urls import path
from . import views

app_name = 'admin_portal'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('dashboard/', views.admin_dashboard, name='dashboard'),
]
