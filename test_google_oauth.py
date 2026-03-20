#!/usr/bin/env python
"""
Script de test pour Google OAuth
Exécute ce script pour vérifier la configuration et tester la connexion
"""

import os
import sys
import django
from dotenv import load_dotenv

# Configuration du path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Charger les variables d'environnement
load_dotenv(BASE_DIR + "/.env")

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

def print_colored(text, color="green"):
    """Affiche du texte coloré dans le terminal"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def test_google_oauth_config():
    """Teste la configuration Google OAuth"""
    print_colored("\n" + "="*60, "blue")
    print_colored("🔍 TEST DE CONFIGURATION GOOGLE OAUTH", "blue")
    print_colored("="*60 + "\n", "blue")
    
    # Vérifier les variables d'environnement
    print_colored("1. Variables d'environnement:", "yellow")
    client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    
    if client_id:
        print_colored(f"   ✅ GOOGLE_CLIENT_ID: {client_id[:30]}...", "green")
    else:
        print_colored("   ❌ GOOGLE_CLIENT_ID: NON CONFIGURÉ", "red")
    
    if client_secret:
        print_colored(f"   ✅ GOOGLE_CLIENT_SECRET: {client_secret[:10]}...", "green")
    else:
        print_colored("   ❌ GOOGLE_CLIENT_SECRET: NON CONFIGURÉ", "red")
    
    # Vérifier la configuration Django
    print_colored("\n2. Configuration Django:", "yellow")
    print_colored(f"   DEBUG: {settings.DEBUG}", "green")
    print_colored(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}", "green")
    print_colored(f"   ACCOUNT_DEFAULT_HTTP_PROTOCOL: {getattr(settings, 'ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'non configuré')}", "green")
    
    # Vérifier la configuration Google OAuth
    print_colored("\n3. Configuration Google OAuth:", "yellow")
    google_config = settings.SOCIALACCOUNT_PROVIDERS.get('google', {})
    
    if google_config:
        app_config = google_config.get('APP', {})
        print_colored(f"   ✅ Client ID: {app_config.get('client_id', 'NON CONFIGURÉ')[:30]}...", "green")
        print_colored(f"   ✅ Secret: {app_config.get('secret', 'NON CONFIGURÉ')[:10]}...", "green")
        print_colored(f"   ✅ Scope: {google_config.get('SCOPE', [])}", "green")
    else:
        print_colored("   ❌ SOCIALACCOUNT_PROVIDERS['google']: NON CONFIGURÉ", "red")
    
    # URLs de callback
    print_colored("\n4. URLs de callback à configurer dans Google Cloud Console:", "yellow")
    redirect_uris = [
        "http://127.0.0.1:8000/accounts/google/login/callback/",
        "http://localhost:8000/accounts/google/login/callback/",
        "https://127.0.0.1:8000/accounts/google/login/callback/",
        "https://omerpay.share.zrok.io/accounts/google/login/callback/",
    ]
    
    for uri in redirect_uris:
        print_colored(f"   📋 {uri}", "blue")
    
    print_colored("\n" + "="*60, "blue")
    print_colored("📝 INSTRUCTIONS:", "yellow")
    print_colored("="*60, "blue")
    print_colored("""
1. Copie les URLs de callback ci-dessus
2. Va sur https://console.cloud.google.com/apis/credentials
3. Sélectionne ton projet
4. Clique sur ton "OAuth 2.0 Client ID"
5. Dans "Authorized redirect URIs", ajoute les URLs
6. Clique sur "Save"
7. Attends 5-10 minutes
8. Redémarre le serveur Django
9. Teste avec: http://127.0.0.1:8000/debug-oauth/
    """, "green")
    
    # Test de l'URL de callback actuelle
    print_colored("\n5. Test de l'URL de callback actuelle:", "yellow")
    redirect_uri = google_config.get('REDIRECT_URI', 'Non configuré')
    print_colored(f"   REDIRECT_URI: {redirect_uri}", "blue")
    
    print_colored("\n✅ Test terminé!\n", "green")

if __name__ == "__main__":
    test_google_oauth_config()
