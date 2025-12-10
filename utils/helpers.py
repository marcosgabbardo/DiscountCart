"""
Helper utilities for DiscountCart Price Monitor.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple
from urllib.parse import urlparse


def parse_price(price_str: str) -> Optional[Decimal]:
    """
    Parse a price string to Decimal.
    Handles formats like: R$80,99 | R$ 80.99 | 80,99 | 80.99 | 1.234,56

    Args:
        price_str: Price string to parse

    Returns:
        Decimal value or None if parsing fails
    """
    if not price_str:
        return None

    # Remove currency symbols, spaces, and common prefixes
    cleaned = price_str.strip()
    cleaned = cleaned.replace('R', '').replace('$', '').replace(' ', '')

    if not cleaned:
        return None

    # Check for shell variable expansion issue
    if cleaned.startswith(',') or cleaned.startswith('.'):
        return None

    has_comma = ',' in cleaned
    has_dot = '.' in cleaned

    if has_comma and has_dot:
        comma_pos = cleaned.rfind(',')
        dot_pos = cleaned.rfind('.')

        if comma_pos > dot_pos:
            # Brazilian format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US format: 1,234.56
            cleaned = cleaned.replace(',', '')

    elif has_comma:
        cleaned = cleaned.replace(',', '.')

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def format_currency(value: Optional[Decimal], currency: str = 'R$') -> str:
    """
    Format a Decimal value as currency string.

    Args:
        value: Decimal value to format
        currency: Currency symbol (default: R$)

    Returns:
        Formatted currency string
    """
    if value is None:
        return f"{currency} --"

    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')

    return f"{currency} {formatted}"


def truncate_string(text: Optional[str], max_length: int = 50, suffix: str = '...') -> str:
    """
    Truncate a string to max length with suffix.
    """
    if not text:
        return ''

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """
    Format a float as percentage string.
    """
    if value is None:
        return '--%'

    return f"{value:.{decimals}f}%"


def validate_zaffari_url(url: str) -> bool:
    """
    Validate if URL is a valid Zaffari product URL.

    Args:
        url: URL to validate

    Returns:
        True if valid Zaffari URL
    """
    parsed = urlparse(url)
    return (
        parsed.netloc in ['www.zaffari.com.br', 'zaffari.com.br'] and
        '/p' in parsed.path
    )


def validate_carrefour_url(url: str) -> bool:
    """
    Validate if URL is a valid Carrefour product URL.

    Args:
        url: URL to validate

    Returns:
        True if valid Carrefour URL
    """
    parsed = urlparse(url)
    return (
        parsed.netloc in ['mercado.carrefour.com.br', 'www.mercado.carrefour.com.br'] and
        '/p' in parsed.path
    )


def validate_product_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if URL is a valid product URL from any supported store.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, store_name) or (False, None)
    """
    if validate_zaffari_url(url):
        return (True, 'zaffari')
    if validate_carrefour_url(url):
        return (True, 'carrefour')
    return (False, None)


def extract_sku_from_url(url: str) -> Optional[str]:
    """
    Extract SKU from product URL (Zaffari or Carrefour).

    Args:
        url: Product URL

    Returns:
        SKU string or None
    """
    # URL format: https://www.zaffari.com.br/product-name-SKU/p
    # or: https://mercado.carrefour.com.br/product-name-SKU/p
    match = re.search(r'-(\d+)/p', url)
    if match:
        return match.group(1)

    match = re.search(r'/(\d+)/p', url)
    if match:
        return match.group(1)

    return None


def get_store_display_name(store: str) -> str:
    """
    Get display name for a store.

    Args:
        store: Store identifier (zaffari, carrefour)

    Returns:
        Display name
    """
    names = {
        'zaffari': 'Zaffari',
        'carrefour': 'Carrefour',
    }
    return names.get(store.lower(), store.title())
