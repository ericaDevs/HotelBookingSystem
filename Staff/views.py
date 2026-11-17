from django.shortcuts import redirect, render


def staff_login(request):
    return redirect('admin_portal:login')


def staff_dashboard(request):
    return render(request, 'staff_portal/overview.html')
