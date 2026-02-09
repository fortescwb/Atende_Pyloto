"""Constantes criptográficas para WhatsApp Flows."""

AES_KEY_SIZE = 16  # 128 bits (padrão dos payloads de data_exchange)
AES_KEY_SIZES_ALLOWED = (16, 24, 32)  # 128/192/256 bits
IV_SIZE = 12  # 96 bits (recomendado para GCM)
TAG_SIZE = 16  # 128 bits
