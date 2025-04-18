import hmac
import hashlib
import os

def validate_mercadopago_signature(body, signature):
    """
    Valida a assinatura HMAC SHA256 enviada pelo Mercado Pago.

    OBS: Essa é uma versão genérica. Mercado Pago ainda não envia assinatura
    HMAC por padrão, então essa função é um placeholder.
    """
    # Exemplo: use sua chave secreta para verificar (caso a MP fornecesse)
    secret = os.getenv('MERCADOPAGO_WEBHOOK_SECRET', 'default-secret')
    expected_signature = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)
