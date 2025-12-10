#!/usr/bin/env python3
"""
DiscountCart Price Monitor CLI

A command-line tool to monitor product prices from Zaffari and Carrefour
and get alerts when prices drop to your target.

Usage:
    python price_monitor.py add <url> <target_price>
    python price_monitor.py list [--store zaffari|carrefour]
    python price_monitor.py check
    python price_monitor.py update
    python price_monitor.py alerts
    python price_monitor.py history <product_id>
    python price_monitor.py remove <product_id>
    python price_monitor.py init-db
    python price_monitor.py migrate
"""

import sys
import argparse
from decimal import Decimal

from tabulate import tabulate

from config import settings
from database import get_db, Store
from database.models import AlertType
from services import ProductService, AlertService
from utils import parse_price, format_currency, truncate_string, validate_product_url


def init_database():
    """Initialize the database schema."""
    print("Inicializando banco de dados...")
    db = get_db()
    db.init_database()
    print("Banco de dados inicializado com sucesso!")


def add_product(url: str, target_price_str: str):
    """Add a new product to monitor."""
    # Validate URL
    is_valid, store_name = validate_product_url(url)
    if not is_valid:
        print(f"Erro: '{url}' não parece ser uma URL válida.")
        print("URLs suportadas:")
        print("  - Zaffari: https://www.zaffari.com.br/produto-123/p")
        print("  - Carrefour: https://mercado.carrefour.com.br/produto-123/p")
        sys.exit(1)

    # Parse target price
    target_price = parse_price(target_price_str)
    if not target_price:
        print(f"Erro: Não foi possível interpretar o preço '{target_price_str}'.")
        print("Use formatos como: 80,99 ou 80.99")
        print("")
        print("DICA: Use aspas simples para evitar problemas com o shell:")
        print("     python price_monitor.py add \"URL\" '80,99'")
        sys.exit(1)

    store_display = Store(store_name).display_name
    print(f"Adicionando produto com preço alvo {format_currency(target_price)}...")
    print(f"Buscando informações do produto no {store_display}...")

    try:
        service = ProductService()
        product = service.add_product(url, target_price)

        print("\n✅ Produto adicionado com sucesso!")
        print("-" * 50)
        print(f"ID: {product.id}")
        print(f"Loja: {product.store.display_name}")
        print(f"Título: {product.title}")
        print(f"SKU: {product.asin}")
        print(f"Preço Atual: {format_currency(product.current_price)}")
        print(f"Preço Alvo: {format_currency(product.target_price)}")

        if product.current_price:
            if product.current_price <= product.target_price:
                print("\n🎉 Ótima notícia! O produto já está no preço alvo ou abaixo!")
            else:
                diff = product.current_price - product.target_price
                percent = (diff / product.current_price) * 100
                print(f"\nO preço precisa cair {format_currency(diff)} ({percent:.1f}%) para atingir o alvo.")

        # Create default target alert
        alert_service = AlertService()
        alert_service.create_alert(product.id, AlertType.TARGET_REACHED)
        print("\n📢 Alerta criado: Você será notificado quando o preço atingir o alvo.")

    except Exception as e:
        print(f"\n❌ Erro ao adicionar produto: {e}")
        sys.exit(1)


def list_products(store_filter: str = None):
    """List all monitored products."""
    try:
        service = ProductService()

        # Parse store filter
        store = None
        if store_filter:
            try:
                store = Store(store_filter.lower())
            except ValueError:
                print(f"Erro: Loja '{store_filter}' não reconhecida.")
                print("Lojas disponíveis: zaffari, carrefour")
                sys.exit(1)

        products = service.get_all_products(store=store)

        if not products:
            if store:
                print(f"Nenhum produto do {store.display_name} sendo monitorado.")
            else:
                print("Nenhum produto sendo monitorado.")
            print("Adicione um produto com: python price_monitor.py add <url> <preco_alvo>")
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

            # Store emoji/abbreviation
            store_abbr = "🟢" if p.store == Store.ZAFFARI else "🔵"

            table_data.append([
                p.id,
                store_abbr,
                truncate_string(p.title, 35),
                format_currency(p.current_price),
                format_currency(p.target_price),
                diff,
                status,
            ])

        headers = ["ID", "Loja", "Produto", "Atual", "Alvo", "Diferença", "Status"]
        title = f"📦 Produtos Monitorados ({len(products)})"
        if store:
            title += f" - {store.display_name}"
        print(f"\n{title}")
        print("Legenda: 🟢 Zaffari | 🔵 Carrefour")
        print("-" * 90)
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 90)

    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        sys.exit(1)


def check_prices():
    """Check current prices and show alerts."""
    print("Verificando preços e alertas...")

    try:
        product_service = ProductService()
        alert_service = AlertService()

        # Get products at target price
        at_target = product_service.get_products_at_target()

        if at_target:
            print(f"\n🎉 {len(at_target)} produto(s) no preço alvo ou abaixo!")
            print("=" * 60)

            for product in at_target:
                savings = product.target_price - product.current_price
                print(f"\n📦 {truncate_string(product.title, 50)}")
                print(f"   Atual: {format_currency(product.current_price)}")
                print(f"   Alvo:  {format_currency(product.target_price)}")
                print(f"   Economia: {format_currency(savings)}")
                print(f"   URL: {product.url}")

                # Print alert
                alert_service.print_alert(
                    product,
                    "Preço atingiu seu alvo!"
                )

            print("\n" + "=" * 60)
        else:
            print("\n👀 Nenhum produto no preço alvo ainda.")

        # Check for products below average
        below_avg = product_service.get_products_below_average(days=7, threshold_percent=settings.PRICE_DROP_THRESHOLD_PERCENT)

        if below_avg:
            print(f"\n📉 {len(below_avg)} produto(s) abaixo da média de 7 dias:")
            for item in below_avg:
                product = item['product']
                print(f"   • {truncate_string(product.title, 40)}: {format_currency(product.current_price)} ({item['discount_percent']:.1f}% abaixo da média)")

        # Summary
        all_products = product_service.get_all_products()
        print(f"\n📊 Resumo: {len(at_target)}/{len(all_products)} produtos no preço alvo")

    except Exception as e:
        print(f"Erro ao verificar preços: {e}")
        sys.exit(1)


def update_prices():
    """Update prices for all monitored products."""
    print("Atualizando preços de todos os produtos...")
    print("Isso pode demorar um pouco para evitar bloqueio pelo site.\n")

    try:
        service = ProductService()
        alert_service = AlertService()

        products = service.get_all_products()
        if not products:
            print("Nenhum produto para atualizar.")
            return

        updated = service.update_all_prices()

        print(f"\n✅ {len(updated)} produto(s) atualizado(s)")

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
        print(f"Erro ao atualizar preços: {e}")
        sys.exit(1)


def show_alerts():
    """Show all triggered alerts."""
    try:
        service = AlertService()
        triggered = service.get_triggered_alerts()

        if not triggered:
            print("Nenhum alerta disparado.")
            return

        print(f"\n🔔 Alertas Disparados ({len(triggered)})")
        print("=" * 60)

        for item in triggered:
            alert = item['alert']
            product = item['product']

            print(f"\n📦 {truncate_string(product['title'], 50)}")
            print(f"   SKU: {product['asin']}")
            print(f"   Preço Atual: {format_currency(product['current_price'])}")
            print(f"   Preço Alvo: {format_currency(product['target_price'])}")
            print(f"   Disparado em: {alert.triggered_at}")
            print(f"   URL: {product['url']}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"Erro ao mostrar alertas: {e}")
        sys.exit(1)


def show_history(product_id: int, days: int = 30):
    """Show price history for a product."""
    try:
        service = ProductService()

        product = service.get_product_by_id(product_id)
        if not product:
            print(f"Produto com ID {product_id} não encontrado.")
            sys.exit(1)

        history = service.get_price_history(product_id, days)

        print(f"\n📊 Histórico de Preços: {truncate_string(product.title, 40)}")
        print(f"   Alvo: {format_currency(product.target_price)}")
        print("-" * 50)

        if not history:
            print("Nenhum histórico disponível.")
            return

        # Calculate statistics
        prices = [h.price for h in history]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)

        print(f"\nEstatísticas (últimos {days} dias):")
        print(f"   Média:   {format_currency(Decimal(str(avg_price)))}")
        print(f"   Mínimo:  {format_currency(min_price)}")
        print(f"   Máximo:  {format_currency(max_price)}")
        print(f"   Registros: {len(history)}")

        # Show recent history
        print(f"\nPreços recentes:")
        table_data = []
        for h in history[:15]:  # Last 15 records
            status = "✅" if h.price <= product.target_price else ""
            table_data.append([
                h.recorded_at.strftime("%Y-%m-%d %H:%M"),
                format_currency(h.price),
                status,
            ])

        headers = ["Data", "Preço", "No Alvo"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))

    except Exception as e:
        print(f"Erro ao mostrar histórico: {e}")
        sys.exit(1)


def remove_product(product_id: int):
    """Remove a product from monitoring."""
    try:
        service = ProductService()

        product = service.get_product_by_id(product_id)
        if not product:
            print(f"Produto com ID {product_id} não encontrado.")
            sys.exit(1)

        # Confirm deletion
        print(f"Produto: {product.title}")
        confirm = input("Tem certeza que deseja remover este produto? (s/N): ")

        if confirm.lower() != 's':
            print("Cancelado.")
            return

        service.delete_product(product_id)
        print(f"✅ Produto removido com sucesso.")

    except Exception as e:
        print(f"Erro ao remover produto: {e}")
        sys.exit(1)


def show_product_detail(product_id: int):
    """Show detailed information about a product."""
    try:
        service = ProductService()
        product = service.get_product_by_id(product_id)

        if not product:
            print(f"Produto com ID {product_id} não encontrado.")
            sys.exit(1)

        avg_7 = service.get_average_price(product_id, 7)
        avg_30 = service.get_average_price(product_id, 30)

        print("\n" + "=" * 60)
        print(f"📦 {product.title}")
        print("=" * 60)
        print(f"ID:           {product.id}")
        print(f"Loja:         {product.store.display_name}")
        print(f"SKU:          {product.asin}")
        print(f"URL:          {product.url}")
        print(f"\n💰 Preços:")
        print(f"   Atual:     {format_currency(product.current_price)}")
        print(f"   Alvo:      {format_currency(product.target_price)}")
        print(f"   Mínimo:    {format_currency(product.lowest_price)}")
        print(f"   Máximo:    {format_currency(product.highest_price)}")
        print(f"   Média (7d):  {format_currency(avg_7)}")
        print(f"   Média (30d): {format_currency(avg_30)}")

        if product.current_price and product.target_price:
            diff = product.current_price - product.target_price
            if diff <= 0:
                print(f"\n✅ No alvo! Economia: {format_currency(abs(diff))}")
            else:
                percent = (diff / product.current_price) * 100
                print(f"\n⬇️ Precisa cair: {format_currency(diff)} ({percent:.1f}%)")

        print(f"\n📅 Criado: {product.created_at}")
        print(f"📅 Atualizado: {product.updated_at}")
        print("=" * 60)

    except Exception as e:
        print(f"Erro ao mostrar produto: {e}")
        sys.exit(1)


def run_migration():
    """Run database migration to add store column."""
    print("Executando migração do banco de dados...")
    db = get_db()

    # First, check if store column already exists
    check_column_query = """
        SELECT COUNT(*) as cnt FROM information_schema.columns
        WHERE table_schema = DATABASE()
        AND table_name = 'products'
        AND column_name = 'store'
    """

    try:
        result = db.execute_query(check_column_query)
        column_exists = result[0]['cnt'] > 0 if result else False

        if not column_exists:
            print("Adicionando coluna 'store' à tabela products...")
            add_column_query = """
                ALTER TABLE products
                ADD COLUMN store ENUM('zaffari', 'carrefour') NOT NULL DEFAULT 'zaffari'
                AFTER image_url
            """
            db.execute_query(add_column_query, fetch=False)
            print("✅ Coluna 'store' adicionada!")
        else:
            print("✅ Coluna 'store' já existe.")

        # Update the view
        print("Atualizando view product_summary...")
        view_query = """
            CREATE OR REPLACE VIEW product_summary AS
            SELECT
                p.id,
                p.asin,
                p.title,
                p.store,
                p.current_price,
                p.target_price,
                p.lowest_price,
                p.highest_price,
                ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)), 2) AS avg_price_7days,
                ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)), 2) AS avg_price_30days,
                (SELECT COUNT(*) FROM price_history ph WHERE ph.product_id = p.id) AS total_price_records,
                CASE
                    WHEN p.current_price <= p.target_price THEN 'TARGET_REACHED'
                    WHEN p.current_price < p.lowest_price THEN 'NEW_LOW'
                    ELSE 'MONITORING'
                END AS status,
                p.is_active,
                p.updated_at
            FROM products p
            WHERE p.is_active = TRUE
        """
        db.execute_query(view_query, fetch=False)

        print("\n✅ Migração executada com sucesso!")
        print("Agora você pode adicionar produtos do Carrefour também.")

    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        print("\nSe o erro persistir, execute manualmente:")
        print("  mysql -u USER -p DATABASE < migrations/001_add_store_column.sql")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DiscountCart Price Monitor - Monitore preços do Zaffari e Carrefour",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s add "https://www.zaffari.com.br/produto-123/p" "R$80,99"
  %(prog)s add "https://mercado.carrefour.com.br/produto-456/p" "R$50,00"
  %(prog)s list
  %(prog)s list --store zaffari
  %(prog)s list --store carrefour
  %(prog)s check
  %(prog)s update
  %(prog)s alerts
  %(prog)s history 1
  %(prog)s detail 1
  %(prog)s remove 1
  %(prog)s init-db
  %(prog)s migrate
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')

    # init-db command
    subparsers.add_parser('init-db', help='Inicializar banco de dados')

    # migrate command
    subparsers.add_parser('migrate', help='Executar migração para suportar múltiplas lojas')

    # add command
    add_parser = subparsers.add_parser('add', help='Adicionar produto para monitorar')
    add_parser.add_argument('url', help='URL do produto (Zaffari ou Carrefour)')
    add_parser.add_argument('target_price', help='Preço alvo (ex: R$80,99 ou 80.99)')

    # list command
    list_parser = subparsers.add_parser('list', help='Listar todos os produtos monitorados')
    list_parser.add_argument('--store', '-s', choices=['zaffari', 'carrefour'],
                            help='Filtrar por loja')

    # check command
    subparsers.add_parser('check', help='Verificar preços e alertas')

    # update command
    subparsers.add_parser('update', help='Atualizar preços de todos os produtos')

    # alerts command
    subparsers.add_parser('alerts', help='Mostrar alertas disparados')

    # history command
    history_parser = subparsers.add_parser('history', help='Mostrar histórico de preços')
    history_parser.add_argument('product_id', type=int, help='ID do produto')
    history_parser.add_argument('--days', type=int, default=30, help='Número de dias (padrão: 30)')

    # detail command
    detail_parser = subparsers.add_parser('detail', help='Mostrar detalhes do produto')
    detail_parser.add_argument('product_id', type=int, help='ID do produto')

    # remove command
    remove_parser = subparsers.add_parser('remove', help='Remover produto do monitoramento')
    remove_parser.add_argument('product_id', type=int, help='ID do produto')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute command
    if args.command == 'init-db':
        init_database()
    elif args.command == 'migrate':
        run_migration()
    elif args.command == 'add':
        add_product(args.url, args.target_price)
    elif args.command == 'list':
        list_products(args.store)
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
