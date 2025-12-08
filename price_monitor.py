#!/usr/bin/env python3
"""
Amazon Price Monitor CLI

A command-line tool to monitor Amazon product prices and get alerts
when prices drop to your target.

Usage:
    python price_monitor.py add <url> <target_price>
    python price_monitor.py list
    python price_monitor.py check
    python price_monitor.py update
    python price_monitor.py alerts
    python price_monitor.py history <product_id>
    python price_monitor.py remove <product_id>
    python price_monitor.py init-db
"""

import sys
import argparse
from decimal import Decimal
from datetime import datetime
from typing import Optional

from tabulate import tabulate

from config import settings
from database import get_db
from database.models import AlertType
from services import ProductService, AlertService
from utils import parse_price, format_currency, truncate_string, validate_amazon_url


def init_database():
    """Initialize the database schema."""
    print("Initializing database...")
    db = get_db()
    db.init_database()
    print("Database initialized successfully!")


def add_product(url: str, target_price_str: str):
    """Add a new product to monitor."""
    # Validate URL
    if not validate_amazon_url(url):
        print(f"Error: '{url}' does not appear to be a valid Amazon URL.")
        sys.exit(1)

    # Parse target price
    target_price = parse_price(target_price_str)
    if not target_price:
        print(f"Error: Could not parse price '{target_price_str}'.")
        print("Use formats like: 80,99 or 80.99")
        print("")
        print("TIP: If using R$, use single quotes to avoid shell issues:")
        print("     python price_monitor.py add \"URL\" '80,99'")
        sys.exit(1)

    print(f"Adding product with target price {format_currency(target_price)}...")
    print("Fetching product information from Amazon...")

    try:
        service = ProductService()
        product = service.add_product(url, target_price)

        print("\n✅ Product added successfully!")
        print("-" * 50)
        print(f"ID: {product.id}")
        print(f"Title: {product.title}")
        print(f"ASIN: {product.asin}")
        print(f"Current Price: {format_currency(product.current_price)}")
        print(f"Target Price: {format_currency(product.target_price)}")

        if product.current_price:
            if product.current_price <= product.target_price:
                print("\n🎉 Great news! The product is already at or below your target price!")
            else:
                diff = product.current_price - product.target_price
                percent = (diff / product.current_price) * 100
                print(f"\nPrice needs to drop {format_currency(diff)} ({percent:.1f}%) to reach target.")

        # Create default target alert
        alert_service = AlertService()
        alert_service.create_alert(product.id, AlertType.TARGET_REACHED)
        print("\n📢 Alert created: You'll be notified when the price reaches your target.")

    except Exception as e:
        print(f"\n❌ Error adding product: {e}")
        sys.exit(1)


def list_products():
    """List all monitored products."""
    try:
        service = ProductService()
        products = service.get_all_products()

        if not products:
            print("No products being monitored.")
            print("Add a product with: python price_monitor.py add <url> <target_price>")
            return

        # Prepare table data
        table_data = []
        for p in products:
            status = "✅" if p.current_price and p.current_price <= p.target_price else "👀"

            diff = ""
            if p.current_price:
                price_diff = p.current_price - p.target_price
                if price_diff <= 0:
                    diff = f"✅ -{format_currency(abs(price_diff))}"
                else:
                    diff = f"⬇️ {format_currency(price_diff)}"

            table_data.append([
                p.id,
                truncate_string(p.title, 40),
                format_currency(p.current_price),
                format_currency(p.target_price),
                diff,
                status,
            ])

        headers = ["ID", "Product", "Current", "Target", "Difference", "Status"]
        print(f"\n📦 Monitored Products ({len(products)})")
        print("-" * 80)
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 80)

    except Exception as e:
        print(f"Error listing products: {e}")
        sys.exit(1)


def check_prices():
    """Check current prices and show alerts."""
    print("Checking prices and alerts...")

    try:
        product_service = ProductService()
        alert_service = AlertService()

        # Get products at target price
        at_target = product_service.get_products_at_target()

        if at_target:
            print(f"\n🎉 {len(at_target)} product(s) at or below target price!")
            print("=" * 60)

            for product in at_target:
                savings = product.target_price - product.current_price
                print(f"\n📦 {truncate_string(product.title, 50)}")
                print(f"   Current: {format_currency(product.current_price)}")
                print(f"   Target:  {format_currency(product.target_price)}")
                print(f"   Savings: {format_currency(savings)}")
                print(f"   URL: {product.url}")

                # Print alert
                alert_service.print_alert(
                    product,
                    "Preco atingiu seu alvo!"
                )

            print("\n" + "=" * 60)
        else:
            print("\n👀 No products at target price yet.")

        # Check for products below average
        below_avg = product_service.get_products_below_average(days=7, threshold_percent=settings.PRICE_DROP_THRESHOLD_PERCENT)

        if below_avg:
            print(f"\n📉 {len(below_avg)} product(s) below 7-day average:")
            for item in below_avg:
                product = item['product']
                print(f"   • {truncate_string(product.title, 40)}: {format_currency(product.current_price)} ({item['discount_percent']:.1f}% below avg)")

        # Summary
        all_products = product_service.get_all_products()
        print(f"\n📊 Summary: {len(at_target)}/{len(all_products)} products at target price")

    except Exception as e:
        print(f"Error checking prices: {e}")
        sys.exit(1)


def update_prices():
    """Update prices for all monitored products."""
    print("Updating prices for all products...")
    print("This may take a while to avoid being blocked by Amazon.\n")

    try:
        service = ProductService()
        alert_service = AlertService()

        products = service.get_all_products()
        if not products:
            print("No products to update.")
            return

        updated = service.update_all_prices()

        print(f"\n✅ Updated {len(updated)} product(s)")

        # Check alerts after update
        newly_triggered = alert_service.check_alerts(updated)

        if newly_triggered:
            print(f"\n{len(newly_triggered)} novo(s) alerta(s) disparado(s)!")
            for item in newly_triggered:
                product = item['product']
                alert_service.print_alert(
                    product,
                    f"Alerta disparado em {format_currency(item['triggered_price'])}"
                )

        # Show summary
        check_prices()

    except Exception as e:
        print(f"Error updating prices: {e}")
        sys.exit(1)


def show_alerts():
    """Show all triggered alerts."""
    try:
        service = AlertService()
        triggered = service.get_triggered_alerts()

        if not triggered:
            print("No triggered alerts.")
            return

        print(f"\n🔔 Triggered Alerts ({len(triggered)})")
        print("=" * 60)

        for item in triggered:
            alert = item['alert']
            product = item['product']

            print(f"\n📦 {truncate_string(product['title'], 50)}")
            print(f"   ASIN: {product['asin']}")
            print(f"   Current Price: {format_currency(product['current_price'])}")
            print(f"   Target Price: {format_currency(product['target_price'])}")
            print(f"   Triggered At: {alert.triggered_at}")
            print(f"   URL: {product['url']}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"Error showing alerts: {e}")
        sys.exit(1)


def show_history(product_id: int, days: int = 30):
    """Show price history for a product."""
    try:
        service = ProductService()

        product = service.get_product_by_id(product_id)
        if not product:
            print(f"Product with ID {product_id} not found.")
            sys.exit(1)

        history = service.get_price_history(product_id, days)

        print(f"\n📊 Price History: {truncate_string(product.title, 40)}")
        print(f"   Target: {format_currency(product.target_price)}")
        print("-" * 50)

        if not history:
            print("No price history available.")
            return

        # Calculate statistics
        prices = [h.price for h in history]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)

        print(f"\nStatistics (last {days} days):")
        print(f"   Average: {format_currency(Decimal(str(avg_price)))}")
        print(f"   Lowest:  {format_currency(min_price)}")
        print(f"   Highest: {format_currency(max_price)}")
        print(f"   Records: {len(history)}")

        # Show recent history
        print(f"\nRecent prices:")
        table_data = []
        for h in history[:15]:  # Last 15 records
            status = "✅" if h.price <= product.target_price else ""
            table_data.append([
                h.recorded_at.strftime("%Y-%m-%d %H:%M"),
                format_currency(h.price),
                status,
            ])

        headers = ["Date", "Price", "At Target"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))

    except Exception as e:
        print(f"Error showing history: {e}")
        sys.exit(1)


def remove_product(product_id: int):
    """Remove a product from monitoring."""
    try:
        service = ProductService()

        product = service.get_product_by_id(product_id)
        if not product:
            print(f"Product with ID {product_id} not found.")
            sys.exit(1)

        # Confirm deletion
        print(f"Product: {product.title}")
        confirm = input("Are you sure you want to remove this product? (y/N): ")

        if confirm.lower() != 'y':
            print("Cancelled.")
            return

        service.delete_product(product_id)
        print(f"✅ Product removed successfully.")

    except Exception as e:
        print(f"Error removing product: {e}")
        sys.exit(1)


def show_product_detail(product_id: int):
    """Show detailed information about a product."""
    try:
        service = ProductService()
        product = service.get_product_by_id(product_id)

        if not product:
            print(f"Product with ID {product_id} not found.")
            sys.exit(1)

        avg_7 = service.get_average_price(product_id, 7)
        avg_30 = service.get_average_price(product_id, 30)

        print("\n" + "=" * 60)
        print(f"📦 {product.title}")
        print("=" * 60)
        print(f"ID:           {product.id}")
        print(f"ASIN:         {product.asin}")
        print(f"URL:          {product.url}")
        print(f"\n💰 Prices:")
        print(f"   Current:   {format_currency(product.current_price)}")
        print(f"   Target:    {format_currency(product.target_price)}")
        print(f"   Lowest:    {format_currency(product.lowest_price)}")
        print(f"   Highest:   {format_currency(product.highest_price)}")
        print(f"   Avg (7d):  {format_currency(avg_7)}")
        print(f"   Avg (30d): {format_currency(avg_30)}")

        if product.current_price and product.target_price:
            diff = product.current_price - product.target_price
            if diff <= 0:
                print(f"\n✅ At target! Savings: {format_currency(abs(diff))}")
            else:
                percent = (diff / product.current_price) * 100
                print(f"\n⬇️ Needs to drop: {format_currency(diff)} ({percent:.1f}%)")

        print(f"\n📅 Created: {product.created_at}")
        print(f"📅 Updated: {product.updated_at}")
        print("=" * 60)

    except Exception as e:
        print(f"Error showing product: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Amazon Price Monitor - Track product prices and get alerts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add "https://amazon.com.br/dp/B0BTXDTD6H" "R$80,99"
  %(prog)s list
  %(prog)s check
  %(prog)s update
  %(prog)s alerts
  %(prog)s history 1
  %(prog)s detail 1
  %(prog)s remove 1
  %(prog)s init-db
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init-db command
    subparsers.add_parser('init-db', help='Initialize the database')

    # add command
    add_parser = subparsers.add_parser('add', help='Add a product to monitor')
    add_parser.add_argument('url', help='Amazon product URL')
    add_parser.add_argument('target_price', help='Target price (e.g., R$80,99 or 80.99)')

    # list command
    subparsers.add_parser('list', help='List all monitored products')

    # check command
    subparsers.add_parser('check', help='Check prices and show alerts')

    # update command
    subparsers.add_parser('update', help='Update prices for all products')

    # alerts command
    subparsers.add_parser('alerts', help='Show triggered alerts')

    # history command
    history_parser = subparsers.add_parser('history', help='Show price history for a product')
    history_parser.add_argument('product_id', type=int, help='Product ID')
    history_parser.add_argument('--days', type=int, default=30, help='Number of days (default: 30)')

    # detail command
    detail_parser = subparsers.add_parser('detail', help='Show detailed product information')
    detail_parser.add_argument('product_id', type=int, help='Product ID')

    # remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a product from monitoring')
    remove_parser.add_argument('product_id', type=int, help='Product ID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    if args.command == 'init-db':
        init_database()
    elif args.command == 'add':
        add_product(args.url, args.target_price)
    elif args.command == 'list':
        list_products()
    elif args.command == 'check':
        check_prices()
    elif args.command == 'update':
        update_prices()
    elif args.command == 'alerts':
        show_alerts()
    elif args.command == 'history':
        show_history(args.product_id, args.days)
    elif args.command == 'detail':
        show_product_detail(args.product_id)
    elif args.command == 'remove':
        remove_product(args.product_id)


if __name__ == '__main__':
    main()
