from django.urls import path
from . import views

app_name = 'admin_portal'

urlpatterns = [
    path('', views.admin_login, name='login'),
    path('overview/', views.overview, name='overview'),
    path('dashboard/', views.overview, name='dashboard'),
    path('reservations/', views.reservation_management, name='reservations'),
    path('rooms/', views.room_management, name='rooms'),
    path('staff/', views.team_management, name='staff'),
    path('revenue/', views.revenue_management, name='revenue'),
]
