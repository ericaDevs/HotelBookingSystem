from django.shortcuts import render
from Properties.models import Rooms

# Create your views here.
def home(request):
    rooms = Rooms.objects.filter(is_available=True).order_by('room_number')
    return render(request, 'index.html', {'rooms': rooms})

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contacts.html')