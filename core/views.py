from django.shortcuts import render,get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import *


def home(request):
    """Page d'accueil avec redirection vers login si non connecté."""
    if request.user.is_authenticated:
        return render(request, "core/home.html", {"user": request.user})
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    """Tableau de bord utilisateur connecté."""
    return render(request, "core/dashboard.html", {"user": request.user})

def video(request): 

    videos = Video.objects.all()

    context = {
        "videos":videos
    }

    return render(request,"streaming/video.html",context)

def streaming(request, id):

    videos = get_object_or_404(Video,id=id)

    if request.method == "POST" and request.user.is_authenticated:
        contenu = request.POST.get("contenu")

        if contenu:
            Commentaire.objects.create(
                user = request.user,
                video = videos,
                contenu = contenu
            )
        
        return redirect( 'streaming',id=id)

    commentaires = Commentaire.objects.filter(video = videos)

    context = {
        "videos":videos,
        "commentaires":commentaires
        }

    return render(request,"streaming/streaming.html",context)