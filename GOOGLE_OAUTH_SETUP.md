# Configuration Google OAuth - Résolution erreur redirect_uri_mismatch

## Problème
L'erreur `redirect_uri_mismatch` se produit lorsque l'URL de callback utilisée par ton application ne correspond pas à celle configurée dans la Google Cloud Console.

## Solution - Étape par étape

### 1. Ouvrir la Google Cloud Console
Rends-toi sur : https://console.cloud.google.com/apis/credentials

### 2. Sélectionner ton projet
Choisis le projet qui contient tes identifiants OAuth.

### 3. Modifier le OAuth 2.0 Client ID
- Trouve ton "OAuth 2.0 Client ID" dans la liste
- Clique dessus pour modifier

### 4. Ajouter les URLs de callback autorisées

Dans la section **"Authorized redirect URIs"**, ajoute EXACTEMENT ces URLs :

#### Pour le développement local (HTTP) :
```
http://127.0.0.1:8000/accounts/google/login/callback/
http://localhost:8000/accounts/google/login/callback/
```

#### Pour le développement local avec HTTPS (recommandé) :
```
https://127.0.0.1:8000/accounts/google/login/callback/
```

#### Pour ngrok (si tu l'utilises) :
```
https://ton-id-ngrok.ngrok-free.dev/accounts/google/login/callback/
```

#### Pour zrok (si tu l'utilises) :
```
https://omerpay.share.zrok.io/accounts/google/login/callback/
```

### 5. Sauvegarder
Clique sur **"Save"** en bas de la page.

### 6. Attendre la propagation
Attends **5-10 minutes** que Google propage les changements.

### 7. Redémarrer ton serveur Django
```bash
pkill -f "runserver 8000"
cd "/Users/omerlinks/Desktop/estim gram/GNPT"
env/bin/python manage.py runserver 8000
```

## URLs de callback à configurer (copier-coller)

Copie ces URLs dans la Google Cloud Console :

```
http://127.0.0.1:8000/accounts/google/login/callback/
http://localhost:8000/accounts/google/login/callback/
https://127.0.0.1:8000/accounts/google/login/callback/
https://marge-unerasing-mila.ngrok-free.dev/accounts/google/login/callback/
https://omerpay.share.zrok.io/accounts/google/login/callback/
```

## Vérification

Après configuration, teste la connexion Google :

1. Ouvre http://127.0.0.1:8000/accounts/login/
2. Clique sur "Se connecter avec Google"
3. Tu devrais être redirigé vers Google, puis vers ton dashboard

## Erreurs courantes

### ❌ Erreur : `redirect_uri_mismatch`
**Cause** : L'URL de callback ne correspond pas exactement à celle configurée.

**Solution** : Vérifie que l'URL dans la console Google correspond EXACTEMENT à celle utilisée par Django (http vs https, port, chemin).

### ❌ Erreur : `disallowed_redirect_uri`
**Cause** : L'hôte n'est pas dans `ALLOWED_HOSTS`.

**Solution** : Ajoute l'hôte dans `config/settings.py` :
```python
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".ngrok-free.dev", "omerpay.share.zrok.io"]
```

## Configuration actuelle de ton projet

Tes identifiants Google OAuth sont configurés dans `.env` :
- **Client ID** : `your_google_client_id_here`
- **Client Secret** : `your_google_client_secret_here`

## Notes importantes

⚠️ **Ne partage jamais tes Client ID et Secret** sur GitHub ou dans un dépôt public.

✅ Utilise toujours HTTPS en production.

✅ Pour le développement local, HTTP est acceptable mais HTTPS est recommandé.

## Besoin d'aide supplémentaire ?

Si tu as toujours des problèmes, vérifie les logs Django :
```bash
tail -f debug.log
```

Ou consulte la documentation officielle :
- [django-allauth Google OAuth](https://django-allauth.readthedocs.io/en/latest/providers.html#google)
- [Google OAuth 2.0 Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
