"""
Alert service for managing price alerts and notifications.
"""

from decimal import Decimal
from typing import Optional, List

from database import get_db, Alert, Product
from database.models import AlertType
from config import settings


class AlertService:
    """Service for alert management and notifications."""

    def __init__(self):
        self.db = get_db()

    def create_alert(
        self,
        product_id: int,
        alert_type: AlertType,
        threshold_value: Optional[Decimal] = None,
        threshold_percentage: Optional[Decimal] = None
    ) -> Alert:
        """Create a new alert for a product."""
        query = """
            INSERT INTO alerts (product_id, alert_type, threshold_value, threshold_percentage)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            product_id,
            alert_type.value,
            float(threshold_value) if threshold_value else None,
            float(threshold_percentage) if threshold_percentage else None,
        )

        with self.db.get_cursor() as cursor:
            cursor.execute(query, params)
            alert_id = cursor.lastrowid

        return self.get_alert_by_id(alert_id)

    def get_alert_by_id(self, alert_id: int) -> Optional[Alert]:
        """Get alert by ID."""
        query = "SELECT * FROM alerts WHERE id = %s"
        results = self.db.execute_query(query, (alert_id,))
        if results:
            return Alert.from_dict(results[0])
        return None

    def get_alerts_for_product(self, product_id: int, active_only: bool = True) -> List[Alert]:
        """Get all alerts for a product."""
        query = "SELECT * FROM alerts WHERE product_id = %s"
        if active_only:
            query += " AND is_active = TRUE"
        query += " ORDER BY created_at DESC"

        results = self.db.execute_query(query, (product_id,))
        return [Alert.from_dict(row) for row in results]

    def get_all_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        query = """
            SELECT a.* FROM alerts a
            JOIN products p ON a.product_id = p.id
            WHERE a.is_active = TRUE AND p.is_active = TRUE
            ORDER BY a.created_at DESC
        """
        results = self.db.execute_query(query)
        return [Alert.from_dict(row) for row in results]

    def get_triggered_alerts(self) -> List[dict]:
        """Get all triggered alerts with product information."""
        query = """
            SELECT
                a.*,
                p.asin,
                p.title,
                p.url,
                p.current_price,
                p.target_price
            FROM alerts a
            JOIN products p ON a.product_id = p.id
            WHERE a.is_triggered = TRUE AND a.is_active = TRUE
            ORDER BY a.triggered_at DESC
        """
        results = self.db.execute_query(query)

        triggered = []
        for row in results:
            triggered.append({
                'alert': Alert.from_dict(row),
                'product': {
                    'asin': row['asin'],
                    'title': row['title'],
                    'url': row['url'],
                    'current_price': Decimal(str(row['current_price'])) if row['current_price'] else None,
                    'target_price': Decimal(str(row['target_price'])),
                }
            })

        return triggered

    def trigger_alert(self, alert_id: int, triggered_price: Decimal) -> None:
        """Mark an alert as triggered."""
        query = """
            UPDATE alerts
            SET is_triggered = TRUE, triggered_price = %s, triggered_at = NOW()
            WHERE id = %s
        """
        self.db.execute_query(query, (float(triggered_price), alert_id), fetch=False)

    def reset_alert(self, alert_id: int) -> None:
        """Reset a triggered alert."""
        query = """
            UPDATE alerts
            SET is_triggered = FALSE, triggered_price = NULL, triggered_at = NULL
            WHERE id = %s
        """
        self.db.execute_query(query, (alert_id,), fetch=False)

    def deactivate_alert(self, alert_id: int) -> None:
        """Deactivate an alert."""
        query = "UPDATE alerts SET is_active = FALSE WHERE id = %s"
        self.db.execute_query(query, (alert_id,), fetch=False)

    def check_alerts(self, products: List[Product]) -> List[dict]:
        """
        Check all alerts against current product prices.

        Returns:
            List of newly triggered alerts with product info
        """
        newly_triggered = []

        for product in products:
            if not product.current_price:
                continue

            alerts = self.get_alerts_for_product(product.id)

            for alert in alerts:
                if alert.is_triggered:
                    continue

                should_trigger = False

                if alert.alert_type == AlertType.TARGET_REACHED:
                    # Check if price is at or below target
                    if product.current_price <= product.target_price:
                        should_trigger = True

                elif alert.alert_type == AlertType.PRICE_DROP:
                    # Check if price dropped by threshold percentage
                    if alert.threshold_percentage and product.highest_price:
                        threshold = product.highest_price * (1 - alert.threshold_percentage / 100)
                        if product.current_price <= threshold:
                            should_trigger = True

                elif alert.alert_type == AlertType.BELOW_AVERAGE:
                    # This requires calculating average - handled separately
                    pass

                if should_trigger:
                    self.trigger_alert(alert.id, product.current_price)
                    newly_triggered.append({
                        'alert': alert,
                        'product': product,
                        'triggered_price': product.current_price,
                    })

        return newly_triggered

    def check_target_alerts(self) -> List[dict]:
        """Check which products have reached their target price."""
        query = """
            SELECT
                p.*,
                a.id as alert_id,
                a.alert_type,
                a.is_triggered as alert_triggered
            FROM products p
            LEFT JOIN alerts a ON p.id = a.product_id AND a.alert_type = 'target_reached' AND a.is_active = TRUE
            WHERE p.is_active = TRUE
            AND p.current_price IS NOT NULL
            AND p.current_price <= p.target_price
            ORDER BY (p.target_price - p.current_price) DESC
        """
        results = self.db.execute_query(query)

        alerts = []
        for row in results:
            product = Product.from_dict(row)
            savings = product.target_price - product.current_price

            alert_info = {
                'product': product,
                'savings': savings,
                'alert_id': row.get('alert_id'),
                'is_new': row.get('alert_triggered') is False if row.get('alert_id') else True,
            }

            # Trigger alert if not already triggered
            if row.get('alert_id') and not row.get('alert_triggered'):
                self.trigger_alert(row['alert_id'], product.current_price)

            alerts.append(alert_info)

        return alerts

    def print_alert(self, product: Product, message: str) -> None:
        """Print alert notification to console."""
        print("\n" + "=" * 60)
        print("ALERTA DE PRECO!")
        print("=" * 60)
        print(f"Produto: {product.title[:50]}..." if product.title and len(product.title) > 50 else f"Produto: {product.title}")
        print(f"ASIN: {product.asin}")
        print(f"Preco Atual: R$ {product.current_price:.2f}")
        print(f"Preco Alvo: R$ {product.target_price:.2f}")
        if product.current_price and product.target_price:
            savings = product.target_price - product.current_price
            print(f"Economia: R$ {savings:.2f}")
        print(f"URL: {product.url}")
        print(message)
        print("=" * 60 + "\n")
