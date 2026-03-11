"""
Tests unitaires pour le système de paiement OpenPay
"""

import json
from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import (
    OffreAbonnement, Paiement, Profile, Abonnement
)
from core.openpay_service import OpenPayService, openpay_service

User = get_user_model()


class OpenPayServiceTest(TestCase):
    """Tests pour le service OpenPay"""
    
    def setUp(self):
        self.service = OpenPayService()
        self.test_phone = "242066203420"
        self.test_customer_id = "TEST_USER_001"
    
    def test_service_initialization(self):
        """Le service s'initialise correctement"""
        self.assertIsNotNone(self.service.base_url)
        self.assertIn("Content-Type", self.service.headers)
        self.assertEqual(self.service.headers["Content-Type"], "application/json")
    
    def test_creer_paylink_payload_structure(self):
        """Vérifie que la méthode creer_paylink prépare correctement les données"""
        # Test avec les paramètres minimaux
        result = self.service.creer_paylink(
            montant=1000,
            telephone=self.test_phone,
            customer_external_id=self.test_customer_id
        )
        
        # Le résultat doit contenir les clés attendues
        self.assertIn("success", result)
        self.assertIn("status", result)
    
    def test_creer_paylink_with_all_params(self):
        """Test avec tous les paramètres"""
        customer_info = {
            "name": "Jean Dupont",
            "phone": self.test_phone,
            "email": "jean@example.com"
        }
        metadata = {
            "order_id": "CMD_001",
            "user_id": 1,
            "offre_id": 1
        }
        
        result = self.service.creer_paylink(
            montant=2500,
            telephone=self.test_phone,
            customer_external_id=self.test_customer_id,
            customer_info=customer_info,
            metadata=metadata,
            redirect_url="http://localhost:8000/paiement/complet/"
        )
        
        self.assertIn("success", result)
    
    def test_verifier_signature_webhook(self):
        """La vérification de signature retourne True par défaut"""
        result = self.service.verifier_signature_webhook("payload", "signature")
        self.assertTrue(result)


class OffreAbonnementTest(TestCase):
    """Tests pour le modèle OffreAbonnement"""
    
    def setUp(self):
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Test",
            prix=5000,
            duree_jours=60,
            can_access_videos=True,
            can_access_books=True,
            can_use_ai_chat=False,
            storage_limit_mb=0
        )
    
    def test_offre_creation(self):
        """Une offre peut être créée"""
        self.assertEqual(self.offre.nom, "Pack Test")
        self.assertEqual(self.offre.prix, 5000)
        self.assertEqual(self.offre.duree_jours, 60)
        self.assertTrue(self.offre.can_access_videos)
        self.assertTrue(self.offre.can_access_books)
        self.assertFalse(self.offre.can_use_ai_chat)
    
    def test_offre_str(self):
        """La représentation string d'une offre est correcte"""
        self.assertEqual(str(self.offre), "Pack Test - 5000")


class PaiementModelTest(TestCase):
    """Tests pour le modèle Paiement"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Premium",
            prix=15000,
            duree_jours=365
        )
        self.paiement = Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_TEST_001",
            montant_paye=15000,
            statut="PENDING"
        )
    
    def test_paiement_creation(self):
        """Un paiement peut être créé"""
        self.assertEqual(self.paiement.user, self.user)
        self.assertEqual(self.paiement.offre, self.offre)
        self.assertEqual(self.paiement.statut, "PENDING")
        self.assertEqual(self.paiement.montant_paye, 15000)
    
    def test_paiement_str(self):
        """La représentation string d'un paiement est correcte"""
        self.assertIn("TXN_TEST_001", str(self.paiement))
        self.assertIn("15000", str(self.paiement))
    
    def test_marquer_comme_succes(self):
        """Un paiement marqué comme succès active l'abonnement"""
        self.paiement.marquer_comme_succes(
            reference_operateur="PTXN_TEST_123",
            reponse_api={"status": "success"}
        )
        
        self.assertEqual(self.paiement.statut, "SUCCESS")
        self.assertEqual(self.paiement.reference_operateur, "PTXN_TEST_123")
        self.assertIsNotNone(self.paiement.date_confirmation)
        
        # Vérifier que le profil est mis à jour
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.is_premium)
        self.assertIsNotNone(profile.premium_until)
        
        # Vérifier que l'abonnement est créé
        abonnement = Abonnement.objects.filter(user=self.user).first()
        self.assertIsNotNone(abonnement)
        self.assertTrue(abonnement.actif)
    
    def test_marquer_comme_echec(self):
        """Un paiement marqué comme échec update le statut"""
        self.paiement.marquer_comme_echec(reponse_api={"status": "failed"})
        
        self.assertEqual(self.paiement.statut, "FAILED")


class PaiementViewTest(TestCase):
    """Tests pour les vues de paiement"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="payuser",
            email="pay@example.com",
            password="pass123"
        )
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Découverte",
            prix=2500,
            duree_jours=30
        )
        
    def test_initier_paiement_requires_login(self):
        """La vue de paiement nécessite d'être connecté"""
        response = self.client.get(reverse('initier_paiement', args=[self.offre.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/connexion/', response.url)
    
    def test_initier_paiement_get_shows_form(self):
        """GET affiche le formulaire de paiement"""
        self.client.login(username="payuser", password="pass123")
        response = self.client.get(reverse('initier_paiement', args=[self.offre.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paiement")
        self.assertContains(response, str(self.offre.prix))
    
    def test_initier_paiement_post_invalid_phone(self):
        """POST avec numéro invalide affiche une erreur"""
        self.client.login(username="payuser", password="pass123")
        response = self.client.post(reverse('initier_paiement', args=[self.offre.id]), {
            'telephone': '123',  # Numéro trop court
            'provider': 'MTN'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_initier_paiement_post_valid_data(self):
        """POST avec données valides crée un paiement"""
        self.client.login(username="payuser", password="pass123")
        response = self.client.post(reverse('initier_paiement', args=[self.offre.id]), {
            'telephone': '066203420',
            'provider': 'MTN'
        }, follow=True)
        
        # Vérifier qu'un paiement a été créé
        paiement = Paiement.objects.filter(user=self.user).first()
        self.assertIsNotNone(paiement)
        self.assertEqual(paiement.offre, self.offre)
        self.assertEqual(paiement.statut, 'PENDING')
    
    def test_paiement_complet_view(self):
        """La vue paiement_complet affiche le statut"""
        self.client.login(username="payuser", password="pass123")
        
        # Créer un paiement test
        Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_TEST",
            montant_paye=2500,
            statut="PENDING"
        )
        
        response = self.client.get(reverse('paiement_complet'))
        self.assertEqual(response.status_code, 200)


class WebhookTest(TestCase):
    """Tests pour le webhook OpenPay"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="webhookuser",
            email="webhook@example.com",
            password="pass123"
        )
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Test",
            prix=1000,
            duree_jours=30
        )
        self.paiement = Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_WEBHOOK_TEST",
            montant_paye=1000,
            statut="PENDING",
            customer_external_id=f"USER_{self.user.id}"
        )
    
    def test_webhook_success_updates_paiement(self):
        """Un webhook succès met à jour le paiement"""
        payload = {
            "reference": "PTXN_WEBHOOK_123",
            "status": "success",
            "amount": "1000",
            "metadata": {
                "paiement_id": self.paiement.id
            }
        }
        
        response = self.client.post(
            reverse('webhook_openpay'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Rafraîchir le paiement depuis la BDD
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.statut, "SUCCESS")
        self.assertEqual(self.paiement.reference_operateur, "PTXN_WEBHOOK_123")
    
    def test_webhook_failed_updates_paiement(self):
        """Un webhook échec met à jour le paiement"""
        payload = {
            "reference": "PTXN_FAILED",
            "status": "failed",
            "metadata": {
                "paiement_id": self.paiement.id
            }
        }
        
        response = self.client.post(
            reverse('webhook_openpay'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.statut, "FAILED")
    
    def test_webhook_invalid_json(self):
        """Un JSON invalide retourne une erreur"""
        response = self.client.post(
            reverse('webhook_openpay'),
            data="invalid json",
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_webhook_missing_paiement_id(self):
        """Un webhook sans paiement_id retourne une erreur"""
        payload = {
            "reference": "PTXN_TEST",
            "status": "success",
            "metadata": {}
        }
        
        response = self.client.post(
            reverse('webhook_openpay'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Le webhook retourne 404 car le paiement n'est pas trouvé
        self.assertEqual(response.status_code, 404)


class DashboardWithPaiementsTest(TestCase):
    """Tests pour le dashboard avec l'historique des paiements"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="dashuser",
            email="dash@example.com",
            password="pass123"
        )
        # Créer les offres pour le dashboard
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Dashboard",
            prix=5000,
            duree_jours=60
        )
    
    def test_dashboard_shows_paiements_history(self):
        """Le dashboard affiche l'historique des paiements"""
        self.client.login(username="dashuser", password="pass123")
        
        # Créer des paiements de test
        Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_001",
            montant_paye=5000,
            statut="SUCCESS"
        )
        Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_002",
            montant_paye=5000,
            statut="PENDING"
        )
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historique des paiements")
        self.assertContains(response, "TXN_001")
        self.assertContains(response, "TXN_002")
    
    def test_dashboard_shows_offres(self):
        """Le dashboard affiche les offres disponibles"""
        self.client.login(username="dashuser", password="pass123")
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pack Dashboard")
        self.assertContains(response, "5000")


class ProfilePremiumTest(TestCase):
    """Tests pour la gestion du statut Premium"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="premiumuser",
            email="premium@example.com",
            password="pass123"
        )
        # Utiliser get_or_create pour éviter les conflits
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Premium Test",
            prix=15000,
            duree_jours=365
        )
    
    def test_is_premium_false_by_default(self):
        """Un utilisateur n'est pas premium par défaut"""
        self.assertFalse(self.profile.is_premium)
    
    def test_is_premium_true_after_payment(self):
        """Un utilisateur devient premium après un paiement succès"""
        paiement = Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_PREMIUM",
            montant_paye=15000,
            statut="PENDING"
        )
        
        paiement.marquer_comme_succes()
        
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_premium)
        self.assertIsNotNone(self.profile.premium_until)
    
    def test_premium_expires_correctly(self):
        """Le premium expire après la date prévue"""
        paiement = Paiement.objects.create(
            user=self.user,
            offre=self.offre,
            transaction_id_interne="TXN_EXPIRE",
            montant_paye=15000,
            statut="PENDING"
        )
        
        # Définir une date d'expiration dans le passé
        self.profile.premium_until = timezone.now() - timedelta(days=1)
        self.profile.save()
        
        self.assertFalse(self.profile.is_premium)


# Tests d'intégration
class IntegrationPaiementFlowTest(TestCase):
    """Tests d'intégration du flux complet de paiement"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="flowuser",
            email="flow@example.com",
            password="pass123"
        )
        self.offre = OffreAbonnement.objects.create(
            nom="Pack Intégration",
            prix=10000,
            duree_jours=180,
            can_access_videos=True,
            can_access_books=True,
            can_use_ai_chat=True
        )
    
    def test_complete_payment_flow(self):
        """Test du flux complet: initiation -> webhook -> activation"""
        # 1. Connexion
        self.client.login(username="flowuser", password="pass123")
        
        # 2. Initier le paiement
        response = self.client.post(reverse('initier_paiement', args=[self.offre.id]), {
            'telephone': '066203420',
            'provider': 'MTN'
        }, follow=True)
        
        # 3. Vérifier que le paiement a été créé
        paiement = Paiement.objects.filter(
            user=self.user, 
            offre=self.offre
        ).first()
        self.assertIsNotNone(paiement)
        self.assertEqual(paiement.statut, 'PENDING')
        
        # 4. Simuler le webhook de succès
        webhook_payload = {
            "reference": "PTXN_FLOW_TEST",
            "status": "success",
            "amount": "10000",
            "metadata": {
                "paiement_id": paiement.id
            }
        }
        
        self.client.post(
            reverse('webhook_openpay'),
            data=json.dumps(webhook_payload),
            content_type='application/json'
        )
        
        # 5. Vérifier que le paiement est maintenant succès
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, 'SUCCESS')
        
        # 6. Vérifier que l'utilisateur est premium
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.is_premium)
        
        # 7. Vérifier que l'abonnement est actif
        abonnement = Abonnement.objects.filter(user=self.user).first()
        self.assertIsNotNone(abonnement)
        self.assertTrue(abonnement.actif)


# Helpers de test
def create_test_offres():
    """Helper pour créer les offres de test"""
    offres_data = [
        {"nom": "Pack Découverte", "prix": 2500, "duree_jours": 30},
        {"nom": "Pack Étudiant", "prix": 10000, "duree_jours": 180},
        {"nom": "Pack Premium", "prix": 15000, "duree_jours": 365},
        {"nom": "Pack Famille", "prix": 25000, "duree_jours": 365},
    ]
    
    created = []
    for data in offres_data:
        offre, created_flag = OffreAbonnement.objects.get_or_create(
            nom=data["nom"],
            defaults={
                "prix": data["prix"],
                "duree_jours": data["duree_jours"],
                "can_access_videos": True,
                "can_access_books": True,
                "can_use_ai_chat": data["prix"] >= 10000,
                "storage_limit_mb": 0 if data["prix"] < 10000 else 100
            }
        )
        created.append(offre)
    
    return created
