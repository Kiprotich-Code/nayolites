"""
PayHero webhook callback view.
Public endpoint — no login required.
Security is via HMAC-SHA256 signature verification.
"""
import json
import logging
from decimal import Decimal

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.finance.providers.payhero import verify_webhook_signature
from apps.finance.services import process_payhero_callback

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class PayHeroCallbackView(View):
    """
    POST /finance/callbacks/payhero/

    Steps:
    1. Read raw request body.
    2. Verify HMAC-SHA256 signature → HTTP 400 on failure (no processing).
    3. Parse JSON payload.
    4. Call process_payhero_callback() → HTTP 200.
    5. Unexpected exceptions → HTTP 500 (logged, not exposed to caller).
    """

    def post(self, request):
        raw_body = request.body

        # Step 2: signature verification
        signature_header = request.META.get('HTTP_X_PAYHERO_SIGNATURE', '')
        if not verify_webhook_signature(raw_body, signature_header):
            logger.warning(
                'PayHero callback rejected: invalid HMAC signature. '
                'IP=%s', request.META.get('REMOTE_ADDR'),
            )
            return HttpResponse('Invalid signature', status=400)

        # Step 3: parse JSON
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning('PayHero callback: invalid JSON — %s', exc)
            return HttpResponse('Invalid payload', status=400)

        # Extract standard fields (PayHero callback schema)
        provider_tx_id = (
            payload.get('reference')
            or payload.get('CheckoutRequestID')
            or payload.get('id', '')
        )
        status = payload.get('status', '')
        amount = payload.get('amount', 0)
        provider_reference = payload.get('MpesaReceiptNumber') or payload.get('provider_reference', '')

        if not provider_tx_id:
            logger.warning('PayHero callback: missing transaction ID')
            return HttpResponse('Missing transaction reference', status=400)

        # Step 4: process
        try:
            process_payhero_callback(
                provider_tx_id=str(provider_tx_id),
                status=str(status),
                amount=Decimal(str(amount)),
                provider_reference=str(provider_reference),
                raw_payload=payload,
            )
        except ValueError as exc:
            # Unknown transaction — log and acknowledge to stop retries
            logger.error('PayHero callback ValueError: %s', exc)
            return HttpResponse('OK', status=200)
        except Exception as exc:
            logger.exception('PayHero callback unexpected error: %s', exc)
            return HttpResponse('Internal server error', status=500)

        return HttpResponse('OK', status=200)
