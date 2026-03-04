from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def home(request):
    """Page d'accueil avec redirection vers login si non connecté."""
    if request.user.is_authenticated:
        return render(request, "core/home.html", {"user": request.user})
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    """Tableau de bord utilisateur connecté."""
    return render(request, "core/dashboard.html", {"user": request.user})
