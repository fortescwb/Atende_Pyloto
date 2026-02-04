"""Constantes criptográficas para WhatsApp Flows.

Definido em app/infra para manter boundaries corretas.
"""

AES_KEY_SIZE = 32  # 256 bits
IV_SIZE = 12  # 96 bits (recomendado para GCM)
TAG_SIZE = 16  # 128 bits
