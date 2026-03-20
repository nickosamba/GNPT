"""
Debug view to show the exact Google OAuth redirect URI
"""
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from allauth.socialaccount.providers.google.provider import GoogleProvider
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def debug_oauth_redirect(request):
    """
    View to display the exact redirect URI that will be sent to Google
    """
    # Get the Google provider
    try:
        app = SocialApp.objects.get(provider='google')
    except SocialApp.DoesNotExist:
        app = None
    
    # Build the redirect URI manually
    scheme = 'http' if settings.DEBUG else 'https'
    host = request.get_host()
    redirect_uri = f"{scheme}://{host}/accounts/google/login/callback/"
    
    context = {
        'request_host': request.get_host(),
        'request_scheme': request.scheme,
        'redirect_uri': redirect_uri,
        'debug': settings.DEBUG,
        'google_client_id': settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'] if settings.SOCIALACCOUNT_PROVIDERS else 'NOT SET',
        'app': app,
    }
    
    return render(request, 'debug_oauth_redirect.html', context)
