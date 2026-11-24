from django.shortcuts import render, get_object_or_404
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
    
    

def room_details(id, request):
    room = get_object_or_404(Rooms, id=id)
    related_rooms = Rooms.objects.exclude(id=room.id).order_by('-id')[:3]
    return render(request, 'room_details.html', {
        'room': room,
        'related_rooms': related_rooms,
    })