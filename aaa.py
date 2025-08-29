import secrets

pepper = secrets.token_urlsafe(32)
print(pepper)