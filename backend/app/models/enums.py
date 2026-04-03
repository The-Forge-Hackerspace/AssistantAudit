"""
Enums partages entre les modeles.
"""

from enum import Enum


class AuthMethod(str, Enum):
    DEVICE_CODE = "device_code"
    CERTIFICATE = "certificate"
    CLIENT_SECRET = "client_secret"
    # INTERACTIVE supprime — pas possible sur Ubuntu headless
