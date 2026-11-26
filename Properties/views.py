from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Rooms
from Reservations.availability import add_current_availability

# Create your views here.
def gallery(request):
    return render(request, 'gallery.html')

def rooms(request):
    room_list = add_current_availability(
        Rooms.objects
        .prefetch_related('images')
        .order_by('room_number'),
        timezone.localdate(),
    )
    room_types = Rooms.objects.order_by().values_list(
        'room_type', flat=True
    ).distinct().order_by('room_type')
    return render(request, 'rooms.html', {
        'rooms': room_list,
        'room_types': room_types,
    })
    
    

def room_details(request, id):
    room = get_object_or_404(
        Rooms.objects.prefetch_related('images'),
        pk=id,
    )
    room = add_current_availability([room], timezone.localdate())[0]
    related_rooms = add_current_availability(
        Rooms.objects.exclude(id=room.id)
        .prefetch_related('images')
        .order_by('-id')[:3],
        timezone.localdate(),
    )
    return render(request, 'room_details.html', {
        'room': room,
        'related_rooms': related_rooms,
    })