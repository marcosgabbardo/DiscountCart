#!/usr/bin/env python3
"""
Zaffari Price Monitor CLI

A command-line tool to monitor Zaffari product prices and get alerts
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

from tabulate import tabulate

from config import settings
from database import get_db
from database.models import AlertType
from services import ProductService, AlertService
from utils import parse_price, format_currency, truncate_string, validate_zaffari_url


def init_database():
    """Initialize the database schema."""
    print("Inicializando banco de dados...")
    db = get_db()
    db.init_database()
    print("Banco de dados inicializado com sucesso!")


def add_product(url: str, target_price_str: str):
    """Add a new product to monitor."""
    # Validate URL
    if not validate_zaffari_url(url):
        print(f"Erro: '{url}' não parece ser uma URL válida do Zaffari.")
        print("Use uma URL no formato: https://www.zaffari.com.br/produto-123/p")
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

    print(f"Adicionando produto com preço alvo {format_currency(target_price)}...")
    print("Buscando informações do produto no Zaffari...")

    try:
        service = ProductService()
        product = service.add_product(url, target_price)

        print("\n✅ Produto adicionado com sucesso!")
        print("-" * 50)
        print(f"ID: {product.id}")
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


def list_products():
    """List all monitored products."""
    try:
        service = ProductService()
        products = service.get_all_products()

        if not products:
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

            table_data.append([
                p.id,
                truncate_string(p.title, 40),
                format_currency(p.current_price),
                format_currency(p.target_price),
                diff,
                status,
            ])

        headers = ["ID", "Produto", "Atual", "Alvo", "Diferença", "Status"]
        print(f"\n📦 Produtos Monitorados ({len(products)})")
        print("-" * 80)
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 80)

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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Zaffari Price Monitor - Monitore preços e receba alertas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s add "https://www.zaffari.com.br/produto-123/p" "R$80,99"
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

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')

    # init-db command
    subparsers.add_parser('init-db', help='Inicializar banco de dados')

    # add command
    add_parser = subparsers.add_parser('add', help='Adicionar produto para monitorar')
    add_parser.add_argument('url', help='URL do produto no Zaffari')
    add_parser.add_argument('target_price', help='Preço alvo (ex: R$80,99 ou 80.99)')

    # list command
    subparsers.add_parser('list', help='Listar todos os produtos monitorados')

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
