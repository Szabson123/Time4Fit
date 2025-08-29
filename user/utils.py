import os, hmac, hashlib, secrets
from datetime import timedelta
from django.utils import timezone


PEPPER = os.environ["OTP_PEPPER"]
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

def gen_code(length=6):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))

def hmac_code(code: str):
    norm = code.strip().upper()
    return hmac.new(PEPPER.encode(), norm.encode(), hashlib.sha256).hexdigest()

def default_expires(ttl=500):
    return timezone.now() + timedelta(seconds=ttl)