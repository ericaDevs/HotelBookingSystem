from django.urls import path
from . import views

urlpatterns = [
    path('', views.gallery, name='gallery'),
    path('rooms/<int:id>/', views.room_details, name='room_details'),
    path('rooms/', views.rooms, name='rooms')
]