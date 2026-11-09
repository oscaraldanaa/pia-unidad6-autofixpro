"""Generación de identificadores de texto (``str``), no UUID."""
import secrets

LONGITUD_MAXIMA = 36   # coincide con la columna String(36) de la BD


def generar_id(prefijo: str) -> str:
    """Ej.: ``ORD-9F2C41AB07D3E856`` (prefijo legible + 64 bits aleatorios)."""
    return f"{prefijo}-{secrets.token_hex(8).upper()}"
