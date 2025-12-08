"""
Zaffari product scraper for price monitoring.
Uses web scraping to extract product information.
"""

import re
import random
import time
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import settings


@dataclass
class ScrapedProduct:
    """Data scraped from a Zaffari product page."""
    sku: str
    url: str
    title: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    is_available: bool = True
    currency: str = 'BRL'
    error: Optional[str] = None


class ZaffariScraper:
    """Scraper for Zaffari supermarket product pages."""

    BASE_URL = 'https://www.zaffari.com.br'

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

    def extract_sku(self, url: str) -> Optional[str]:
        """Extract SKU/product ID from Zaffari URL."""
        # URL format: https://www.zaffari.com.br/product-name-SKU/p
        # Example: https://www.zaffari.com.br/queijo-mussarela-fatiado-president-150g-1008729/p
        match = re.search(r'-(\d+)/p', url)
        if match:
            return match.group(1)

        # Try alternative patterns
        match = re.search(r'/(\d+)/p', url)
        if match:
            return match.group(1)

        return None

    def validate_url(self, url: str) -> bool:
        """Check if URL is a valid Zaffari product URL."""
        parsed = urlparse(url)
        return (
            parsed.netloc in ['www.zaffari.com.br', 'zaffari.com.br'] and
            '/p' in parsed.path
        )

    def normalize_url(self, url: str) -> str:
        """Normalize Zaffari URL."""
        if not url.startswith('http'):
            url = f"https://{url}"
        return url

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price text to Decimal value."""
        if not price_text:
            return None

        price_text = price_text.strip()

        # Remove ALL non-numeric characters except dots and commas
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None

        # Handle Brazilian format: R$ 1.234,56
        if ',' in price_text and '.' in price_text:
            # Has both: Brazilian format (. = thousand, , = decimal)
            price_text = price_text.replace('.', '').replace(',', '.')
        elif ',' in price_text:
            # Only comma: decimal separator (e.g., 39,60 -> 39.60)
            price_text = price_text.replace(',', '.')
        elif '.' in price_text:
            # Only dot - check if it's decimal or thousand separator
            parts = price_text.split('.')
            if len(parts) == 2:
                after_dot = parts[1]
                if len(after_dot) == 3:
                    # Likely thousand separator
                    price_text = price_text.replace('.', '')

        try:
            return Decimal(price_text)
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
            raise Exception("Request timed out. O site pode estar lento ou bloqueando requests.")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                raise Exception("Acesso bloqueado pelo site. Tente novamente mais tarde.")
            raise Exception(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def _parse_product_page(self, html: str, url: str, sku: str) -> ScrapedProduct:
        """Parse product information from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        product = ScrapedProduct(sku=sku, url=url)

        # Extract title - VTEX common selectors
        title_selectors = [
            '.vtex-store-components-3-x-productBrand',
            '.vtex-store-components-3-x-productNameContainer',
            '.productName',
            'h1.product-name',
            '.product-title',
            'h1[class*="productName"]',
            '.vtex-product-summary-2-x-productBrand',
            'h1',
        ]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and len(title_text) > 3:
                    product.title = title_text
                    break

        # Extract price - Zaffari specific selector first, then VTEX common selectors
        price_selectors = [
            '.zaffarilab-zaffari-produto-1-x-ProductPriceSellingPriceValue',
            '.vtex-product-price-1-x-sellingPrice',
            '.vtex-product-price-1-x-currencyContainer',
            '.vtex-store-components-3-x-sellingPrice',
            '.skuBestPrice',
            '.price-best-price',
            '.product-price .best-price',
            '[class*="sellingPrice"]',
            '[class*="bestPrice"]',
            '.price',
        ]

        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                parsed_price = self._parse_price(price_text)
                if parsed_price and parsed_price > 0:
                    product.price = parsed_price
                    break

        # Try to get price from JSON-LD structured data
        if not product.price:
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Look for price in offers
                        if 'offers' in data:
                            offers = data['offers']
                            if isinstance(offers, dict) and 'price' in offers:
                                product.price = Decimal(str(offers['price']))
                            elif isinstance(offers, list) and len(offers) > 0:
                                product.price = Decimal(str(offers[0].get('price', 0)))
                except:
                    pass

        # Extract original price (if on sale)
        original_selectors = [
            '.vtex-product-price-1-x-listPrice',
            '.vtex-store-components-3-x-listPrice',
            '.skuListPrice',
            '.list-price',
            '.old-price',
            '[class*="listPrice"]',
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
            '.vtex-store-components-3-x-productImage img',
            '.product-image img',
            '[class*="productImage"] img',
            '.main-image img',
            'img[class*="product"]',
        ]

        for selector in image_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                product.image_url = img_elem.get('src') or img_elem.get('data-src')
                if product.image_url:
                    break

        # Check availability
        unavailable_indicators = [
            '.vtex-store-components-3-x-unavailableContainer',
            '.product-unavailable',
            '[class*="unavailable"]',
        ]

        for selector in unavailable_indicators:
            if soup.select_one(selector):
                product.is_available = False
                break

        # Also check for "indisponível" text
        page_text = soup.get_text().lower()
        if 'indisponível' in page_text or 'esgotado' in page_text:
            if not product.price:
                product.is_available = False

        return product

    def scrape_product(self, url: str) -> ScrapedProduct:
        """
        Scrape product information from a Zaffari URL.

        Args:
            url: Zaffari product URL

        Returns:
            ScrapedProduct with extracted information
        """
        if not self.validate_url(url):
            return ScrapedProduct(
                sku='',
                url=url,
                is_available=False,
                error="URL inválida. Use uma URL de produto do Zaffari (ex: zaffari.com.br/produto-123/p)"
            )

        sku = self.extract_sku(url)
        if not sku:
            sku = 'unknown'

        normalized_url = self.normalize_url(url)

        try:
            self._random_delay()
            html = self._fetch_page(normalized_url)

            if not html:
                return ScrapedProduct(
                    sku=sku,
                    url=normalized_url,
                    is_available=False,
                    error="Falha ao buscar conteúdo da página"
                )

            product = self._parse_product_page(html, normalized_url, sku)

            if not product.title:
                product.error = "Não foi possível extrair informações do produto. A estrutura da página pode ter mudado."

            return product

        except Exception as e:
            return ScrapedProduct(
                sku=sku,
                url=normalized_url,
                is_available=False,
                error=str(e)
            )

    def scrape_multiple(self, urls: list) -> list:
        """
        Scrape multiple products with delays between requests.

        Args:
            urls: List of Zaffari product URLs

        Returns:
            List of ScrapedProduct objects
        """
        results = []
        for i, url in enumerate(urls):
            print(f"Buscando produto {i + 1}/{len(urls)}...")
            result = self.scrape_product(url)
            results.append(result)

            if i < len(urls) - 1:
                self._random_delay()

        return results
