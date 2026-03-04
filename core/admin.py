from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import (
    PaysAutorise,
    OffreAbonnement,
    Profile,
    Abonnement,
    Paiement,
    Video,
    DocumentIA,
    Commentaire,
    Like,
)


# ==========================================
# 1. RÉFÉRENTIEL GÉOGRAPHIQUE
# ==========================================
@admin.register(PaysAutorise)
class PaysAutoriseAdmin(ModelAdmin):
    list_display = ["code_iso", "indicatif", "is_active", "drapeau_emoji_display"]
    list_filter = ["is_active"]
    search_fields = ["code_iso__name", "indicatif"]
    list_editable = ["is_active"]
    
    fieldsets = [
        (None, {
            "fields": ["code_iso", "indicatif", "is_active"],
        }),
    ]
    
    @display(description="Drapeau")
    def drapeau_emoji_display(self, obj):
        return obj.drapeau_emoji


# ==========================================
# 2. CATALOGUE DES OFFRES (SaaS Features)
# ==========================================
@admin.register(OffreAbonnement)
class OffreAbonnementAdmin(ModelAdmin):
    list_display = ["nom", "prix", "duree_jours", "can_access_videos", "can_access_books", "can_use_ai_chat", "storage_limit_mb"]
    list_filter = ["can_access_videos", "can_access_books", "can_use_ai_chat"]
    search_fields = ["nom"]
    list_editable = ["prix", "duree_jours"]
    
    fieldsets = [
        ("Informations générales", {
            "fields": ["nom", "prix", "duree_jours"],
        }),
        ("Fonctionnalités", {
            "fields": [
                "can_access_videos",
                "can_access_books",
                "can_use_ai_chat",
                "storage_limit_mb",
            ],
            "classes": ["collapse"],
        }),
    ]


# ==========================================
# 3. PROFIL UTILISATEUR & AUTHENTIFICATION
# ==========================================
@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ["user", "telephone", "pays", "is_premium_display", "premium_until"]
    list_filter = ["pays", "premium_until"]
    search_fields = ["user__email", "user__username", "telephone"]
    readonly_fields = ["created_at", "updated_at", "nom_complet_display", "is_premium_display"]
    
    fieldsets = [
        ("Informations utilisateur", {
            "fields": ["user", "telephone", "pays"],
        }),
        ("Statut Premium", {
            "fields": ["premium_until", "is_premium_display"],
        }),
        ("Profil détaillé", {
            "fields": ["avatar", "bio", "date_naissance", "genre"],
            "classes": ["collapse"],
        }),
        ("Métadonnées", {
            "fields": ["created_at", "updated_at", "nom_complet_display"],
            "classes": ["collapse"],
        }),
    ]
    
    @display(description="Premium", boolean=True)
    def is_premium_display(self, obj):
        return obj.is_premium
    
    @display(description="Nom complet")
    def nom_complet_display(self, obj):
        return obj.nom_complet
    
    def get_queryset(self, request):
        """Optimize queries by selecting related user."""
        return super().get_queryset(request).select_related("user")


# ==========================================
# 4. HISTORIQUE ET PAIEMENTS (Sécurité / Audit)
# ==========================================
@admin.register(Abonnement)
class AbonnementAdmin(ModelAdmin):
    list_display = ["user", "offre", "date_debut", "date_fin", "actif"]
    list_filter = ["actif", "date_fin"]
    search_fields = ["user__email", "offre__nom"]
    readonly_fields = ["date_debut"]
    list_editable = ["actif"]
    
    fieldsets = [
        ("Informations", {
            "fields": ["user", "offre", "actif"],
        }),
        ("Période", {
            "fields": ["date_debut", "date_fin"],
        }),
    ]


@admin.register(Paiement)
class PaiementAdmin(ModelAdmin):
    list_display = ["transaction_id_interne", "user", "offre", "statut", "montant_paye", "date_creation"]
    list_filter = ["statut", "date_creation"]
    search_fields = ["transaction_id_interne", "user__email", "reference_operateur"]
    readonly_fields = ["date_creation", "reponse_api_brute"]
    list_editable = ["statut"]
    
    fieldsets = [
        ("Transaction", {
            "fields": ["transaction_id_interne", "reference_operateur", "statut"],
        }),
        ("Détails", {
            "fields": ["user", "offre", "montant_paye"],
        }),
        ("Réponse API", {
            "fields": ["reponse_api_brute"],
            "classes": ["collapse", "monospace"],
        }),
        ("Métadonnées", {
            "fields": ["date_creation"],
            "classes": ["collapse"],
        }),
    ]


# ==========================================
# 5. CONTENU PÉDAGOGIQUE & IA (RAG)
# ==========================================
@admin.register(Video)
class VideoAdmin(ModelAdmin):
    list_display = ["titre", "is_free", "date_publication"]
    list_filter = ["is_free", "date_publication"]
    search_fields = ["titre", "description"]
    readonly_fields = ["date_publication"]
    list_editable = ["is_free"]
    
    fieldsets = [
        ("Informations", {
            "fields": ["titre", "description", "is_free"],
        }),
        ("Fichiers", {
            "fields": ["fichier_video", "miniature"],
        }),
        ("Métadonnées", {
            "fields": ["date_publication"],
            "classes": ["collapse"],
        }),
    ]


@admin.register(DocumentIA)
class DocumentIAAdmin(ModelAdmin):
    list_display = ["titre", "user", "taille_mb", "vector_id", "date_upload"]
    list_filter = ["date_upload"]
    search_fields = ["titre", "user__email"]
    readonly_fields = ["taille_mb", "date_upload"]
    
    fieldsets = [
        ("Informations", {
            "fields": ["titre", "user"],
        }),
        ("Fichier", {
            "fields": ["fichier_pdf", "taille_mb", "vector_id"],
        }),
        ("Métadonnées", {
            "fields": ["date_upload"],
            "classes": ["collapse"],
        }),
    ]


# ==========================================
# 6. INTERACTIONS SOCIALES
# ==========================================
@admin.register(Commentaire)
class CommentaireAdmin(ModelAdmin):
    list_display = ["user", "get_target", "created_at", "is_deleted", "likes_count_display"]
    list_filter = ["is_deleted", "created_at"]
    search_fields = ["user__email", "contenu"]
    readonly_fields = ["created_at", "updated_at", "likes_count_display"]
    list_editable = ["is_deleted"]
    
    fieldsets = [
        ("Commentaire", {
            "fields": ["user", "contenu"],
        }),
        ("Cible", {
            "fields": ["video", "document"],
        }),
        ("Réponse", {
            "fields": ["parent"],
            "classes": ["collapse"],
        }),
        ("Statut", {
            "fields": ["is_deleted"],
        }),
        ("Métadonnées", {
            "fields": ["created_at", "updated_at", "likes_count_display"],
            "classes": ["collapse"],
        }),
    ]
    
    @display(description="Cible")
    def get_target(self, obj):
        return obj.video or obj.document
    
    @display(description="Likes")
    def likes_count_display(self, obj):
        return obj.likes_count


@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display = ["user", "get_target", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at"]
    
    fieldsets = [
        ("Like", {
            "fields": ["user"],
        }),
        ("Cible", {
            "fields": ["commentaire", "video", "document"],
        }),
        ("Métadonnées", {
            "fields": ["created_at"],
            "classes": ["collapse"],
        }),
    ]
    
    @display(description="Cible")
    def get_target(self, obj):
        return obj.commentaire or obj.video or obj.document
