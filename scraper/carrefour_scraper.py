"""
Carrefour product scraper for price monitoring.
Uses web scraping and VTEX API to extract product information from mercado.carrefour.com.br.
"""

import re
import random
import time
import json
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import settings


@dataclass
class ScrapedProduct:
    """Data scraped from a Carrefour product page."""
    sku: str
    url: str
    title: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    image_url: Optional[str] = None
    is_available: bool = True
    currency: str = 'BRL'
    error: Optional[str] = None


class CarrefourScraper:
    """Scraper for Carrefour supermarket product pages."""

    BASE_URL = 'https://mercado.carrefour.com.br'

    def __init__(self):
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self) -> None:
        """Configure session with appropriate headers."""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/json',
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
        """Extract SKU/product ID from Carrefour URL."""
        # URL format: https://mercado.carrefour.com.br/product-name-SKU/p
        match = re.search(r'-(\d+)/p', url)
        if match:
            return match.group(1)

        match = re.search(r'/(\d+)/p', url)
        if match:
            return match.group(1)

        return None

    def extract_title_from_url(self, url: str) -> Optional[str]:
        """Extract product title from URL slug."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if path.endswith('/p'):
            path = path[:-2]

        slug = re.sub(r'-\d+$', '', path)

        if slug:
            title = slug.replace('-', ' ').title()
            return title

        return None

    def validate_url(self, url: str) -> bool:
        """Check if URL is a valid Carrefour product URL."""
        parsed = urlparse(url)
        return (
            parsed.netloc in ['mercado.carrefour.com.br', 'www.mercado.carrefour.com.br'] and
            '/p' in parsed.path
        )

    def normalize_url(self, url: str) -> str:
        """Normalize Carrefour URL."""
        if not url.startswith('http'):
            url = f"https://{url}"
        return url

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price text to Decimal value."""
        if not price_text:
            return None

        price_text = str(price_text).strip()
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None

        if ',' in price_text and '.' in price_text:
            price_text = price_text.replace('.', '').replace(',', '.')
        elif ',' in price_text:
            price_text = price_text.replace(',', '.')
        elif '.' in price_text:
            parts = price_text.split('.')
            if len(parts) == 2 and len(parts[1]) == 3:
                price_text = price_text.replace('.', '')

        try:
            return Decimal(price_text)
        except Exception:
            return None

    def _fetch_price_from_api(self, sku: str) -> Optional[dict]:
        """Try to fetch product info from VTEX API."""
        self.session.headers['User-Agent'] = self._get_random_user_agent()

        # VTEX API endpoints commonly used
        api_urls = [
            f"{self.BASE_URL}/api/catalog_system/pub/products/search?fq=productId:{sku}",
            f"{self.BASE_URL}/api/catalog_system/pub/products/search?fq=skuId:{sku}",
            f"{self.BASE_URL}/api/catalog_system/pub/products/search/{sku}",
        ]

        for api_url in api_urls:
            try:
                response = self.session.get(
                    api_url,
                    timeout=settings.REQUEST_TIMEOUT,
                    headers={'Accept': 'application/json'}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return data[0]
            except Exception:
                continue

        return None

    def _extract_price_from_json_ld(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """Extract price from JSON-LD structured data."""
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Handle single product
                if isinstance(data, dict):
                    if data.get('@type') == 'Product':
                        offers = data.get('offers', {})
                        if isinstance(offers, dict):
                            price = offers.get('price') or offers.get('lowPrice')
                            if price:
                                return Decimal(str(price))
                        elif isinstance(offers, list) and len(offers) > 0:
                            price = offers[0].get('price')
                            if price:
                                return Decimal(str(price))
                # Handle list of items
                elif isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Product':
                            offers = item.get('offers', {})
                            if isinstance(offers, dict):
                                price = offers.get('price') or offers.get('lowPrice')
                                if price:
                                    return Decimal(str(price))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return None

    def _extract_price_from_state(self, html: str) -> Optional[Decimal]:
        """Extract price from __STATE__ or similar JavaScript state."""
        # Look for price in JavaScript state objects
        patterns = [
            r'"sellingPrice"\s*:\s*(\d+(?:\.\d+)?)',
            r'"Price"\s*:\s*(\d+(?:\.\d+)?)',
            r'"price"\s*:\s*(\d+(?:\.\d+)?)',
            r'"bestPrice"\s*:\s*(\d+(?:\.\d+)?)',
            r'"spotPrice"\s*:\s*(\d+(?:\.\d+)?)',
            r'sellingPrice.*?(\d+(?:,\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                price_str = match.group(1)
                # VTEX stores prices in cents sometimes
                price = self._parse_price(price_str)
                if price:
                    # If price seems too high (in cents), divide by 100
                    if price > 10000:
                        price = price / 100
                    if 0.01 < price < 100000:  # Sanity check
                        return Decimal(str(round(float(price), 2)))

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
            raise Exception("Request timed out. O site pode estar lento.")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                raise Exception("Acesso bloqueado pelo site.")
            raise Exception(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def _parse_product_page(self, html: str, url: str, sku: str) -> ScrapedProduct:
        """Parse product information from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        product = ScrapedProduct(sku=sku, url=url)

        # Extract title
        title_selectors = [
            '.vtex-store-components-3-x-productBrand',
            '.vtex-store-components-3-x-productNameContainer',
            'h1[class*="productName"]',
            '.productName',
            'h1.product-name',
            '.product-title',
            'h1',
        ]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if title_text and len(title_text) > 3:
                    product.title = title_text
                    break

        # Try multiple methods to get price
        # Method 1: CSS selectors (most reliable for current price)
        price_selectors = [
            # Carrefour specific - blue royal price (main price displayed)
            'span.text-blue-royal.font-bold.text-xl',
            'span[class*="text-blue-royal"][class*="font-bold"]',
            'span[class*="blue-royal"]',
            # Other Carrefour selectors
            '[class*="sellingPrice"] [class*="currencyInteger"]',
            '[class*="sellingPriceValue"]',
            '[class*="ProductPrice"] [class*="Value"]',
            '.vtex-product-price-1-x-sellingPriceValue',
            '.skuBestPrice',
            '.price-best-price',
            '[data-testid="price"]',
        ]

        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                parsed_price = self._parse_price(price_text)
                if parsed_price and parsed_price > 0:
                    product.price = parsed_price
                    break

        # Method 2: JSON-LD structured data (fallback)
        if not product.price:
            product.price = self._extract_price_from_json_ld(soup)

        # Method 3: JavaScript state (last resort)
        if not product.price:
            product.price = self._extract_price_from_state(html)

        # Extract image
        image_selectors = [
            '.vtex-store-components-3-x-productImage img',
            '[class*="productImage"] img',
            'img[class*="product"]',
        ]

        for selector in image_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                product.image_url = img_elem.get('src') or img_elem.get('data-src')
                if product.image_url:
                    break

        # Check availability
        page_text = soup.get_text().lower()
        if 'indisponível' in page_text or 'esgotado' in page_text:
            if not product.price:
                product.is_available = False

        return product

    def scrape_product(self, url: str) -> ScrapedProduct:
        """Scrape product information from a Carrefour URL."""
        if not self.validate_url(url):
            return ScrapedProduct(
                sku='',
                url=url,
                is_available=False,
                error="URL inválida. Use uma URL de produto do Carrefour (ex: mercado.carrefour.com.br/produto-123/p)"
            )

        sku = self.extract_sku(url)
        if not sku:
            sku = 'unknown'

        normalized_url = self.normalize_url(url)
        url_title = self.extract_title_from_url(normalized_url)

        try:
            self._random_delay()

            # Try HTML scraping first (CSS selectors have most accurate current price)
            html = self._fetch_page(normalized_url)

            if html:
                product = self._parse_product_page(html, normalized_url, sku)

                if not product.title and url_title:
                    product.title = url_title

                if product.title and product.price:
                    product.error = None
                    return product

            # Fallback to API if HTML scraping didn't get price
            api_data = self._fetch_price_from_api(sku)
            if api_data:
                title = api_data.get('productName') or api_data.get('name')
                items = api_data.get('items', [])
                price = None
                if items:
                    sellers = items[0].get('sellers', [])
                    if sellers:
                        offer = sellers[0].get('commertialOffer', {})
                        price = offer.get('Price') or offer.get('spotPrice')

                if price:
                    return ScrapedProduct(
                        sku=sku,
                        url=normalized_url,
                        title=title or url_title,
                        price=Decimal(str(price)),
                        is_available=True
                    )

            # If we got title from HTML but no price
            if html:
                product = self._parse_product_page(html, normalized_url, sku)
                if not product.title and url_title:
                    product.title = url_title
                if product.title and not product.price:
                    product.error = "Não foi possível extrair o preço. Site pode estar bloqueando."
                    return product

            # Last resort: URL title only
            if url_title:
                return ScrapedProduct(
                    sku=sku,
                    url=normalized_url,
                    title=url_title,
                    is_available=True,
                    error="Não foi possível extrair o preço. Tente novamente mais tarde."
                )

            return ScrapedProduct(
                sku=sku,
                url=normalized_url,
                is_available=False,
                error="Falha ao buscar informações do produto."
            )

        except Exception as e:
            if url_title:
                return ScrapedProduct(
                    sku=sku,
                    url=normalized_url,
                    title=url_title,
                    is_available=True,
                    error=f"Erro: {str(e)}"
                )
            return ScrapedProduct(
                sku=sku,
                url=normalized_url,
                is_available=False,
                error=str(e)
            )

    def scrape_multiple(self, urls: list) -> list:
        """Scrape multiple products with delays between requests."""
        results = []
        for i, url in enumerate(urls):
            print(f"Buscando produto {i + 1}/{len(urls)}...")
            result = self.scrape_product(url)
            results.append(result)

            if i < len(urls) - 1:
                self._random_delay()

        return results
