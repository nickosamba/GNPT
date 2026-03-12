from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("connexion/", views.connexion, name="connexion"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("video/", views.video, name='video'),
    path("video/<int:id>/", views.streaming, name="streaming"),
    path("video/<int:id>/like/", views.like_video, name="like_video"),
    path("api/search/", views.api_search_videos, name="api_search_videos"),

    # Paiement OpenPay
    path("paiement/<int:offre_id>/", views.initier_paiement, name="initier_paiement"),
    path("paiement/succes/", views.paiement_succes, name="paiement_succes"),
    path("paiement/annule/", views.paiement_annule, name="paiement_annule"),
    path("paiement/callback/", views.paiement_callback, name="paiement_callback"),
    path("webhook/openpay/", views.webhook_openpay, name="webhook_openpay"),
]
