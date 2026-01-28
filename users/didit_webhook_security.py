"""
Webhook signature verification helper for Didit.me
"""

import hmac
import hashlib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def verify_didit_webhook_signature(request):
    """
    Verify webhook signature to ensure request is from Didit.me.
    
    Didit.me signs webhooks using HMAC-SHA256 with your webhook secret.
    The signature is sent in the 'X-Didit-Signature' header.
    
    Args:
        request: Django request object
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    webhook_secret = getattr(settings, 'DIDIT_WEBHOOK_SECRET', '')
    
    # Skip verification if webhook secret not configured (dev mode)
    if not webhook_secret:
        logger.warning("Webhook secret not configured - skipping signature verification")
        return True
    
    # Get signature from header
    signature_header = request.META.get('HTTP_X_DIDIT_SIGNATURE', '')
    
    if not signature_header:
        logger.warning("No signature header found in webhook request")
        return False
    
    # Get raw request body
    try:
        raw_body = request.body
    except Exception as e:
        logger.error(f"Failed to get request body: {str(e)}")
        return False
    
    # Compute expected signature
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison to prevent timing attacks)
    is_valid = hmac.compare_digest(signature_header, expected_signature)
    
    if not is_valid:
        logger.warning(
            f"Signature mismatch - Expected: {expected_signature[:10]}..., "
            f"Got: {signature_header[:10]}..."
        )
    
    return is_valid
