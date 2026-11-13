from django.shortcuts import render
from .models import Rooms

# Create your views here.
def gallery(request):
    return render(request, 'gallery.html')

def rooms(request):
    available_rooms = Rooms.objects.filter(is_available=True).order_by('room_number')
    room_types = available_rooms.order_by().values_list(
        'room_type', flat=True
    ).distinct().order_by('room_type')
    return render(request, 'rooms.html', {
        'rooms': available_rooms,
        'room_types': room_types,
    })