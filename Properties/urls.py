from django.urls import path
from . import views

urlpatterns = [
    path('', views.gallery, name='gallery'),
    path('<id:id>/', views.room_details, name = 'per_room'),
    path('rooms/', views.rooms, name='rooms')
]