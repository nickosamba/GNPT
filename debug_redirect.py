"""
Script pour déboguer le redirect URI utilisé par django-allauth
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.google.provider import GoogleProvider
from config.settings import SOCIALACCOUNT_PROVIDERS

print("=" * 60)
print("GOOGLE OAUTH CONFIGURATION")
print("=" * 60)

provider = GoogleProvider(None)
print(f"\nProvider: {provider}")

# Vérifier les settings
google_settings = SOCIALACCOUNT_PROVIDERS.get('google', {})
print(f"\nSettings from SOCIALACCOUNT_PROVIDERS:")
for key, value in google_settings.items():
    print(f"  {key}: {value}")

# Vérifier l'adapter
print(f"\nGoogleOAuth2Adapter:")
print(f"  Base URL: {GoogleOAuth2Adapter}")

# Vérifier les variables d'environnement
from decouple import config
from dotenv import load_dotenv
load_dotenv('.env')

print(f"\nEnvironment variables:")
print(f"  GOOGLE_CLIENT_ID: {config('GOOGLE_CLIENT_ID', default='NOT SET')[:20]}...")
print(f"  GOOGLE_CLIENT_SECRET: {'*' * 20}")

print("\n" + "=" * 60)
print("REDIRECT URIs à ajouter dans Google Cloud Console:")
print("=" * 60)
print("http://127.0.0.1:8000/accounts/google/login/callback/")
print("http://localhost:8000/accounts/google/login/callback/")
print("https://omerpay.share.zrok.io/accounts/google/login/callback/")
print("=" * 60)
