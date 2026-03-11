from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("connexion/", views.connexion, name="connexion"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("dashboard/", views.dashboard, name="dashboard"),
    
    # Paiement OpenPay
    path("paiement/<int:offre_id>/", views.initier_paiement, name="initier_paiement"),
    path("paiement/succes/", views.paiement_succes, name="paiement_succes"),
    path("paiement/annule/", views.paiement_annule, name="paiement_annule"),
    path("paiement/callback/", views.paiement_callback, name="paiement_callback"),
    path("webhook/openpay/", views.webhook_openpay, name="webhook_openpay"),
]
