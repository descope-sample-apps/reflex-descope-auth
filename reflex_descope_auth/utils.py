import secrets
import hashlib
import base64

def generate_code_verifier(length: int = 48) -> str:
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_code_challenge(verifier: str) -> str:
    sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256_hash).rstrip(b'=').decode('utf-8')
