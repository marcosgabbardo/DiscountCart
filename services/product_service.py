"""
Product service for managing monitored products.
"""

from decimal import Decimal
from typing import Optional, List
from datetime import datetime, timedelta

from database import get_db, Product, PriceHistory, ProductSummary
from scraper import AmazonScraper


class ProductService:
    """Service for product CRUD operations and price tracking."""

    def __init__(self):
        self.db = get_db()
        self.scraper = AmazonScraper()

    def add_product(self, url: str, target_price: Decimal) -> Product:
        """
        Add a new product to monitor.

        Args:
            url: Amazon product URL
            target_price: Target price for alerts

        Returns:
            Created Product object
        """
        # Scrape product information
        scraped = self.scraper.scrape_product(url)

        if scraped.error and not scraped.title:
            raise ValueError(f"Failed to scrape product: {scraped.error}")

        # Check if product already exists
        existing = self.get_product_by_asin(scraped.asin)
        if existing:
            # Update target price and reactivate if needed
            self._update_product_target(existing.id, target_price)
            existing.target_price = target_price
            existing.is_active = True
            return existing

        # Insert new product
        query = """
            INSERT INTO products (asin, url, title, image_url, target_price, current_price, lowest_price, highest_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            scraped.asin,
            scraped.url,
            scraped.title,
            scraped.image_url,
            float(target_price),
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

    def _update_product_target(self, product_id: int, target_price: Decimal) -> None:
        """Update product target price and reactivate."""
        query = """
            UPDATE products
            SET target_price = %s, is_active = TRUE
            WHERE id = %s
        """
        self.db.execute_query(query, (float(target_price), product_id), fetch=False)

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        query = "SELECT * FROM products WHERE id = %s"
        results = self.db.execute_query(query, (product_id,))
        if results:
            return Product.from_dict(results[0])
        return None

    def get_product_by_asin(self, asin: str) -> Optional[Product]:
        """Get product by ASIN."""
        query = "SELECT * FROM products WHERE asin = %s"
        results = self.db.execute_query(query, (asin,))
        if results:
            return Product.from_dict(results[0])
        return None

    def get_all_products(self, active_only: bool = True) -> List[Product]:
        """Get all monitored products."""
        query = "SELECT * FROM products"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY updated_at DESC"

        results = self.db.execute_query(query)
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

        scraped = self.scraper.scrape_product(product.url)

        if scraped.error:
            print(f"Warning: {scraped.error}")

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
        """Update prices for all active products."""
        products = self.get_all_products(active_only=True)
        updated = []

        for i, product in enumerate(products):
            print(f"Updating {i + 1}/{len(products)}: {product.title[:50] if product.title else product.asin}...")
            updated_product = self.update_product_price(product.id)
            if updated_product:
                updated.append(updated_product)

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

    def get_products_at_target(self) -> List[Product]:
        """Get products that have reached or are below target price."""
        query = """
            SELECT * FROM products
            WHERE is_active = TRUE
            AND current_price IS NOT NULL
            AND current_price <= target_price
            ORDER BY (target_price - current_price) DESC
        """
        results = self.db.execute_query(query)
        return [Product.from_dict(row) for row in results]

    def get_products_below_average(self, days: int = 7, threshold_percent: float = 10.0) -> List[dict]:
        """Get products that are below their average price by threshold percentage."""
        query = """
            SELECT
                p.*,
                (SELECT AVG(ph.price) FROM price_history ph
                 WHERE ph.product_id = p.id
                 AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL %s DAY)) as avg_price
            FROM products p
            WHERE p.is_active = TRUE
            AND p.current_price IS NOT NULL
            HAVING avg_price IS NOT NULL
            AND p.current_price < avg_price * (1 - %s / 100)
            ORDER BY ((avg_price - p.current_price) / avg_price * 100) DESC
        """
        results = self.db.execute_query(query, (days, threshold_percent))

        products_with_avg = []
        for row in results:
            product = Product.from_dict(row)
            products_with_avg.append({
                'product': product,
                'avg_price': Decimal(str(row['avg_price'])),
                'discount_percent': float((Decimal(str(row['avg_price'])) - product.current_price) / Decimal(str(row['avg_price'])) * 100)
            })

        return products_with_avg
