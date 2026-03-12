import json
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField

# ==========================================
# 1. RÉFÉRENTIEL GÉOGRAPHIQUE
# ==========================================
class PaysAutorise(models.Model):
    """Filtre les pays où le Mobile Money est actif pour l'application."""
    code_iso = CountryField(unique=True, help_text="Sélectionnez le pays (ex: Congo, Côte d'Ivoire)")
    indicatif = models.CharField(max_length=10, help_text="Ex: +242")
    is_active = models.BooleanField(default=True, help_text="Décocher pour désactiver les paiements dans ce pays")

    class Meta:
        verbose_name = "Pays Autorisé"
        verbose_name_plural = "Pays Autorisés"

    def __str__(self):
        return f"{self.code_iso.name} ({self.indicatif})"

    @property
    def drapeau_emoji(self):
        """Génère dynamiquement l'emoji du drapeau pour la rapidité mobile."""
        return "".join(chr(127397 + ord(c)) for c in str(self.code_iso).upper())


# ==========================================
# 2. CATALOGUE DES OFFRES (SaaS Features)
# ==========================================
class OffreAbonnement(models.Model):
    """Modèle 'Feature-Based' : On vend des accès et des capacités."""
    nom = models.CharField(max_length=100, help_text="Ex: Pack Étudiant, Pack Pro IA")
    prix = models.PositiveIntegerField(help_text="Montant en devise locale (ex: FCFA)")
    duree_jours = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True, help_text="Décocher pour masquer l'offre")

    # Flags de fonctionnalités (Active/Désactive des modules de l'app)
    can_access_videos = models.BooleanField(default=True)
    can_access_books = models.BooleanField(default=True)
    can_use_ai_chat = models.BooleanField(default=False)
    storage_limit_mb = models.FloatField(default=0.0, help_text="Limite de stockage PDF en Mo")

    class Meta:
        verbose_name = "Offre d'Abonnement"
        verbose_name_plural = "Offres d'Abonnement"
        ordering = ['prix']

    def __str__(self):
        return f"{self.nom} - {self.prix}"


# ==========================================
# 3. PROFIL UTILISATEUR & AUTHENTIFICATION
# ==========================================
class Profile(models.Model):
    """
    Profil utilisateur étendu pour django-allauth avec Google.
    Les données de base (email, nom, etc.) sont gérées par le modèle User de Django.
    Google pré-remplit automatiquement : email, first_name, last_name via les signals allauth.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    telephone = models.CharField(max_length=20, unique=True, db_index=True, blank=True, null=True)
    pays = models.ForeignKey(PaysAutorise, on_delete=models.SET_NULL, null=True, blank=True, related_name="profils")

    # Date d'expiration absolue (La seule source de vérité)
    premium_until = models.DateTimeField(null=True, blank=True, db_index=True)

    # Champs supplémentaires pour le profil
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    genre = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin'), ('A', 'Autre')], blank=True, null=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"

    def __str__(self):
        return f"Profil de {self.user.email}"

    @property
    def nom_complet(self):
        """Retourne le nom complet depuis le modèle User."""
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    @property
    def is_premium(self):
        """Calcul dynamique : Impossible d'avoir un statut premium expiré."""
        return bool(self.premium_until and self.premium_until > timezone.now())

    def get_active_subscription(self):
        """Récupère l'abonnement le plus récent et non expiré de l'historique."""
        return self.user.abonnements.filter(
            actif=True,
            date_fin__gt=timezone.now()
        ).order_by('-date_fin').first()


# ==========================================
# 4. HISTORIQUE ET PAIEMENTS (Sécurité / Audit)
# ==========================================
class Abonnement(models.Model):
    """Historique des accès : Permet de tracer qui a eu quoi et à quelle période."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="abonnements")
    offre = models.ForeignKey(OffreAbonnement, on_delete=models.PROTECT)
    date_debut = models.DateTimeField(default=timezone.now)
    date_fin = models.DateTimeField(db_index=True)
    actif = models.BooleanField(default=True, help_text="Peut être désactivé manuellement par un admin")

    class Meta:
        verbose_name = "Historique Abonnement"
        ordering = ['-date_fin']

    def __str__(self):
        return f"{self.user.email} - {self.offre.nom} (Jusqu'au {self.date_fin.strftime('%d/%m/%Y')})"


class Paiement(models.Model):
    """
    Trace irréfutable de la transaction Mobile Money en cas de litige.
    Intégration avec OpenPay API v1.
    """
    STATUT_CHOICES = [
        ('PENDING', 'En attente'),
        ('SUCCESS', 'Succès'),
        ('FAILED', 'Échec'),
        ('CANCELLED', 'Annulé'),
        ('EXPIRED', 'Expiré'),
    ]

    PROVIDER_CHOICES = [
        ('MTN', 'MTN Mobile Money'),
        ('AIRTEL', 'Airtel Money'),
        ('MOOV', 'Moov Money'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="paiements")
    offre = models.ForeignKey(OffreAbonnement, on_delete=models.PROTECT)
    transaction_id_interne = models.CharField(max_length=100, unique=True, db_index=True)
    payment_token = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Token de paiement OpenPay")
    reference_operateur = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="ID OpenPay (ex: PTXN26042237B99A5D9)")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='MTN')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='PENDING', db_index=True)
    montant_paye = models.PositiveIntegerField()
    payment_phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Numéro ayant servi au paiement")
    customer_external_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID client dans le système")
    payment_url = models.URLField(blank=True, null=True, help_text="Lien de paiement OpenPay (PayLink)")
    reponse_api_brute = models.TextField(blank=True, null=True, help_text="JSON de la réponse OpenPay")
    webhook_signature = models.CharField(max_length=255, blank=True, null=True, help_text="Signature du webhook")
    is_processed = models.BooleanField(default=False, help_text="Évite le traitement en double des webhooks")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(blank=True, null=True, help_text="Date de confirmation du paiement")
    expire_a = models.DateTimeField(blank=True, null=True, help_text="Date d'expiration du lien de paiement")

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['payment_token']),
            models.Index(fields=['reference_operateur']),
            models.Index(fields=['is_processed', 'statut']),
        ]

    def __str__(self):
        return f"[{self.statut}] {self.transaction_id_interne} - {self.montant_paye} XAF"

    def marquer_comme_succes(self, reference_operateur=None, reponse_api=None):
        """Marque le paiement comme réussi et met à jour l'abonnement de l'utilisateur."""
        if self.is_processed and self.statut == 'SUCCESS':
            # Déjà traité, éviter les doublons
            return
        
        self.statut = 'SUCCESS'
        self.reference_operateur = reference_operateur or self.reference_operateur
        if reponse_api:
            self.reponse_api_brute = json.dumps(reponse_api)
        self.date_confirmation = timezone.now()
        self.is_processed = True
        self.save()

        # Activer l'abonnement
        duree_jours = self.offre.duree_jours

        # Récupérer ou créer le profil
        profile, _ = Profile.objects.get_or_create(user=self.user)

        # Calculer la nouvelle date d'expiration
        if profile.premium_until and profile.premium_until > timezone.now():
            nouvelle_date = profile.premium_until + timezone.timedelta(days=duree_jours)
        else:
            nouvelle_date = timezone.now() + timezone.timedelta(days=duree_jours)

        profile.premium_until = nouvelle_date
        profile.save()

        # Créer l'historique d'abonnement
        Abonnement.objects.create(
            user=self.user,
            offre=self.offre,
            date_fin=nouvelle_date,
            actif=True
        )

    def marquer_comme_echec(self, reponse_api=None):
        """Marque le paiement comme échoué."""
        self.statut = 'FAILED'
        if reponse_api:
            self.reponse_api_brute = json.dumps(reponse_api)
        self.is_processed = True
        self.save()

    def marquer_comme_annule(self):
        """Marque le paiement comme annulé."""
        self.statut = 'CANCELLED'
        self.save()

    def verifier_montant(self, montant_recu):
        """Vérifie que le montant reçu correspond au montant attendu."""
        return int(montant_recu) == self.montant_paye


# ==========================================
# 5. CONTENU PÉDAGOGIQUE & IA (RAG)
# ==========================================
class Categorie(models.Model):
    """Catégories pour organiser les vidéos (Grammaire, Conjugaison, Exercices, etc.)."""
    nom = models.CharField(max_length=100, unique=True, help_text="Nom de la catégorie (ex: Grammaire, Conjugaison)")
    description = models.TextField(blank=True, help_text="Description courte de la catégorie")
    couleur = models.CharField(max_length=7, default="#3B82F6", help_text="Code couleur hex pour l'affichage (ex: #3B82F6)")
    icone = models.CharField(max_length=50, blank=True, help_text="Nom de l'icône ou lettre initiale")
    is_active = models.BooleanField(default=True, help_text="Décocher pour masquer la catégorie")
    ordre = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage (croissant)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom

    @property
    def video_count(self):
        """Retourne le nombre de vidéos dans cette catégorie."""
        return self.videos.filter(is_active=True).count()


class Video(models.Model):
    """Stockage des cours du professeur."""
    titre = models.CharField(max_length=255)
    description = models.TextField()
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True, related_name='videos')
    fichier_video = models.FileField(upload_to='videos_privees/')
    miniature = models.ImageField(upload_to='thumbs/', blank=True, null=True)
    is_free = models.BooleanField(default=False, help_text="Cocher pour offrir cette vidéo gratuitement (Marketing)")
    is_active = models.BooleanField(default=True, help_text="Décocher pour masquer la vidéo")
    date_publication = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.titre

    @property
    def likes_count(self):
        """Retourne le nombre de likes de cette vidéo."""
        return self.likes.count()


class DocumentIA(models.Model):
    """Gestion des PDF des élèves avec contrôle strict des quotas de stockage."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    titre = models.CharField(max_length=255)
    fichier_pdf = models.FileField(upload_to='docs_ia_prives/')
    taille_mb = models.FloatField(default=0.0)
    vector_id = models.CharField(max_length=255, blank=True, help_text="ID dans la base vectorielle (Pinecone/Chroma)")
    date_upload = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Sécurité : Vérifie que l'élève ne dépasse pas le stockage autorisé par son offre."""
        if not self.pk:
            current_usage = self.user.documents.aggregate(total=Sum('taille_mb'))['total'] or 0.0
            active_sub = self.user.profile.get_active_subscription()

            if not active_sub or not active_sub.offre.can_use_ai_chat:
                raise ValidationError("Vous devez avoir une offre IA active pour uploader un document.")

            limit = active_sub.offre.storage_limit_mb

            if current_usage + self.taille_mb > limit:
                raise ValidationError(f"Limite de stockage atteinte ({limit} Mo max). Veuillez supprimer des fichiers ou upgrader votre offre.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Doc IA: {self.titre} ({self.user.username})"


# ==========================================
# 6. INTERACTIONS SOCIALES
# ==========================================
class Commentaire(models.Model):
    """
    Modèle pour les commentaires sur les vidéos et documents.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commentaires")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="commentaires", blank=True, null=True)
    document = models.ForeignKey(DocumentIA, on_delete=models.CASCADE, related_name="commentaires", blank=True, null=True)

    contenu = models.TextField(help_text="Contenu du commentaire")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name="reponses", blank=True, null=True, help_text="Commentaire parent pour les réponses")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, help_text="Marquer comme supprimé sans effacer de la BDD")

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ['-created_at']

    def __str__(self):
        return f"Commentaire de {self.user.email} le {self.created_at.strftime('%d/%m/%Y')}"

    @property
    def likes_count(self):
        """Retourne le nombre de likes du commentaire."""
        return self.likes.count()


class Like(models.Model):
    """
    Modèle pour les likes sur les commentaires, vidéos et documents.
    Un utilisateur ne peut liker qu'une seule fois par objet.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    commentaire = models.ForeignKey(Commentaire, on_delete=models.CASCADE, related_name="likes", blank=True, null=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="likes", blank=True, null=True)
    document = models.ForeignKey(DocumentIA, on_delete=models.CASCADE, related_name="likes", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Like"
        verbose_name_plural = "Likes"
        constraints = [
            models.UniqueConstraint(fields=['user', 'commentaire'], name='unique_like_commentaire'),
            models.UniqueConstraint(fields=['user', 'video'], name='unique_like_video'),
            models.UniqueConstraint(fields=['user', 'document'], name='unique_like_document'),
        ]

    def __str__(self):
        target = self.commentaire or self.video or self.document
        return f"Like de {self.user.email} sur {target}"

    def clean(self):
        """Validation : Au moins un objet doit être associé au like."""
        if not any([self.commentaire, self.video, self.document]):
            raise ValidationError("Un like doit être associé à un commentaire, une vidéo ou un document.")
        if sum([bool(self.commentaire), bool(self.video), bool(self.document)]) > 1:
            raise ValidationError("Un like ne peut être associé qu'à un seul objet à la fois.")
