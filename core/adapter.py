"""
Custom adapter for handling Google OAuth signup.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptateur personnalisé pour gérer la création des utilisateurs via Google.
    La création du profil est gérée par les signals.
    """
    pass
