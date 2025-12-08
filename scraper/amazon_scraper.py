"""
Amazon product scraper for price monitoring.
Uses web scraping to extract product information.
"""

import re
import random
import time
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from config import settings


@dataclass
class ScrapedProduct:
    """Data scraped from an Amazon product page."""
    asin: str
    url: str
    title: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    is_available: bool = True
    currency: str = 'BRL'
    rating: Optional[float] = None
    review_count: Optional[int] = None
    error: Optional[str] = None


class AmazonScraper:
    """Scraper for Amazon Brazil product pages."""

    # Amazon Brazil base URL
    BASE_URL = 'https://www.amazon.com.br'

    # Regex patterns for ASIN extraction
    ASIN_PATTERNS = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'asin=([A-Z0-9]{10})',
    ]

    def __init__(self):
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self) -> None:
        """Configure session with appropriate headers."""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })

    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the configured list."""
        return random.choice(settings.USER_AGENTS)

    def _random_delay(self) -> None:
        """Add random delay between requests to avoid detection."""
        delay = random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)
        time.sleep(delay)

    def extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN (Amazon Standard Identification Number) from URL."""
        for pattern in self.ASIN_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def normalize_url(self, url: str) -> str:
        """Normalize Amazon URL to a clean format."""
        asin = self.extract_asin(url)
        if asin:
            return f"{self.BASE_URL}/dp/{asin}"
        return url

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price text to Decimal value."""
        if not price_text:
            return None

        original_text = price_text  # Keep original for debugging
        price_text = price_text.strip()

        # Remove ALL non-numeric characters except dots and commas
        # This handles R$, spaces, non-breaking spaces, and any other chars
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None

        # Handle Brazilian format: R$ 1.234,56
        # Brazilian: 1.234,56 -> 1234.56
        if ',' in price_text and '.' in price_text:
            # Has both: Brazilian format (. = thousand, , = decimal)
            price_text = price_text.replace('.', '').replace(',', '.')
        elif ',' in price_text:
            # Only comma: decimal separator (e.g., 39,60 -> 39.60)
            price_text = price_text.replace(',', '.')
            # After converting comma to dot, check if we need to handle "39.600" case
            if '.' in price_text:
                parts = price_text.split('.')
                if len(parts) == 2:
                    before_dot = parts[0]
                    after_dot = parts[1]
                    # If 3 digits after dot AND small number before, it's mangled
                    if len(after_dot) == 3 and len(before_dot) <= 3:
                        price_text = f"{before_dot}.{after_dot[:2]}"
        elif '.' in price_text:
            # Only dot - determine if decimal or thousand separator
            parts = price_text.split('.')
            if len(parts) == 2:
                before_dot = parts[0]
                after_dot = parts[1]
                if len(after_dot) == 2:
                    pass  # Already correct decimal format
                elif len(after_dot) == 3 and len(before_dot) <= 3:
                    # "39.600" should be "39.60" (mangled Brazilian price)
                    price_text = f"{before_dot}.{after_dot[:2]}"
                elif len(after_dot) == 3:
                    # Large number with thousand separator (e.g., "1.234" -> 1234)
                    price_text = price_text.replace('.', '')

        try:
            result = Decimal(price_text)
            # Sanity check: if result > 10000 and looks like it could be cents
            # Check if dividing by 100 gives a reasonable price (10-500)
            if result > 10000:
                cents_price = result / 100
                if 10 <= cents_price <= 500:
                    return cents_price
            return result
        except Exception:
            return None

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content with error handling."""
        self.session.headers['User-Agent'] = self._get_random_user_agent()

        try:
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text

        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Amazon may be slow or blocking requests.")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 503:
                raise Exception("Amazon is blocking automated requests. Try again later.")
            raise Exception(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def _parse_product_page(self, html: str, url: str, asin: str) -> ScrapedProduct:
        """Parse product information from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        product = ScrapedProduct(asin=asin, url=url)

        # Extract title
        title_elem = soup.select_one('#productTitle')
        if title_elem:
            product.title = title_elem.get_text(strip=True)

        # Extract price - Get one-time purchase price (not subscription)
        # Filter out: price per liter/unit (< R$10) and pick highest of two lowest real prices

        all_prices = []

        # IMPORTANT: Only look in the buy box area
        buy_box = soup.select_one('#desktop_buybox')
        if not buy_box:
            buy_box = soup.select_one('#buybox')
        if not buy_box:
            buy_box = soup.select_one('#centerCol')
        if not buy_box:
            buy_box = soup

        # Specific selectors for the main price display
        price_selectors = [
            '#corePrice_feature_div .a-price .a-offscreen',
            '#corePriceDisplay_desktop_feature_div .a-price .a-offscreen',
            '.priceToPay .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
        ]

        for selector in price_selectors:
            for price_elem in buy_box.select(selector):
                price_text = price_elem.get_text(strip=True)
                parsed_price = self._parse_price(price_text)
                # Filter: R$10 <= price <= R$50000 (ignore per-unit prices and parsing errors)
                if parsed_price and 10 <= parsed_price <= 50000:
                    all_prices.append(parsed_price)

        # Get the highest of the two lowest prices (one-time purchase > subscription)
        if all_prices:
            unique_prices = sorted(set(all_prices))
            # Take up to 2 lowest and pick max (one-time purchase)
            product.price = max(unique_prices[:2])

        # Extract original price (if on sale)
        original_selectors = [
            '.a-text-price .a-offscreen',
            '#listPrice',
            '.priceBlockStrikePriceString',
        ]

        for selector in original_selectors:
            original_elem = soup.select_one(selector)
            if original_elem:
                original_text = original_elem.get_text(strip=True)
                product.original_price = self._parse_price(original_text)
                if product.original_price:
                    break

        # Extract image URL
        image_selectors = [
            '#landingImage',
            '#imgBlkFront',
            '#main-image',
            '.a-dynamic-image',
        ]

        for selector in image_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                product.image_url = img_elem.get('src') or img_elem.get('data-old-hires')
                if product.image_url:
                    break

        # Check availability
        unavailable_indicators = [
            '#availability .a-color-price',
            '#outOfStock',
            '.a-color-price:contains("Indisponível")',
        ]

        availability_elem = soup.select_one('#availability')
        if availability_elem:
            availability_text = availability_elem.get_text(strip=True).lower()
            if 'indisponível' in availability_text or 'unavailable' in availability_text:
                product.is_available = False

        # Extract rating
        rating_elem = soup.select_one('.a-icon-star .a-icon-alt, #acrPopover')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True) if rating_elem.name != 'span' else rating_elem.get('title', '')
            rating_match = re.search(r'(\d+[,.]?\d*)', rating_text)
            if rating_match:
                try:
                    product.rating = float(rating_match.group(1).replace(',', '.'))
                except ValueError:
                    pass

        # Extract review count
        review_elem = soup.select_one('#acrCustomerReviewText')
        if review_elem:
            review_text = review_elem.get_text(strip=True)
            review_match = re.search(r'([\d.]+)', review_text.replace('.', ''))
            if review_match:
                try:
                    product.review_count = int(review_match.group(1))
                except ValueError:
                    pass

        return product

    def scrape_product(self, url: str) -> ScrapedProduct:
        """
        Scrape product information from an Amazon URL.

        Args:
            url: Amazon product URL

        Returns:
            ScrapedProduct with extracted information
        """
        asin = self.extract_asin(url)
        if not asin:
            return ScrapedProduct(
                asin='',
                url=url,
                is_available=False,
                error="Could not extract ASIN from URL. Please provide a valid Amazon product URL."
            )

        normalized_url = self.normalize_url(url)

        try:
            self._random_delay()
            html = self._fetch_page(normalized_url)

            if not html:
                return ScrapedProduct(
                    asin=asin,
                    url=normalized_url,
                    is_available=False,
                    error="Failed to fetch page content"
                )

            product = self._parse_product_page(html, normalized_url, asin)

            # Validate that we got at least the title
            if not product.title:
                product.error = "Could not parse product information. Page structure may have changed."

            return product

        except Exception as e:
            return ScrapedProduct(
                asin=asin,
                url=normalized_url,
                is_available=False,
                error=str(e)
            )

    def scrape_multiple(self, urls: list) -> list:
        """
        Scrape multiple products with delays between requests.

        Args:
            urls: List of Amazon product URLs

        Returns:
            List of ScrapedProduct objects
        """
        results = []
        for i, url in enumerate(urls):
            print(f"Scraping product {i + 1}/{len(urls)}...")
            result = self.scrape_product(url)
            results.append(result)

            # Add extra delay between products
            if i < len(urls) - 1:
                self._random_delay()

        return results
