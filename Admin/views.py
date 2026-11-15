from django.shortcuts import render


def admin_login(request):
    return render(request, 'admin_portal/login.html')


def admin_dashboard(request):
    return render(request, 'admin_portal/dashboard.html')
