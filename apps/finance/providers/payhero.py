"""
PayHero payment provider boundary.

This module is the ONLY place that talks to the PayHero API.
It has NO ORM imports and NO Django model imports.
All exceptions raised here use PayHeroError, imported from services.
"""
import hashlib
import hmac
import os
from decimal import Decimal

import requests as _requests

# PayHeroError is defined in apps/finance/services to avoid circular imports.
# Import it lazily inside functions when needed.


def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify a PayHero webhook callback using HMAC-SHA256.

    Reads PAYHERO_WEBHOOK_SECRET from the environment.
    Uses hmac.compare_digest() for constant-time comparison.
    Returns True if valid, False otherwise (including empty secret).
    """
    secret = os.environ.get('PAYHERO_WEBHOOK_SECRET', '')
    if not secret:
        # If no secret configured, reject all webhooks in production.
        # In development (secret=''), this will always return False — configure the secret.
        return False

    expected = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # constant-time comparison
    return hmac.compare_digest(expected, signature_header or '')


def initiate_stk_push(phone: str, amount, reference: str, callback_url: str) -> dict:
    """
    Initiate an M-Pesa STK push via the PayHero API.

    Reads PAYHERO_API_KEY and PAYHERO_CHANNEL_ID from the environment.
    Returns the raw JSON response dict on success.
    Raises PayHeroError on any HTTP error or network failure.
    """
    from apps.finance.services import PayHeroError

    api_key = os.environ.get('PAYHERO_API_KEY', '')
    channel_id = os.environ.get('PAYHERO_CHANNEL_ID', '')

    if not api_key or not channel_id:
        raise PayHeroError(
            'PayHero is not configured. Set PAYHERO_API_KEY and PAYHERO_CHANNEL_ID.'
        )

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'amount': int(Decimal(str(amount))),   # PayHero expects integer cents/KES
        'phone_number': phone,
        'channel_id': channel_id,
        'provider': 'm-pesa',
        'external_reference': reference,
        'callback_url': callback_url,
    }

    try:
        response = _requests.post(
            'https://backend.payhero.co.ke/api/v2/payments',
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except _requests.exceptions.HTTPError as exc:
        raise PayHeroError(
            f'PayHero API returned HTTP {exc.response.status_code}: {exc.response.text[:200]}'
        ) from exc
    except _requests.exceptions.RequestException as exc:
        raise PayHeroError(f'PayHero API network error: {exc}') from exc
