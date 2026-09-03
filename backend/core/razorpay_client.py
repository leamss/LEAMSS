"""Razorpay Client for LEAMSS Portal.

Direct, reliable implementation of Razorpay API with:
- Orders API (create order)
- Utility (verify_payment_signature with HMAC SHA256)
- SSL-resilient transport for Windows environments
"""
import os
import hmac
import hashlib
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SignatureVerificationError(Exception):
    pass


class RazorpayErrors:
    SignatureVerificationError = SignatureVerificationError


class RazorpayOrder:
    def __init__(self, key_id: str, key_secret: str, base_url: str = "https://api.razorpay.com/v1"):
        self.key_id = key_id
        self.key_secret = key_secret
        self.base_url = base_url

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(verify=False, auth=(self.key_id, self.key_secret), timeout=30.0) as client:
            resp = client.post(f"{self.base_url}/orders", json=data)
            if resp.status_code not in (200, 201):
                logger.error("Razorpay order creation failed: %s", resp.text)
                raise Exception(f"Razorpay API Error ({resp.status_code}): {resp.text}")
            return resp.json()


class RazorpayUtility:
    def __init__(self, key_secret: str):
        self.key_secret = key_secret

    def verify_payment_signature(self, data: Dict[str, str]) -> bool:
        order_id = data.get("razorpay_order_id", "")
        payment_id = data.get("razorpay_payment_id", "")
        signature = data.get("razorpay_signature", "")

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        secret = self.key_secret.encode("utf-8")
        expected_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            raise SignatureVerificationError("Payment signature verification failed")
        return True


class RazorpayClient:
    errors = RazorpayErrors

    def __init__(self, key_id: str = None, key_secret: str = None):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "")
        self.order = RazorpayOrder(self.key_id, self.key_secret)
        self.utility = RazorpayUtility(self.key_secret)

    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)


# Global helper instance
def get_razorpay_client() -> RazorpayClient:
    key_id = os.environ.get("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret:
        return None
    return RazorpayClient(key_id, key_secret)
