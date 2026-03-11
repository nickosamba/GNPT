"""Services OpenPay"""

import requests
import json
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

OPENPAY_API_URL = os.environ.get("OPENPAY_API_URL", "https://api.openpay-cg.com/v1")
OPENPAY_API_KEY = os.environ.get("OPENPAY_API_KEY", "")
OPENPAY_SECRET_KEY = os.environ.get("OPENPAY_SECRET_KEY", "")
API_TIMEOUT = 30


class OpenPayError(Exception):
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class OpenPayService:
    def __init__(self):
        self.base_url = OPENPAY_API_URL
        self.headers = {
            "XO-API-KEY": OPENPAY_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def creer_paylink(self, montant: int, description: str, customer: dict = None, metadata: dict = None, expires_at: int = 24, success_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        url = f"{self.base_url}/payment-link"
        payload = {"amount": montant, "description": description, "expires_at": expires_at, "metadata": metadata or {}}
        if customer: payload["customer"] = customer
        if success_url: payload["success_url"] = success_url
        if cancel_url: payload["cancel_url"] = cancel_url

        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=API_TIMEOUT)
            if response.status_code not in [200, 201]:
                raise OpenPayError(message="Erreur API OpenPay", status_code=response.status_code)
            result = response.json()
            if result.get("success"):
                data = result.get("data", {})
                return {"success": True, "payment_token": data.get("payment_token"), "payment_url": data.get("payment_url"), "reference": data.get("reference"), "status": data.get("status", "pending"), "data": data}
            return {"success": False, "error": result.get("message", "Erreur inconnue")}
        except requests.exceptions.Timeout:
            raise OpenPayError("Timeout API OpenPay")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            raise OpenPayError(message=f"Erreur HTTP: {e}", status_code=status_code)
        except requests.exceptions.RequestException as e:
            raise OpenPayError(message=f"Erreur de connexion: {str(e)}")
        except Exception as e:
            raise OpenPayError(message=str(e))
    
    def verifier_statut(self, reference: str) -> Dict[str, Any]:
        url = f"{self.base_url}/transaction/status/{reference}"
        try:
            response = requests.get(url, headers=self.headers, timeout=API_TIMEOUT)
            if response.status_code == 404:
                raise OpenPayError(f"Transaction non trouvee: {reference}", status_code=404)
            if response.status_code != 200:
                raise OpenPayError("Erreur API OpenPay", status_code=response.status_code)
            result = response.json()
            return {"success": True, "status": result.get("status"), "reference": result.get("reference"), "amount": result.get("amount"), "metadata": result.get("metadata"), "data": result}
        except OpenPayError:
            raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            raise OpenPayError(message=f"Erreur HTTP: {e}", status_code=status_code)
        except requests.exceptions.Timeout:
            raise OpenPayError("Timeout API OpenPay")
        except requests.exceptions.RequestException as e:
            raise OpenPayError(message=f"Erreur de connexion: {str(e)}")
        except Exception as e:
            raise OpenPayError(message=str(e))
    
    @staticmethod
    def verifier_signature_webhook(payload_recu: str, signature_entete: str) -> bool:
        if not OPENPAY_SECRET_KEY:
            return True
        return True


openpay_service = OpenPayService()
