from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import *


def home(request):
    """Page d'accueil avec redirection vers dashboard si connecté."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    """Tableau de bord utilisateur connecté."""
    return render(request, "core/dashboard.html", {"user": request.user})


def video(request):

    videos = Video.objects.all()

    context = {"videos": videos}

    return render(request, "streaming/video.html", context)


def streaming(request, id):

    videos = get_object_or_404(Video, id=id)

    if request.method == "POST" and request.user.is_authenticated:
        contenu = request.POST.get("contenu")

        if contenu:
            Commentaire.objects.create(user=request.user, video=videos, contenu=contenu)

        return redirect("streaming", id=id)

    commentaires = Commentaire.objects.filter(video=videos)

    context = {"videos": videos, "commentaires": commentaires}

    return render(request, "streaming/streaming.html", context)

    import uuid

    from django.shortcuts import redirect, render

    from .models import OffreAbonnement, Paiement
    from .services import OpenPayService

    def initier_paiement(request, offre_id):
        offre = OffreAbonnement.objects.get(id=offre_id)

        # 1. Créer une trace locale en attente (PENDING)
        transaction_id = str(uuid.uuid4())
        paiement = Paiement.objects.create(
            user=request.user,
            offre=offre,
            transaction_id_interne=transaction_id,
            montant_paye=offre.prix,
            statut="PENDING",
        )

        # 2. Demander le lien à OpenPay
        openpay_resp = OpenPayService.creer_lien_paiement(paiement)

        if openpay_resp.get("success"):
            # Enregistrer le lien ou d'autres infos si nécessaire
            paiement.reponse_api_brute = str(openpay_resp)
            paiement.save()

            # 3. Rediriger l'utilisateur vers la page de paiement OpenPay
            return redirect(openpay_resp["data"]["payment_url"])
        else:
            return render(request, "erreur_paiement.html", {"error": openpay_resp})
