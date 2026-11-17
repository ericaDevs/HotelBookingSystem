from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('login/', views.staff_login, name='login'),
    path('overview/', views.staff_dashboard, name='dashboard'),
]
