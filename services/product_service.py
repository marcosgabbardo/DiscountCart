"""
Product service for managing monitored products.
"""

import math
from decimal import Decimal
from typing import Optional, List, Tuple

from database import get_db, Product, PriceHistory, ProductSummary, Store
from scraper import ZaffariScraper, CarrefourScraper


class ProductService:
    """Service for product CRUD operations and price tracking."""

    def __init__(self):
        self.db = get_db()
        self.zaffari_scraper = ZaffariScraper()
        self.carrefour_scraper = CarrefourScraper()

    def _get_scraper(self, store: Store):
        """Get the appropriate scraper for the store."""
        if store == Store.CARREFOUR:
            return self.carrefour_scraper
        return self.zaffari_scraper

    def _detect_store(self, url: str) -> Store:
        """Detect which store the URL belongs to."""
        return Store.from_url(url)

    def add_product(self, url: str) -> Product:
        """
        Add a new product to monitor.

        Args:
            url: Product URL (Zaffari or Carrefour)

        Returns:
            Created Product object
        """
        # Detect store from URL
        store = self._detect_store(url)
        scraper = self._get_scraper(store)

        # Scrape product information
        scraped = scraper.scrape_product(url)

        # If scraping failed with error, raise it
        if scraped.error:
            raise ValueError(f"Falha ao buscar produto: {scraped.error}")

        # Must have title and price for a valid scrape
        if not scraped.title:
            raise ValueError("Não foi possível extrair o título do produto.")

        if not scraped.price:
            raise ValueError("Não foi possível extrair o preço do produto. O site pode estar bloqueando.")

        # Check if product already exists (use SKU + store as identifier)
        existing = self.get_product_by_sku(scraped.sku, store)
        if existing:
            # Reactivate and update current price
            self._reactivate_product(existing.id)
            if scraped.price:
                self._update_current_price(existing.id, scraped.price)
            return self.get_product_by_id(existing.id)

        # Try to categorize the product using Anthropic API
        category = None
        if scraped.title:
            try:
                from .category_service import CategoryService
                category_service = CategoryService()
                category = category_service.categorize_product(scraped.title)
            except Exception as e:
                print(f"Aviso: Não foi possível categorizar o produto: {e}")

        # Insert new product
        query = """
            INSERT INTO products (asin, url, title, image_url, store, category, current_price, lowest_price, highest_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            scraped.sku,  # Using SKU in asin column
            scraped.url,
            scraped.title,
            scraped.image_url,
            store.value,
            category,
            float(scraped.price) if scraped.price else None,
            float(scraped.price) if scraped.price else None,
            float(scraped.price) if scraped.price else None,
        )

        with self.db.get_cursor() as cursor:
            cursor.execute(query, params)
            product_id = cursor.lastrowid

        # Record initial price in history
        if scraped.price:
            self._record_price_history(product_id, scraped.price, scraped.is_available)

        # Fetch and return the created product
        return self.get_product_by_id(product_id)

    def _reactivate_product(self, product_id: int) -> None:
        """Reactivate a product."""
        query = """
            UPDATE products
            SET is_active = TRUE
            WHERE id = %s
        """
        self.db.execute_query(query, (product_id,), fetch=False)

    def _update_current_price(self, product_id: int, price: Decimal) -> None:
        """Update current price and adjust lowest/highest if needed."""
        # Get current product to compare prices
        product = self.get_product_by_id(product_id)
        if not product:
            return

        new_lowest = min(product.lowest_price or price, price)
        new_highest = max(product.highest_price or price, price)

        query = """
            UPDATE products
            SET current_price = %s, lowest_price = %s, highest_price = %s
            WHERE id = %s
        """
        self.db.execute_query(query, (float(price), float(new_lowest), float(new_highest), product_id), fetch=False)

        # Record in price history
        self._record_price_history(product_id, price, True)

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        query = "SELECT * FROM products WHERE id = %s"
        results = self.db.execute_query(query, (product_id,))
        if results:
            return Product.from_dict(results[0])
        return None

    def get_product_by_sku(self, sku: str, store: Optional[Store] = None) -> Optional[Product]:
        """Get product by SKU and optionally by store."""
        if store:
            query = "SELECT * FROM products WHERE asin = %s AND store = %s"
            results = self.db.execute_query(query, (sku, store.value))
        else:
            query = "SELECT * FROM products WHERE asin = %s"
            results = self.db.execute_query(query, (sku,))
        if results:
            return Product.from_dict(results[0])
        return None

    def get_all_products(self, active_only: bool = True, store: Optional[Store] = None) -> List[Product]:
        """Get all monitored products, optionally filtered by store."""
        conditions = []
        params = []

        if active_only:
            conditions.append("is_active = TRUE")
        if store:
            conditions.append("store = %s")
            params.append(store.value)

        query = "SELECT * FROM products"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY store, updated_at DESC"

        results = self.db.execute_query(query, tuple(params) if params else None)
        return [Product.from_dict(row) for row in results]

    def get_product_summary(self) -> List[ProductSummary]:
        """Get summary view of all active products."""
        query = "SELECT * FROM product_summary"
        results = self.db.execute_query(query)
        return [ProductSummary.from_dict(row) for row in results]

    def update_product_price(self, product_id: int) -> Optional[Product]:
        """
        Update product price by scraping current price.

        Returns:
            Updated Product object
        """
        product = self.get_product_by_id(product_id)
        if not product:
            return None

        scraper = self._get_scraper(product.store)
        scraped = scraper.scrape_product(product.url)

        # If scraping failed with error, raise it
        if scraped.error:
            raise ValueError(f"Falha ao atualizar produto: {scraped.error}")

        if not scraped.price:
            raise ValueError("Não foi possível extrair o preço do produto. O site pode estar bloqueando.")

        if scraped.price:
            # Update product prices
            new_lowest = min(product.lowest_price or scraped.price, scraped.price)
            new_highest = max(product.highest_price or scraped.price, scraped.price)

            query = """
                UPDATE products
                SET current_price = %s, lowest_price = %s, highest_price = %s
                WHERE id = %s
            """
            self.db.execute_query(
                query,
                (float(scraped.price), float(new_lowest), float(new_highest), product_id),
                fetch=False
            )

            # Record in history
            self._record_price_history(product_id, scraped.price, scraped.is_available)

        return self.get_product_by_id(product_id)

    def update_all_prices(self) -> List[Product]:
        """Update prices for all active products with retry on block."""
        import time

        products = self.get_all_products(active_only=True)
        updated = []
        failed = []
        retry_delay = 30  # seconds to wait when blocked

        for i, product in enumerate(products):
            print(f"Atualizando {i + 1}/{len(products)}: {product.title[:50] if product.title else product.asin}...")

            # Try up to 2 times
            for attempt in range(2):
                try:
                    updated_product = self.update_product_price(product.id)
                    if updated_product:
                        updated.append(updated_product)
                    break
                except ValueError as e:
                    if 'bloqueando' in str(e).lower() or 'blocked' in str(e).lower():
                        if attempt == 0:
                            print(f"  ⚠️  Bloqueado. Aguardando {retry_delay}s antes de tentar novamente...")
                            time.sleep(retry_delay)
                        else:
                            print(f"  ❌ Falhou após retry: {e}")
                            failed.append((product, str(e)))
                    else:
                        print(f"  ❌ Erro: {e}")
                        failed.append((product, str(e)))
                        break

        if failed:
            print(f"\n⚠️  {len(failed)} produto(s) não puderam ser atualizados.")

        return updated

    def _record_price_history(self, product_id: int, price: Decimal, was_available: bool = True) -> None:
        """Record price in history table."""
        query = """
            INSERT INTO price_history (product_id, price, was_available)
            VALUES (%s, %s, %s)
        """
        self.db.execute_query(query, (product_id, float(price), was_available), fetch=False)

    def get_price_history(self, product_id: int, days: int = 30) -> List[PriceHistory]:
        """Get price history for a product."""
        query = """
            SELECT * FROM price_history
            WHERE product_id = %s AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY recorded_at DESC
        """
        results = self.db.execute_query(query, (product_id, days))
        return [PriceHistory.from_dict(row) for row in results]

    def get_average_price(self, product_id: int, days: int = 7) -> Optional[Decimal]:
        """Calculate average price for the last N days."""
        query = """
            SELECT AVG(price) as avg_price
            FROM price_history
            WHERE product_id = %s AND recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        results = self.db.execute_query(query, (product_id, days))
        if results and results[0]['avg_price']:
            return Decimal(str(results[0]['avg_price']))
        return None

    def get_std_deviation(self, product_id: int, days: int = 30) -> Optional[Tuple[Decimal, Decimal]]:
        """
        Calculate average and standard deviation for the last N days.
        Returns: (avg_price, std_deviation) or None
        """
        history = self.get_price_history(product_id, days)
        if len(history) < 2:
            return None

        prices = [float(h.price) for h in history]
        avg = sum(prices) / len(prices)
        variance = sum((p - avg) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)

        return (Decimal(str(round(avg, 2))), Decimal(str(round(std_dev, 2))))

    def get_products_below_std_deviation(self, days: int = 30, num_std_dev: int = 1) -> List[dict]:
        """
        Get products where current price is below (avg - N std deviations).

        Args:
            days: Number of days for price history (30, 90, or 180)
            num_std_dev: Number of standard deviations below average (1 or 2)
        """
        products = self.get_all_products(active_only=True)
        results = []

        for product in products:
            if not product.current_price:
                continue

            stats = self.get_std_deviation(product.id, days)
            if not stats:
                continue

            avg_price, std_dev = stats
            threshold = avg_price - (std_dev * num_std_dev)

            if product.current_price <= threshold:
                results.append({
                    'product': product,
                    'avg_price': avg_price,
                    'std_deviation': std_dev,
                    'threshold': threshold,
                    'num_std_dev': num_std_dev,
                    'days': days,
                    'diff': float(threshold - product.current_price)
                })

        return results

    def get_all_std_deviation_alerts(self) -> dict:
        """
        Get all products that are below standard deviation thresholds.
        Checks for 1 and 2 std deviations for 30, 90, and 180 day periods.

        Returns:
            Dictionary with keys for each alert type containing list of products
        """
        periods = [30, 90, 180]
        std_levels = [1, 2]

        results = {}

        for days in periods:
            for num_std in std_levels:
                key = f"std_dev_{num_std}_{days}d"
                results[key] = self.get_products_below_std_deviation(days, num_std)

        return results

    def get_product_std_analysis(self, product_id: int) -> Optional[dict]:
        """
        Get complete standard deviation analysis for a product.

        Returns analysis for 30, 90, and 180 day periods.
        """
        product = self.get_product_by_id(product_id)
        if not product or not product.current_price:
            return None

        analysis = {
            'product': product,
            'periods': {}
        }

        for days in [30, 90, 180]:
            stats = self.get_std_deviation(product.id, days)
            if stats:
                avg_price, std_dev = stats
                threshold_1 = avg_price - std_dev
                threshold_2 = avg_price - (std_dev * 2)

                analysis['periods'][days] = {
                    'avg_price': avg_price,
                    'std_deviation': std_dev,
                    'threshold_1_std': threshold_1,
                    'threshold_2_std': threshold_2,
                    'is_below_1_std': product.current_price <= threshold_1,
                    'is_below_2_std': product.current_price <= threshold_2,
                }
            else:
                analysis['periods'][days] = None

        return analysis

    def deactivate_product(self, product_id: int) -> bool:
        """Deactivate a product (stop monitoring)."""
        query = "UPDATE products SET is_active = FALSE WHERE id = %s"
        self.db.execute_query(query, (product_id,), fetch=False)
        return True

    def activate_product(self, product_id: int) -> bool:
        """Activate a product (resume monitoring)."""
        query = "UPDATE products SET is_active = TRUE WHERE id = %s"
        self.db.execute_query(query, (product_id,), fetch=False)
        return True

    def delete_product(self, product_id: int) -> bool:
        """Delete a product and all its history."""
        query = "DELETE FROM products WHERE id = %s"
        self.db.execute_query(query, (product_id,), fetch=False)
        return True

