"""
Service OpenPay - Intégration API de paiement Mobile Money
Documentation officielle: https://api.openpay-cg.com

Endpoints:
- POST /v1/transaction/payment - Initier un paiement direct
- POST /v1/payment-link - Créer un lien de paiement (PayLink)
- GET /v1/transaction/status/:reference - Vérifier le statut
"""

import requests
import json
import logging
import os
from decouple import config
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configuration OpenPay - Cherche le fichier .env à la racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

OPENPAY_API_URL = config("OPENPAY_API_URL", default="https://api.openpay-cg.com/v1")
OPENPAY_API_KEY = config("OPENPAY_API_KEY", default="")
OPENPAY_SECRET_KEY = config("OPENPAY_SECRET_KEY", default="")

# Vérifier la configuration au démarrage
if not OPENPAY_API_KEY:
    logger.warning("⚠️ OPENPAY_API_KEY non configuré - Les paiements ne fonctionneront pas !")
    logger.warning("Définissez OPENPAY_API_KEY dans vos variables d'environnement")


class OpenPayError(Exception):
    """Exception pour les erreurs OpenPay"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OpenPayService:
    """
    Service pour interagir avec l'API OpenPay.
    Authentification via header: XO-API-KEY
    """
    
    def __init__(self):
        self.base_url = OPENPAY_API_URL
        # Headers requis par OpenPay
        self.headers = {
            "XO-API-KEY": OPENPAY_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def creer_paylink(self, montant, description, customer=None, metadata=None,
                      expires_at=24, success_url=None, cancel_url=None):
        """
        Crée un lien de paiement (PayLink) OpenPay avec formulaire intégré.

        Args:
            montant (int): Montant en XAF
            description (str): Description du paiement
            customer (dict): Infos client {name, phone, email}
            metadata (dict): Métadonnées pour le suivi (paiement_id, user_id, etc.)
            expires_at (int): Durée de validité en heures (défaut: 24h)
            success_url (str): URL de redirection après succès
            cancel_url (str): URL de redirection après annulation

        Returns:
            dict: {
                'success': bool,
                'payment_token': str,
                'payment_url': str,
                'reference': str,
                'status': str,
                'error': str (si échec)
            }
        """
        url = f"{self.base_url}/payment-link"

        payload = {
            "amount": montant,
            "description": description,
            "expires_at": expires_at,  # en heures
            "metadata": metadata or {}
        }

        if customer:
            payload["customer"] = customer

        if success_url:
            payload["success_url"] = success_url

        if cancel_url:
            payload["cancel_url"] = cancel_url

        logger.info(f"Création PayLink: {montant} XAF - {description}")
        logger.info(f"URL: {url}")
        logger.info(f"Headers: XO-API-KEY={OPENPAY_API_KEY[:10] if OPENPAY_API_KEY else 'VIDE'}...")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )

            logger.info(f"Statut réponse: {response.status_code}")
            logger.info(f"Réponse brute: {response.text[:500] if response.text else 'VIDE'}")
            
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                data = result.get("data", {})
                logger.info(f"PayLink créé avec succès: {data.get('payment_token')}")

                return {
                    "success": True,
                    "payment_token": data.get("payment_token"),
                    "payment_url": data.get("payment_url"),
                    "reference": data.get("reference"),
                    "status": data.get("status", "pending"),
                    "amount": data.get("amount"),
                    "expires_at": data.get("expires_at"),
                    "data": data
                }
            else:
                logger.error(f"Échec création PayLink: {result}")
                raise OpenPayError(message=result.get("message", "Erreur inconnue"))

        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP: {e}")
            logger.error(f"Réponse erreur: {e.response.text if e.response else 'Aucune réponse'}")
            error_detail = self._parse_error_response(e.response)
            status_code = e.response.status_code if e.response else None
            raise OpenPayError(message=f"Erreur API: {error_detail}", status_code=status_code)
        except requests.exceptions.Timeout:
            logger.error("Timeout API OpenPay")
            raise OpenPayError(message="Timeout API OpenPay")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de connexion: {str(e)}")
            raise OpenPayError(message=f"Erreur de connexion: {str(e)}")
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            raise OpenPayError(message=str(e))
    
    def initier_paiement_direct(self, montant, payment_phone_number, provider="MTN",
                                 customer_external_id=None, customer=None, metadata=None):
        """
        Initie un paiement direct (sans PayLink).
        Utilise l'endpoint /v1/transaction/payment
        
        Args:
            montant (int): Montant en XAF
            payment_phone_number (str): Numéro de téléphone (format: 242XXXXXXXXX)
            provider (str): Opérateur (MTN, AIRTEL, MOOV)
            customer_external_id (str): ID unique du client dans votre système
            customer (dict): Infos client {name, phone}
            metadata (dict): Métadonnées
        
        Returns:
            dict: {
                'success': bool,
                'reference': str,
                'status': str,
                'error': str (si échec)
            }
        """
        url = f"{self.base_url}/transaction/payment"
        
        payload = {
            "amount": str(montant),
            "payment_phone_number": payment_phone_number,
            "provider": provider
        }
        
        if customer_external_id:
            payload["customer_external_id"] = customer_external_id
        
        if customer:
            payload["customer"] = customer
        
        if metadata:
            payload["metadata"] = metadata
        
        logger.info(f"Paiement direct: {montant} XAF - {payment_phone_number}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "reference": result.get("reference"),
                "status": result.get("status"),
                "type": result.get("type"),
                "data": result
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP: {e}")
            error_detail = self._parse_error_response(e.response)
            return {
                "success": False,
                "error": f"Erreur API: {error_detail}",
                "status": "failed"
            }
        except Exception as e:
            logger.error(f"Erreur: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    def verifier_statut(self, reference):
        """
        Vérifie le statut d'une transaction par sa référence.
        GET /v1/transaction/status/:reference
        
        Args:
            reference (str): Référence de la transaction (ex: PTXN26042237B99A5D9)
        
        Returns:
            dict: {
                'success': bool,
                'status': str (pending, success, failed, cancelled),
                'data': dict (détails complets)
            }
        """
        url = f"{self.base_url}/transaction/status/{reference}"
        
        logger.info(f"Vérification statut: {reference}")
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "status": result.get("status"),
                "reference": result.get("reference"),
                "amount": result.get("amount"),
                "provider": result.get("provider"),
                "metadata": result.get("metadata"),
                "data": result
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP: {e}")
            return {
                "success": False,
                "error": f"Erreur API: {e.response.status_code}",
                "status": "unknown"
            }
        except Exception as e:
            logger.error(f"Erreur: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status": "unknown"
            }
    
    def _parse_error_response(self, response):
        """Extrait les détails d'une réponse d'erreur"""
        try:
            error_data = response.json()
            return error_data.get("message", error_data.get("error", "Erreur inconnue"))
        except:
            return f"Statut {response.status_code}"
    
    @staticmethod
    def verifier_signature_webhook(payload_recu, signature_entete):
        """
        Vérifie la signature du webhook OpenPay.
        En production, utiliser HMAC-SHA256 avec OPENPAY_SECRET_KEY.
        
        Args:
            payload_recu (str): Body brut de la requête
            signature_entete (str): Signature reçue dans le header
        
        Returns:
            bool: True si la signature est valide
        """
        if not OPENPAY_SECRET_KEY:
            logger.warning("OPENPAY_SECRET_KEY non configuré - signature non vérifiée")
            return True
        
        # TODO: Implémenter la vérification HMAC selon la doc OpenPay
        # import hmac
        # import hashlib
        # signature_calculee = hmac.new(
        #     OPENPAY_SECRET_KEY.encode(),
        #     payload_recu.encode(),
        #     hashlib.sha256
        # ).hexdigest()
        # return hmac.compare_digest(signature_calculee, signature_entete)
        
        return True


# Instance globale du service
openpay_service = OpenPayService()
