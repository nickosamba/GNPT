"""
Custom adapter for handling Google OAuth signup.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptateur personnalisé pour gérer la création des utilisateurs via Google.
    La création du profil est gérée par les signals.
    """
    def get_connect_redirect_url(self, request, sociallogin):
        """
        Retourne l'URL de redirection après connexion sociale.
        Gère HTTP/HTTPS dynamiquement.
        """
        from django.urls import reverse
        from allauth.utils import get_request_param
        
        redirect_url = get_request_param(request, 'next', settings.LOGIN_REDIRECT_URL)
        return redirect_url
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Permet l'inscription automatique pour Google OAuth.
        """
        return True
