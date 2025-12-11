"""
Database models and data classes for DiscountCart Price Monitor.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class Store(Enum):
    """Supported stores for price monitoring."""
    ZAFFARI = 'zaffari'
    CARREFOUR = 'carrefour'

    @classmethod
    def from_url(cls, url: str) -> 'Store':
        """Detect store from URL."""
        url_lower = url.lower()
        if 'carrefour' in url_lower:
            return cls.CARREFOUR
        elif 'zaffari' in url_lower:
            return cls.ZAFFARI
        raise ValueError(f"URL não reconhecida: {url}")

    @property
    def display_name(self) -> str:
        """Get display name for the store."""
        names = {
            'zaffari': 'Zaffari',
            'carrefour': 'Carrefour',
        }
        return names.get(self.value, self.value.title())


class AlertType(Enum):
    """Types of price alerts."""
    TARGET_REACHED = 'target_reached'
    PRICE_DROP = 'price_drop'
    BELOW_AVERAGE = 'below_average'
    STD_DEVIATION = 'std_deviation'  # Alerta quando preço cai 1 desvio padrão


@dataclass
class Product:
    """Represents a monitored product."""
    id: Optional[int] = None
    asin: str = ''
    url: str = ''
    title: Optional[str] = None
    image_url: Optional[str] = None
    store: Store = Store.ZAFFARI
    category: Optional[str] = None
    target_price: Decimal = Decimal('0.00')
    current_price: Optional[Decimal] = None
    lowest_price: Optional[Decimal] = None
    highest_price: Optional[Decimal] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        """Create Product from dictionary."""
        store = data.get('store', 'zaffari')
        if isinstance(store, str):
            store = Store(store)
        return cls(
            id=data.get('id'),
            asin=data.get('asin', ''),
            url=data.get('url', ''),
            title=data.get('title'),
            image_url=data.get('image_url'),
            store=store,
            category=data.get('category'),
            target_price=Decimal(str(data.get('target_price', 0))),
            current_price=Decimal(str(data['current_price'])) if data.get('current_price') else None,
            lowest_price=Decimal(str(data['lowest_price'])) if data.get('lowest_price') else None,
            highest_price=Decimal(str(data['highest_price'])) if data.get('highest_price') else None,
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> dict:
        """Convert Product to dictionary."""
        return {
            'id': self.id,
            'asin': self.asin,
            'url': self.url,
            'title': self.title,
            'image_url': self.image_url,
            'store': self.store.value if isinstance(self.store, Store) else self.store,
            'category': self.category,
            'target_price': float(self.target_price),
            'current_price': float(self.current_price) if self.current_price else None,
            'lowest_price': float(self.lowest_price) if self.lowest_price else None,
            'highest_price': float(self.highest_price) if self.highest_price else None,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @property
    def price_status(self) -> str:
        """Get current price status relative to target."""
        if self.current_price is None:
            return 'UNKNOWN'
        if self.current_price <= self.target_price:
            return 'TARGET_REACHED'
        if self.lowest_price and self.current_price < self.lowest_price:
            return 'NEW_LOW'
        return 'MONITORING'

    @property
    def discount_from_target(self) -> Optional[float]:
        """Calculate percentage discount needed to reach target."""
        if self.current_price and self.current_price > 0:
            return float((self.current_price - self.target_price) / self.current_price * 100)
        return None


@dataclass
class PriceHistory:
    """Represents a price history record."""
    id: Optional[int] = None
    product_id: int = 0
    price: Decimal = Decimal('0.00')
    was_available: bool = True
    recorded_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'PriceHistory':
        """Create PriceHistory from dictionary."""
        return cls(
            id=data.get('id'),
            product_id=data.get('product_id', 0),
            price=Decimal(str(data.get('price', 0))),
            was_available=data.get('was_available', True),
            recorded_at=data.get('recorded_at'),
        )


@dataclass
class Alert:
    """Represents a price alert."""
    id: Optional[int] = None
    product_id: int = 0
    alert_type: AlertType = AlertType.TARGET_REACHED
    threshold_value: Optional[Decimal] = None
    threshold_percentage: Optional[Decimal] = None
    is_triggered: bool = False
    triggered_price: Optional[Decimal] = None
    triggered_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Alert':
        """Create Alert from dictionary."""
        alert_type = data.get('alert_type', 'target_reached')
        if isinstance(alert_type, str):
            alert_type = AlertType(alert_type)

        return cls(
            id=data.get('id'),
            product_id=data.get('product_id', 0),
            alert_type=alert_type,
            threshold_value=Decimal(str(data['threshold_value'])) if data.get('threshold_value') else None,
            threshold_percentage=Decimal(str(data['threshold_percentage'])) if data.get('threshold_percentage') else None,
            is_triggered=data.get('is_triggered', False),
            triggered_price=Decimal(str(data['triggered_price'])) if data.get('triggered_price') else None,
            triggered_at=data.get('triggered_at'),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )


@dataclass
class ProductSummary:
    """Summary view of a product with statistics."""
    id: int
    asin: str
    title: Optional[str]
    store: Store
    category: Optional[str]
    current_price: Optional[Decimal]
    target_price: Decimal
    lowest_price: Optional[Decimal]
    highest_price: Optional[Decimal]
    avg_price_7days: Optional[Decimal]
    avg_price_30days: Optional[Decimal]
    total_price_records: int
    status: str
    is_active: bool
    updated_at: Optional[datetime]

    @classmethod
    def from_dict(cls, data: dict) -> 'ProductSummary':
        """Create ProductSummary from dictionary."""
        store = data.get('store', 'zaffari')
        if isinstance(store, str):
            store = Store(store)
        return cls(
            id=data.get('id', 0),
            asin=data.get('asin', ''),
            title=data.get('title'),
            store=store,
            category=data.get('category'),
            current_price=Decimal(str(data['current_price'])) if data.get('current_price') else None,
            target_price=Decimal(str(data.get('target_price', 0))),
            lowest_price=Decimal(str(data['lowest_price'])) if data.get('lowest_price') else None,
            highest_price=Decimal(str(data['highest_price'])) if data.get('highest_price') else None,
            avg_price_7days=Decimal(str(data['avg_price_7days'])) if data.get('avg_price_7days') else None,
            avg_price_30days=Decimal(str(data['avg_price_30days'])) if data.get('avg_price_30days') else None,
            total_price_records=data.get('total_price_records', 0),
            status=data.get('status', 'MONITORING'),
            is_active=data.get('is_active', True),
            updated_at=data.get('updated_at'),
        )
