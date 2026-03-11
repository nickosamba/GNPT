import requests
from django.conf import settings


class OpenPayService:
    @staticmethod
    def creer_lien_paiement(paiement_obj):
        """
        Génère un lien de paiement OpenPay pour un objet Paiement Django.
        """
        url = f"{settings.OPENPAY_URL}/payment-link"
        headers = {
            "XO-API-KEY": settings.OPENPAY_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        data = {
            "amount": paiement_obj.offre.prix,
            "description": f"Abonnement {paiement_obj.offre.nom}",
            "expires_at": 24,  # expire dans 24h
            "customer": {
                "name": paiement_obj.user.profile.nom_complet,
                "phone": paiement_obj.user.profile.telephone or "",
            },
            "success_url": "https://ton-domaine.com/paiement/success/",
            "metadata": {"transaction_id_interne": paiement_obj.transaction_id_interne},
        }

        response = requests.post(url, json=data, headers=headers)
        return response.json()
