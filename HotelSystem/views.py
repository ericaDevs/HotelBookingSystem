from django.shortcuts import render
from Properties.models import Rooms
from Admin.models import Contacts


# Create your views here.
def home(request):
    rooms = (
        Rooms.objects.filter(is_available=True)
        .prefetch_related('images')
        .order_by('room_number')
    )
    return render(request, 'index.html', {'rooms': rooms})


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