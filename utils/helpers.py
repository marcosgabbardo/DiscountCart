"""
Helper utilities for Amazon Price Monitor.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional


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
    cleaned = re.sub(r'[R$\s]', '', price_str.strip())

    # Handle empty string after cleaning
    if not cleaned:
        return None

    # Determine format and normalize
    # Brazilian format: 1.234,56 (dot as thousand separator, comma as decimal)
    # US format: 1,234.56 (comma as thousand separator, dot as decimal)

    has_comma = ',' in cleaned
    has_dot = '.' in cleaned

    if has_comma and has_dot:
        # Both present - determine which is decimal separator
        comma_pos = cleaned.rfind(',')
        dot_pos = cleaned.rfind('.')

        if comma_pos > dot_pos:
            # Brazilian format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US format: 1,234.56
            cleaned = cleaned.replace(',', '')

    elif has_comma:
        # Only comma - assume decimal separator (Brazilian common format: 80,99)
        cleaned = cleaned.replace(',', '.')

    # has_dot only or no separator - already in correct format

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

    # Format with 2 decimal places and Brazilian format
    formatted = f"{float(value):,.2f}"
    # Convert to Brazilian format (swap . and ,)
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')

    return f"{currency} {formatted}"


def truncate_string(text: Optional[str], max_length: int = 50, suffix: str = '...') -> str:
    """
    Truncate a string to max length with suffix.

    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append if truncated

    Returns:
        Truncated string
    """
    if not text:
        return ''

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """
    Format a float as percentage string.

    Args:
        value: Float value (e.g., 15.5 for 15.5%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    if value is None:
        return '--%'

    return f"{value:.{decimals}f}%"


def validate_amazon_url(url: str) -> bool:
    """
    Validate if URL is a valid Amazon product URL.

    Args:
        url: URL to validate

    Returns:
        True if valid Amazon URL
    """
    amazon_patterns = [
        r'amazon\.com\.br',
        r'amazon\.com',
        r'amazon\.co\.',
        r'amzn\.to',
    ]

    url_lower = url.lower()
    return any(re.search(pattern, url_lower) for pattern in amazon_patterns)


def extract_asin_from_url(url: str) -> Optional[str]:
    """
    Extract ASIN from Amazon URL.

    Args:
        url: Amazon product URL

    Returns:
        ASIN string or None
    """
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'asin=([A-Z0-9]{10})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None
