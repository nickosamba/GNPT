"""
Signals pour gérer la création automatique du Profile lors de l'inscription via Google.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.signals import pre_social_login, social_account_added


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crée automatiquement un Profile lorsqu'un nouvel utilisateur est créé.
    """
    if created:
        # Import here to avoid circular imports
        from .models import Profile
        Profile.objects.get_or_create(user=instance)


@receiver(pre_social_login)
def handle_pre_social_login(request, sociallogin, **kwargs):
    """
    Gère la connexion sociale avant la sauvegarde.
    Le profil sera créé par le signal post_save sur User.
    """
    pass


@receiver(social_account_added)
def handle_social_account_added(request, sociallogin, **kwargs):
    """
    Crée le profil après l'ajout d'un compte social.
    """
    user = sociallogin.user
    from .models import Profile
    Profile.objects.get_or_create(user=user)
