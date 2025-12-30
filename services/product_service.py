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

        Requires at least 30 data points for statistical significance.
        """
        history = self.get_price_history(product_id, days)
        if len(history) < 30:
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

    # ==================== ANALYSIS METHODS ====================

    def get_products_at_minimum(self, store: Optional[Store] = None) -> List[Product]:
        """Get products where current price equals the historical minimum."""
        products = self.get_all_products(active_only=True, store=store)
        return [p for p in products if p.current_price and p.lowest_price and p.current_price <= p.lowest_price]

    def get_products_at_maximum(self, store: Optional[Store] = None) -> List[Product]:
        """Get products where current price equals the historical maximum."""
        products = self.get_all_products(active_only=True, store=store)
        return [p for p in products if p.current_price and p.highest_price and p.current_price >= p.highest_price]

    def get_products_below_average(self, days: int = 30, store: Optional[Store] = None) -> List[dict]:
        """Get products where current price is below the average for the period."""
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            if not product.current_price:
                continue

            avg_price = self.get_average_price(product.id, days)
            if avg_price and product.current_price < avg_price:
                diff_percent = float((avg_price - product.current_price) / avg_price * 100)
                results.append({
                    'product': product,
                    'avg_price': avg_price,
                    'diff_percent': diff_percent,
                    'days': days
                })

        # Sort by biggest discount
        results.sort(key=lambda x: x['diff_percent'], reverse=True)
        return results

    def get_products_above_average(self, days: int = 30, store: Optional[Store] = None) -> List[dict]:
        """Get products where current price is above the average for the period."""
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            if not product.current_price:
                continue

            avg_price = self.get_average_price(product.id, days)
            if avg_price and product.current_price > avg_price:
                diff_percent = float((product.current_price - avg_price) / avg_price * 100)
                results.append({
                    'product': product,
                    'avg_price': avg_price,
                    'diff_percent': diff_percent,
                    'days': days
                })

        # Sort by biggest increase
        results.sort(key=lambda x: x['diff_percent'], reverse=True)
        return results

    def get_products_with_price_drop(self, store: Optional[Store] = None) -> List[dict]:
        """Get products where the last price is lower than the previous one."""
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            history = self.get_price_history(product.id, days=7)
            if len(history) < 2:
                continue

            # History is sorted DESC, so [0] is most recent, [1] is previous
            current = history[0].price
            previous = history[1].price

            if current < previous:
                drop_percent = float((previous - current) / previous * 100)
                results.append({
                    'product': product,
                    'previous_price': previous,
                    'current_price': current,
                    'drop_percent': drop_percent,
                    'recorded_at': history[0].recorded_at
                })

        # Sort by biggest drop
        results.sort(key=lambda x: x['drop_percent'], reverse=True)
        return results

    def get_products_with_price_rise(self, store: Optional[Store] = None) -> List[dict]:
        """Get products where the last price is higher than the previous one."""
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            history = self.get_price_history(product.id, days=7)
            if len(history) < 2:
                continue

            # History is sorted DESC, so [0] is most recent, [1] is previous
            current = history[0].price
            previous = history[1].price

            if current > previous:
                rise_percent = float((current - previous) / previous * 100)
                results.append({
                    'product': product,
                    'previous_price': previous,
                    'current_price': current,
                    'rise_percent': rise_percent,
                    'recorded_at': history[0].recorded_at
                })

        # Sort by biggest rise
        results.sort(key=lambda x: x['rise_percent'], reverse=True)
        return results

    def get_volatile_products(self, days: int = 30, threshold: float = 10.0, store: Optional[Store] = None) -> List[dict]:
        """
        Get products with high price volatility (coefficient of variation > threshold%).

        Coefficient of variation = (std_dev / avg) * 100
        """
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            stats = self.get_std_deviation(product.id, days)
            if not stats:
                continue

            avg_price, std_dev = stats
            if avg_price > 0:
                cv = float(std_dev / avg_price * 100)
                if cv >= threshold:
                    results.append({
                        'product': product,
                        'avg_price': avg_price,
                        'std_deviation': std_dev,
                        'coefficient_variation': cv,
                        'days': days
                    })

        # Sort by highest volatility
        results.sort(key=lambda x: x['coefficient_variation'], reverse=True)
        return results

    def get_stable_products(self, days: int = 30, threshold: float = 5.0, store: Optional[Store] = None) -> List[dict]:
        """
        Get products with stable prices (coefficient of variation < threshold%).

        Coefficient of variation = (std_dev / avg) * 100
        """
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            stats = self.get_std_deviation(product.id, days)
            if not stats:
                continue

            avg_price, std_dev = stats
            if avg_price > 0:
                cv = float(std_dev / avg_price * 100)
                if cv < threshold:
                    results.append({
                        'product': product,
                        'avg_price': avg_price,
                        'std_deviation': std_dev,
                        'coefficient_variation': cv,
                        'days': days
                    })

        # Sort by lowest volatility
        results.sort(key=lambda x: x['coefficient_variation'])
        return results

    def get_near_minimum(self, threshold_percent: float = 5.0, store: Optional[Store] = None) -> List[dict]:
        """Get products where current price is within threshold% of the historical minimum."""
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            if not product.current_price or not product.lowest_price:
                continue

            if product.lowest_price > 0:
                diff_percent = float((product.current_price - product.lowest_price) / product.lowest_price * 100)
                if 0 < diff_percent <= threshold_percent:
                    results.append({
                        'product': product,
                        'lowest_price': product.lowest_price,
                        'diff_percent': diff_percent
                    })

        # Sort by closest to minimum
        results.sort(key=lambda x: x['diff_percent'])
        return results

    def get_opportunity_score(self, store: Optional[Store] = None) -> List[dict]:
        """
        Calculate an opportunity score for each product based on multiple factors.

        Score considers:
        - Distance from minimum (higher = better)
        - Below average (bonus points)
        - Below std deviation (bonus points)
        - Recent price drop (bonus points)
        """
        products = self.get_all_products(active_only=True, store=store)
        results = []

        for product in products:
            if not product.current_price or not product.lowest_price or not product.highest_price:
                continue

            score = 0
            factors = []

            # Factor 1: Position in price range (0-40 points)
            price_range = product.highest_price - product.lowest_price
            if price_range > 0:
                position = (product.highest_price - product.current_price) / price_range
                range_score = float(position * 40)
                score += range_score
                if range_score >= 30:
                    factors.append(f"Próximo do mínimo ({range_score:.0f}pts)")

            # Factor 2: At minimum (20 bonus points)
            if product.current_price <= product.lowest_price:
                score += 20
                factors.append("No mínimo histórico (+20pts)")

            # Factor 3: Below 30d average (15 points)
            avg_30 = self.get_average_price(product.id, 30)
            if avg_30 and product.current_price < avg_30:
                score += 15
                factors.append("Abaixo da média 30d (+15pts)")

            # Factor 4: Below 1 std deviation (15 points)
            stats = self.get_std_deviation(product.id, 30)
            if stats:
                avg, std = stats
                if product.current_price <= (avg - std):
                    score += 15
                    factors.append("Abaixo de 1 DP (+15pts)")
                    # Factor 5: Below 2 std deviation (additional 10 points)
                    if product.current_price <= (avg - std * 2):
                        score += 10
                        factors.append("Abaixo de 2 DP (+10pts)")

            if score > 0:
                results.append({
                    'product': product,
                    'score': score,
                    'factors': factors
                })

        # Sort by highest score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

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

    def plot_price_history(self, product_id: int, days: int = 30) -> bool:
        """
        Plot price history chart in the terminal.

        Args:
            product_id: ID of the product
            days: Number of days to show (default: 30)

        Returns:
            True if chart was displayed, False if no data
        """
        try:
            import plotext as plt
        except ImportError:
            print("Erro: plotext não instalado. Execute: pip install plotext")
            return False

        product = self.get_product_by_id(product_id)
        if not product:
            print(f"Produto com ID {product_id} não encontrado.")
            return False

        history = self.get_price_history(product_id, days)
        if not history:
            print("Sem histórico de preços disponível.")
            return False

        # Sort by date (oldest first)
        history = sorted(history, key=lambda h: h.recorded_at)

        # Extract dates and prices (use numeric indices for x-axis)
        date_labels = [h.recorded_at.strftime("%d/%m") for h in history]
        x_values = list(range(len(history)))
        prices = [float(h.price) for h in history]

        # Calculate statistics
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        current = prices[-1] if prices else 0

        # Get std deviation info
        stats = self.get_std_deviation(product_id, days)
        threshold_1 = None
        threshold_2 = None
        if stats:
            avg, std_dev = stats
            threshold_1 = float(avg - std_dev)
            threshold_2 = float(avg - (std_dev * 2))

        # Clear and setup plot
        plt.clear_figure()
        plt.theme('dark')

        # Title
        title = f"{product.title[:50]}..." if product.title and len(product.title) > 50 else product.title
        plt.title(f"📈 Histórico de Preços: {title}")

        # Plot price line using numeric x-axis
        plt.plot(x_values, prices, label="Preço", marker="braille", color="cyan")

        # Set custom x-axis tick labels (show subset to avoid crowding)
        num_ticks = min(10, len(date_labels))
        if num_ticks > 1:
            step = max(1, len(date_labels) // num_ticks)
            tick_indices = list(range(0, len(date_labels), step))
            tick_labels = [date_labels[i] for i in tick_indices]
            plt.xticks(tick_indices, tick_labels)

        # Plot average line
        plt.hline(avg_price, color="yellow")

        # Plot std deviation thresholds if available
        if threshold_1:
            plt.hline(threshold_1, color="green")
        if threshold_2:
            plt.hline(threshold_2, color="red")

        # Labels
        plt.xlabel("Data")
        plt.ylabel("Preço (R$)")

        # Show the plot
        plt.show()

        # Print legend below chart
        print(f"\n{'─' * 60}")
        print(f"📊 Estatísticas ({days} dias) - {len(history)} registros")
        print(f"{'─' * 60}")
        print(f"  Atual:    R$ {current:.2f}")
        print(f"  Média:    R$ {avg_price:.2f} ━━ (linha amarela)")
        print(f"  Mínimo:   R$ {min_price:.2f}")
        print(f"  Máximo:   R$ {max_price:.2f}")
        if threshold_1:
            print(f"  1 DP:     R$ {threshold_1:.2f} ━━ (linha verde)")
        if threshold_2:
            print(f"  2 DP:     R$ {threshold_2:.2f} ━━ (linha vermelha)")

        # Status indicator
        if current <= (threshold_2 or 0):
            print(f"\n  🔥 OFERTA EXCEPCIONAL! Preço abaixo de 2 desvios padrão!")
        elif current <= (threshold_1 or 0):
            print(f"\n  ✅ Bom preço! Abaixo de 1 desvio padrão.")
        elif current <= min_price:
            print(f"\n  📉 Preço no mínimo histórico!")

        print(f"{'─' * 60}")

        return True

