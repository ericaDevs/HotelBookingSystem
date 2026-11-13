from django.http import Http404
from django.shortcuts import get_object_or_404, render
from Properties.models import Rooms

# Create your views here.
def bookings(request):
    rooms = Rooms.objects.filter(is_available=True).order_by('room_number')
    selected_room = None
    room_id = request.GET.get('room')
    if room_id:
        if not room_id.isdecimal():
            raise Http404
        selected_room = get_object_or_404(rooms, pk=int(room_id))

    return render(request, 'bookings.html', {
        'rooms': rooms,
        'selected_room': selected_room,
    })