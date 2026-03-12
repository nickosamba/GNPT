from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
import json
import uuid
import logging

from .models import OffreAbonnement, Paiement, Profile, Abonnement, Video, Commentaire, Categorie, Like
from .openpay_service import openpay_service, OpenPayError, OPENPAY_API_KEY

logger = logging.getLogger(__name__)


def home(request):
    """Page d'accueil avec redirection vers dashboard si connecté."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/index.html")


def index(request):
    """Page d'accueil publique."""
    from .models import OffreAbonnement
    offres = OffreAbonnement.objects.filter(is_active=True).order_by('prix')
    return render(request, "core/index.html", {"offres": offres})


def connexion(request):
    """Page de connexion avec support Google OAuth et formulaire classique."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Récupérer l'URL de redirection après connexion
    next_url = request.GET.get('next', 'dashboard')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Connexion réussie ! Bienvenue.")
            # Rediriger vers la page demandée ou le dashboard
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, "core/connexion.html", {"form": form, "next": next_url})


@login_required
def deconnexion(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect("index")


@login_required
def video(request):
    """Page de catalogue des vidéos avec recherche et filtres."""
    query = request.GET.get('q', '')
    categorie_id = request.GET.get('categorie', '')

    videos = Video.objects.filter(is_active=True)
    categories = Categorie.objects.filter(is_active=True)
    selected_category = None

    # Filtrer par recherche
    if query:
        videos = videos.filter(
            models.Q(titre__icontains=query) |
            models.Q(description__icontains=query)
        )

    # Filtrer par catégorie
    if categorie_id:
        try:
            selected_category = Categorie.objects.get(id=int(categorie_id), is_active=True)
            videos = videos.filter(categorie=selected_category)
        except (ValueError, TypeError, Categorie.DoesNotExist):
            pass

    # Filtrer par gratuit/premium
    free_filter = request.GET.get('free', '')
    if free_filter == 'true':
        videos = videos.filter(is_free=True)
    elif free_filter == 'false':
        videos = videos.filter(is_free=False)

    context = {
        'videos': videos,
        'categories': categories,
        'selected_category': selected_category,
        'query': query,
        'selected_categorie': categorie_id,
        'free_filter': free_filter,
    }
    return render(request, 'core/video.html', context)


@login_required
def api_search_videos(request):
    """API endpoint pour la recherche de vidéos avec suggestions."""
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 10))
    
    videos = Video.objects.filter(is_active=True)
    
    if query:
        videos = videos.filter(
            models.Q(titre__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(categorie__nom__icontains=query)
        )[:limit]
    
    results = []
    for video in videos:
        results.append({
            'id': video.id,
            'titre': video.titre,
            'description': video.description[:100] if video.description else '',
            'categorie': video.categorie.nom if video.categorie else None,
            'categorie_id': video.categorie_id,
            'is_free': video.is_free,
            'url': f'/video/{video.id}/',
            'miniature': video.miniature.url if video.miniature else None,
            'date_pub': video.date_publication.strftime('%d %b %Y')
        })
    
    return JsonResponse({'videos': results})


@login_required
def dashboard(request):
    """Tableau de bord utilisateur connecté."""
    from .models import OffreAbonnement, Paiement, Categorie, Video
    offres = OffreAbonnement.objects.all()
    # Récupérer les 5 derniers paiements de l'utilisateur
    paiements = Paiement.objects.filter(user=request.user).order_by('-date_creation')[:5]
    # Récupérer les catégories actives
    categories = Categorie.objects.filter(is_active=True)
    # Récupérer 6 vidéos recommandées (gratuites et payantes)
    videos_recommandees = Video.objects.filter(is_active=True).order_by('-date_publication')[:6]
    return render(request, "core/dashboard.html", {
        "user": request.user,
        "offres": offres,
        "paiements": paiements,
        "categories": categories,
        "videos_recommandees": videos_recommandees,
    })


@login_required
def initier_paiement(request, offre_id):
    """
    Initie un paiement pour un abonnement donné via PayLink OpenPay.
    Crée un lien de paiement et redirige l'utilisateur vers la page sécurisée OpenPay.

    Logic:
    - Prend un 'offre_id'
    - Génère une transaction interne
    - Appelle l'endpoint /v1/payment-link d'OpenPay avec XO-API-KEY
    - Enregistre le paiement en PENDING
    - Redirige vers payment_url
    """
    # Vérifier que la clé API est configurée
    if not OPENPAY_API_KEY:
        messages.error(request, "Configuration manquante : La clé API OpenPay n'est pas configurée. Contactez l'administrateur.")
        return redirect('dashboard')

    offre = get_object_or_404(OffreAbonnement, id=offre_id)
    profile = request.user.profile

    # Contexte par défaut pour le formulaire
    context = {
        "offre": offre,
        "profile": profile,
    }

    if request.method == "POST":
        # Récupérer le numéro depuis le POST ou utiliser celui du profil
        telephone = request.POST.get('telephone', '').replace(' ', '').replace('-', '')
        provider = request.POST.get('provider', 'MTN')

        # Si aucun numéro fourni, utiliser un placeholder (l'utilisateur le saisira sur OpenPay)
        if not telephone:
            telephone = profile.telephone if profile.telephone else '242000000000'

        # Nettoyer le numéro (format international sans +)
        if telephone.startswith('+'):
            telephone = telephone[1:]

        # Si le numéro commence par 0, ajouter l'indicatif Congo (242)
        if telephone.startswith('0'):
            telephone = '242' + telephone[1:]

        # Si le numéro est trop court (sans indicatif), ajouter 242
        if len(telephone) < 9:
            telephone = '242' + telephone

        # Générer un ID de transaction unique
        transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        customer_external_id = f"USER_{request.user.id}"

        # URLs de retour
        success_url = request.build_absolute_uri('/paiement/succes/')
        cancel_url = request.build_absolute_uri('/paiement/annule/')

        # Créer le paiement en base de données
        paiement = Paiement.objects.create(
            user=request.user,
            offre=offre,
            transaction_id_interne=transaction_id,
            customer_external_id=customer_external_id,
            payment_phone_number=telephone,
            provider=provider,
            montant_paye=offre.prix,
            statut='PENDING'
        )

        # Informations client
        # S'assurer que l'email n'est jamais vide (requis par OpenPay)
        user_email = request.user.email or f"user_{request.user.id}@estim-gram.com"
        customer = {
            "name": f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            "phone": telephone,
            "email": user_email
        }

        # Métadonnées pour le suivi
        metadata = {
            "order_id": transaction_id,
            "user_id": request.user.id,
            "offre_id": offre.id,
            "paiement_id": paiement.id
        }

        try:
            # Créer le PayLink via OpenPay
            result = openpay_service.creer_paylink(
                montant=offre.prix,
                description=f"Abonnement - {offre.nom}",
                customer=customer,
                metadata=metadata,
                expires_at=24,  # 24 heures
                success_url=success_url,
                cancel_url=cancel_url
            )

            if result['success']:
                # Mettre à jour le paiement avec le lien de paiement
                paiement.payment_token = result.get('payment_token')
                paiement.reference_operateur = result.get('reference') or result.get('payment_token')
                paiement.payment_url = result.get('payment_url')
                paiement.reponse_api_brute = json.dumps(result.get('data', {}))
                paiement.save()

                logger.info(f"PayLink créé: {paiement.payment_token} pour {request.user.email}")

                # Rediriger vers le lien de paiement OpenPay
                return redirect(result.get('payment_url'))
            else:
                paiement.marquer_comme_echec()
                messages.error(request, f"Échec de l'initiation du paiement: {result.get('error')}")
                return render(request, "core/paiement.html", context)

        except OpenPayError as e:
            logger.error(f"Erreur OpenPay: {e.message} (status: {e.status_code})")
            paiement.marquer_comme_echec({'error': e.message})
            messages.error(request, f"Erreur de paiement: {e.message}")
            return render(request, "core/paiement.html", context)
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            paiement.marquer_comme_echec({'error': str(e)})
            messages.error(request, "Erreur technique lors du paiement")
            return render(request, "core/paiement.html", context)

    return render(request, "core/paiement.html", context)


@login_required
def paiement_succes(request):
    """Page de succès après paiement."""
    paiement = Paiement.objects.filter(
        user=request.user,
        statut='SUCCESS'
    ).order_by('-date_creation').first()

    if not paiement:
        messages.warning(request, "Aucun paiement réussi trouvé.")
        return redirect('dashboard')

    return render(request, "core/paiement_succes.html", {"paiement": paiement})


@login_required
def paiement_annule(request):
    """Page d'annulation de paiement."""
    messages.info(request, "Le paiement a été annulé.")
    return render(request, "core/paiement_echec.html", {"annule": True})


def video(request):
    """Liste des vidéos disponibles."""
    videos = Video.objects.all()
    context = {"videos": videos}
    return render(request, "streaming/video.html", context)


def streaming(request, id):
    """Page de streaming d'une vidéo avec commentaires."""
    video = get_object_or_404(Video, id=id)

    # Vérifier si la vidéo est gratuite ou si l'utilisateur a un abonnement
    is_accessible = video.is_free
    user_has_subscription = False
    user_has_liked = False
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            abonnement = profile.get_active_subscription()
            user_has_subscription = bool(abonnement)
            # Si l'utilisateur a un abonnement, toutes les vidéos sont accessibles
            is_accessible = True
            # Vérifier si l'utilisateur a déjà liké cette vidéo
            from .models import Like
            user_has_liked = Like.objects.filter(user=request.user, video=video).exists()
        except Exception:
            pass

    # Si la vidéo n'est pas accessible, rediriger ou afficher un message
    if not is_accessible:
        messages.warning(request, "Cette vidéo est réservée aux abonnés. Veuillez souscrire à un abonnement pour y accéder.")
        return redirect("dashboard")

    # Gestion des commentaires (POST)
    if request.method == "POST" and request.user.is_authenticated:
        contenu = request.POST.get("contenu")
        if contenu:
            commentaire = Commentaire.objects.create(user=request.user, video=video, contenu=contenu)
            # Retourner une réponse JSON pour AJAX
            return JsonResponse({
                "success": True,
                "message": "Commentaire ajouté",
                "commentaire": {
                    "id": commentaire.id,
                    "contenu": commentaire.contenu,
                    "user": commentaire.user.username,
                    "user_initial": (commentaire.user.first_name or commentaire.user.username)[0].upper(),
                    "created_at": commentaire.created_at.strftime("%d/%m/%Y à %H:%M")
                }
            })
        return JsonResponse({"success": False, "message": "Contenu vide"}, status=400)

    commentaires = Commentaire.objects.filter(video=video).order_by('-created_at')
    context = {
        "video": video,
        "commentaires": commentaires,
        "user_has_subscription": user_has_subscription,
        "user_has_liked": user_has_liked,
    }
    return render(request, "streaming/streaming.html", context)


@login_required
def like_video(request, id):
    """Gère les likes sur les vidéos via AJAX."""
    from .models import Video, Like
    
    if request.method == "POST":
        video = get_object_or_404(Video, id=id)
        data = json.loads(request.body)
        liked = data.get("liked", False)
        
        if liked:
            # Ajouter le like (gère les doublons grâce au UniqueConstraint)
            Like.objects.get_or_create(user=request.user, video=video)
        else:
            # Supprimer le like
            Like.objects.filter(user=request.user, video=video).delete()
        
        # Retourner le nouveau nombre de likes
        like_count = video.likes.count()
        return JsonResponse({"success": True, "like_count": like_count})
    
    return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)


@csrf_exempt
@require_POST
def paiement_callback(request):
    """
    Endpoint callback pour les notifications de paiement OpenPay.
    Reçoit les notifications de changement de statut et active l'abonnement.
    
    Logic:
    - Reçoit la notification de paiement (POST)
    - Valide les données reçues
    - Trouve le paiement via payment_id ou référence
    - Met à jour le statut et active l'abonnement si succès
    """
    try:
        # Récupérer les données du callback
        data = json.loads(request.body.decode('utf-8'))
        
        reference = data.get('reference')
        statut = data.get('status')
        metadata = data.get('metadata', {})
        montant_recu = data.get('amount')
        payment_token = data.get('payment_token')
        
        # Récupérer le paiement via payment_id ou référence
        paiement_id = metadata.get('paiement_id')
        
        if paiement_id:
            paiement = Paiement.objects.get(id=paiement_id)
        elif reference:
            paiement = Paiement.objects.filter(reference_operateur=reference).first()
        else:
            logger.error("Aucun identifiant de paiement dans le callback")
            return JsonResponse({'error': 'paiement_id manquant dans metadata'}, status=400)
        
        if not paiement:
            logger.error(f"Paiement non trouvé: {paiement_id or reference}")
            return JsonResponse({'error': 'Paiement non trouvé'}, status=404)
        
        # Éviter le traitement en double
        if paiement.is_processed and paiement.statut in ['SUCCESS', 'FAILED', 'CANCELLED']:
            logger.info(f"Paiement déjà traité: {paiement.transaction_id_interne}")
            return JsonResponse({'status': 'ok', 'message': 'Déjà traité'})
        
        # Security: Vérifier le montant reçu vs le montant attendu
        if montant_recu and not paiement.verifier_montant(montant_recu):
            logger.warning(f"Discordance de montant pour {paiement.transaction_id_interne}: attendu {paiement.montant_paye}, reçu {montant_recu}")
        
        # Traiter selon le statut
        if statut == 'success':
            paiement.marquer_comme_succes(
                reference_operateur=reference,
                reponse_api=data
            )
            logger.info(f"Paiement confirmé via callback: {paiement.transaction_id_interne}")
            return JsonResponse({'status': 'ok', 'message': 'Paiement confirmé', 'abonnement_active': True})
        
        elif statut in ('failed', 'cancelled', 'expired'):
            if statut == 'cancelled':
                paiement.marquer_comme_annule()
            else:
                paiement.marquer_comme_echec(reponse_api=data)
            logger.info(f"Paiement {statut} via callback: {paiement.transaction_id_interne}")
            return JsonResponse({'status': 'ok', 'message': f'Paiement {statut} enregistré'})
        
        logger.info(f"Callback reçu statut {statut}: {paiement.transaction_id_interne}")
        return JsonResponse({'status': 'ok', 'message': 'Callback reçu'})
    
    except Paiement.DoesNotExist:
        logger.error(f"Paiement non trouvé pour callback")
        return JsonResponse({'error': 'Paiement non trouvé'}, status=404)
    except json.JSONDecodeError:
        logger.error(f"JSON invalide dans le callback")
        return JsonResponse({'error': 'JSON invalide'}, status=400)
    except OpenPayError as e:
        logger.error(f"Erreur OpenPay dans callback: {e.message}")
        return JsonResponse({'error': e.message}, status=500)
    except Exception as e:
        logger.error(f"Erreur inattendue dans callback: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def webhook_openpay(request):
    """
    Vue POST (csrf_exempt) pour recevoir les notifications asynchrones d'OpenPay.
    Doit valider la signature et mettre à jour le statut de l'abonnement.
    
    Logic:
    - Reçoit les notifications webhook d'OpenPay
    - Valide la signature du webhook
    - Récupère le paiement via le payment_id dans les métadonnées
    - Vérifie le montant reçu vs le montant attendu en BDD
    - Met à jour le statut de l'abonnement
    - Gère les timeouts de l'API avec des blocs try/except
    """
    try:
        # Récupérer le body brut pour la vérification de signature
        body = request.body.decode('utf-8')
        signature = request.headers.get('X-OpenPay-Signature', '')
        
        # Vérifier la signature (optionnel en dev, requis en prod)
        if not openpay_service.verifier_signature_webhook(body, signature):
            logger.warning(f"Signature invalide pour le webhook")
            return JsonResponse({'error': 'Signature invalide'}, status=401)

        data = json.loads(body)

        # Extraire les informations du webhook
        reference = data.get('reference')
        statut = data.get('status')
        metadata = data.get('metadata', {})
        montant_recu = data.get('amount')
        
        # Essayer de récupérer le paiement par payment_id ou par référence
        paiement_id = metadata.get('paiement_id')
        
        if paiement_id:
            paiement = Paiement.objects.get(id=paiement_id)
        elif reference:
            paiement = Paiement.objects.filter(reference_operateur=reference).first()
        else:
            logger.error("Aucun identifiant de paiement dans le webhook")
            return JsonResponse({'error': 'paiement_id manquant dans metadata'}, status=400)

        if not paiement:
            logger.error(f"Paiement non trouvé: {paiement_id or reference}")
            return JsonResponse({'error': 'Paiement non trouvé'}, status=404)
        
        # Éviter le traitement en double
        if paiement.is_processed and paiement.statut in ['SUCCESS', 'FAILED', 'CANCELLED']:
            logger.info(f"Paiement déjà traité: {paiement.transaction_id_interne}")
            return JsonResponse({'status': 'ok', 'message': 'Déjà traité'})
        
        # Security: Vérifier le montant reçu vs le montant attendu en BDD
        if montant_recu and not paiement.verifier_montant(montant_recu):
            logger.warning(f"Discordance de montant pour {paiement.transaction_id_interne}: attendu {paiement.montant_paye}, reçu {montant_recu}")
            # Ne pas bloquer, mais logger l'anomalie
        
        # Traiter selon le statut
        if statut == 'success':
            paiement.marquer_comme_succes(
                reference_operateur=reference,
                reponse_api=data
            )
            logger.info(f"Paiement confirmé via webhook: {paiement.transaction_id_interne}")
            return JsonResponse({'status': 'ok', 'message': 'Paiement confirmé'})

        elif statut in ('failed', 'cancelled', 'expired'):
            if statut == 'cancelled':
                paiement.marquer_comme_annule()
            else:
                paiement.marquer_comme_echec(reponse_api=data)
            logger.info(f"Paiement {statut} via webhook: {paiement.transaction_id_interne}")
            return JsonResponse({'status': 'ok', 'message': f'Paiement {statut} enregistré'})

        logger.info(f"Webhook reçu statut {statut}: {paiement.transaction_id_interne}")
        return JsonResponse({'status': 'ok', 'message': 'Webhook reçu'})

    except Paiement.DoesNotExist:
        logger.error(f"Paiement non trouvé pour webhook")
        return JsonResponse({'error': 'Paiement non trouvé'}, status=404)
    except json.JSONDecodeError:
        logger.error(f"JSON invalide dans le webhook")
        return JsonResponse({'error': 'JSON invalide'}, status=400)
    except OpenPayError as e:
        logger.error(f"Erreur OpenPay dans webhook: {e.message}")
        return JsonResponse({'error': e.message}, status=500)
    except Exception as e:
        logger.error(f"Erreur inattendue dans webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
