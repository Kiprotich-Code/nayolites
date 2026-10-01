import hashlib
import hmac
import os
from decimal import Decimal

# PayHeroError is defined in apps/finance/services.py and imported there


def initiate_stk_push(phone: str, amount, reference: str, callback_url: str) -> dict:
    """
    POST to PayHero /v2/payments to initiate an M-Pesa STK push.

    Reads PAYHERO_API_KEY and PAYHERO_CHANNEL_ID from environment variables.
    Returns the raw JSON response dict on success.
    Raises PayHeroError (imported from apps/finance/services) on HTTP error
    or network failure.

    No ORM imports — this module is a pure provider boundary with no DB access.
    """
    pass


def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify a PayHero webhook callback signature using HMAC-SHA256.

    Reads PAYHERO_WEBHOOK_SECRET from environment variables and computes the
    expected HMAC-SHA256 digest of payload_bytes. Compares it against
    signature_header using hmac.compare_digest() for constant-time comparison
    to prevent timing attacks.

    Returns True if the signature is valid, False otherwise.
    Defaults to False (safe default) until fully implemented in Phase 6.
    """
    return False
