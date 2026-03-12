from django.utils import timezone
from core.models import Abonnement


def user_subscription_status(request):
    """
    Ajoute le statut d'abonnement de l'utilisateur à tous les templates.
    Disponible via {{ user_subscription }} dans les templates.
    """
    if not request.user.is_authenticated:
        return {'user_subscription': None}
    
    try:
        profile = request.user.profile
        abonnement = profile.get_active_subscription()
        
        if abonnement:
            jours_restants = (abonnement.date_fin - timezone.now()).days
            return {
                'user_subscription': {
                    'is_premium': True,
                    'nom': abonnement.offre.nom,
                    'jours_restants': max(0, jours_restants),
                    'date_fin': abonnement.date_fin,
                }
            }
        else:
            return {'user_subscription': {'is_premium': False}}
    except Exception:
        return {'user_subscription': {'is_premium': False}}
