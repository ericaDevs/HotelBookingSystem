from django.shortcuts import render
from django.utils import timezone
from Properties.models import Rooms
from Reservations.availability import add_current_availability
from Admin.models import Contacts


# Create your views here.
def home(request):
    rooms = add_current_availability(
        Rooms.objects
        .prefetch_related('images')
        .order_by('room_number'),
        timezone.localdate(),
    )
    return render(request, 'index.html', {'rooms': rooms, 'today': timezone.localdate()})


def about(request):
    return render(request, 'about.html')


def get_contact_submissions():
    return Contacts.objects.order_by("-pk")


def contact(request):
    contacts = get_contact_submissions()
    total_contacts = contacts.count()
    return render(
        request,
        "contacts.html",
        {"contacts": contacts, "total_contacts": total_contacts},
    )