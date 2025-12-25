"""
Alert service for managing price alerts based on standard deviation.
"""

from decimal import Decimal
from typing import Optional, List

from database import get_db, Alert, Product
from database.models import AlertType
from services.product_service import ProductService


class AlertService:
    """Service for alert management based on standard deviation analysis."""

    # Mapping of AlertType to (days, num_std_dev)
    ALERT_CONFIG = {
        AlertType.STD_DEV_1_30D: (30, 1),
        AlertType.STD_DEV_1_90D: (90, 1),
        AlertType.STD_DEV_1_180D: (180, 1),
        AlertType.STD_DEV_2_30D: (30, 2),
        AlertType.STD_DEV_2_90D: (90, 2),
        AlertType.STD_DEV_2_180D: (180, 2),
    }

    def __init__(self):
        self.db = get_db()
        self.product_service = ProductService()

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
                p.current_price
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

    def check_std_deviation_alerts(self) -> dict:
        """
        Check all products for standard deviation alerts.

        Returns a dictionary with alerts organized by type.
        """
        all_alerts = self.product_service.get_all_std_deviation_alerts()

        result = {
            '1_std_dev': {
                '30d': all_alerts.get('std_dev_1_30d', []),
                '90d': all_alerts.get('std_dev_1_90d', []),
                '180d': all_alerts.get('std_dev_1_180d', []),
            },
            '2_std_dev': {
                '30d': all_alerts.get('std_dev_2_30d', []),
                '90d': all_alerts.get('std_dev_2_90d', []),
                '180d': all_alerts.get('std_dev_2_180d', []),
            }
        }

        return result

    def get_best_deals(self) -> List[dict]:
        """
        Get products that are at 2 standard deviations below average.
        These are the best deals available.
        """
        # Products at 2 std dev for any period are exceptional deals
        best_deals = []

        for days in [30, 90, 180]:
            deals = self.product_service.get_products_below_std_deviation(days, 2)
            for deal in deals:
                # Avoid duplicates
                product_ids = [d['product'].id for d in best_deals]
                if deal['product'].id not in product_ids:
                    best_deals.append(deal)

        # Sort by biggest discount
        best_deals.sort(key=lambda x: x['diff'], reverse=True)

        return best_deals

    def print_alert(self, product: Product, message: str, stats: dict = None) -> None:
        """Print alert notification to console."""
        print("\n" + "=" * 60)
        print("ALERTA DE PRECO!")
        print("=" * 60)
        print(f"Produto: {product.title[:50]}..." if product.title and len(product.title) > 50 else f"Produto: {product.title}")
        print(f"SKU: {product.asin}")
        print(f"Loja: {product.store.display_name}")
        print(f"Preco Atual: R$ {product.current_price:.2f}")

        if stats:
            print(f"\nEstatísticas ({stats.get('days', 30)} dias):")
            print(f"  Média: R$ {stats.get('avg_price', 0):.2f}")
            print(f"  Desvio Padrão: R$ {stats.get('std_deviation', 0):.2f}")
            print(f"  Limite ({stats.get('num_std_dev', 1)} DP): R$ {stats.get('threshold', 0):.2f}")
            print(f"  Economia: R$ {stats.get('diff', 0):.2f}")

        print(f"\nURL: {product.url}")
        print(message)
        print("=" * 60 + "\n")

    def print_std_deviation_summary(self) -> None:
        """Print a summary of all standard deviation alerts."""
        alerts = self.check_std_deviation_alerts()

        print("\n" + "=" * 70)
        print("📊 RESUMO DE ALERTAS POR DESVIO PADRÃO")
        print("=" * 70)

        # 2 std dev alerts (best deals)
        print("\n🔥 OFERTAS EXCEPCIONAIS (2 Desvios Padrão)")
        print("-" * 70)
        for period in ['30d', '90d', '180d']:
            items = alerts['2_std_dev'][period]
            if items:
                print(f"\n  📅 Período: {period}")
                for item in items:
                    p = item['product']
                    print(f"    • {p.title[:40]}...")
                    print(f"      R$ {p.current_price:.2f} (limite: R$ {item['threshold']:.2f})")
            else:
                print(f"\n  📅 Período: {period} - Nenhum produto")

        # 1 std dev alerts (good deals)
        print("\n\n💰 BOAS OFERTAS (1 Desvio Padrão)")
        print("-" * 70)
        for period in ['30d', '90d', '180d']:
            items = alerts['1_std_dev'][period]
            if items:
                print(f"\n  📅 Período: {period}")
                for item in items:
                    p = item['product']
                    print(f"    • {p.title[:40]}...")
                    print(f"      R$ {p.current_price:.2f} (limite: R$ {item['threshold']:.2f})")
            else:
                print(f"\n  📅 Período: {period} - Nenhum produto")

        print("\n" + "=" * 70)
