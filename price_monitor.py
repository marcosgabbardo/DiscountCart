#!/usr/bin/env python3
"""
DiscountCart Price Monitor CLI

A command-line tool to monitor product prices from Zaffari and Carrefour
and get alerts based on standard deviation analysis.

Usage:
    python price_monitor.py add <url>
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
from services import ProductService, AlertService, CategoryService
from utils import parse_price, format_currency, truncate_string, validate_product_url


def init_database():
    """Initialize the database schema."""
    print("Inicializando banco de dados...")
    db = get_db()
    db.init_database()
    print("Banco de dados inicializado com sucesso!")


def add_product(url: str):
    """Add a new product to monitor."""
    # Validate URL
    is_valid, store_name = validate_product_url(url)
    if not is_valid:
        print(f"Erro: '{url}' não parece ser uma URL válida.")
        print("URLs suportadas:")
        print("  - Zaffari: https://www.zaffari.com.br/produto-123/p")
        print("  - Carrefour: https://mercado.carrefour.com.br/produto-123/p")
        sys.exit(1)

    store_display = Store(store_name).display_name
    print(f"Adicionando produto para monitoramento...")
    print(f"Buscando informações do produto no {store_display}...")

    try:
        service = ProductService()
        product = service.add_product(url)

        print("\n✅ Produto adicionado com sucesso!")
        print("-" * 50)
        print(f"ID: {product.id}")
        print(f"Loja: {product.store.display_name}")
        print(f"Título: {product.title}")
        print(f"SKU: {product.asin}")
        print(f"Categoria: {product.category or 'Não categorizado'}")
        print(f"Preço Atual: {format_currency(product.current_price)}")

        print("\n📢 Produto será monitorado para alertas de desvio padrão.")
        print("   Use 'check' para ver alertas quando o preço estiver abaixo da média.")

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
            print("Adicione um produto com: python price_monitor.py add <url>")
            return

        # Prepare table data
        table_data = []
        for p in products:
            # Store emoji/abbreviation
            store_abbr = "🟢" if p.store == Store.ZAFFARI else "🔵"

            # Price vs lowest
            status = ""
            if p.current_price and p.lowest_price:
                if p.current_price <= p.lowest_price:
                    status = "📉 Mínimo"
                else:
                    diff = ((p.current_price - p.lowest_price) / p.lowest_price) * 100
                    status = f"+{diff:.1f}%"

            table_data.append([
                p.id,
                store_abbr,
                truncate_string(p.title, 35),
                format_currency(p.current_price),
                format_currency(p.lowest_price),
                format_currency(p.highest_price),
                status,
            ])

        headers = ["ID", "Loja", "Produto", "Atual", "Mínimo", "Máximo", "Status"]
        title = f"📦 Produtos Monitorados ({len(products)})"
        if store:
            title += f" - {store.display_name}"
        print(f"\n{title}")
        print("Legenda: 🟢 Zaffari | 🔵 Carrefour")
        print("-" * 100)
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 100)

    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        sys.exit(1)


def check_prices():
    """Check current prices and show standard deviation alerts."""
    print("Verificando preços e alertas de desvio padrão...")

    try:
        alert_service = AlertService()

        # Print full summary
        alert_service.print_std_deviation_summary()

        # Get best deals (2 std dev)
        best_deals = alert_service.get_best_deals()
        if best_deals:
            print(f"\n🎯 {len(best_deals)} oferta(s) excepcional(is) encontrada(s)!")

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

        # Show summary
        check_prices()

    except Exception as e:
        print(f"Erro ao atualizar preços: {e}")
        sys.exit(1)


def show_alerts():
    """Show all current standard deviation alerts."""
    try:
        alert_service = AlertService()
        alert_service.print_std_deviation_summary()

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

        # Get std deviation analysis
        analysis = service.get_product_std_analysis(product_id)
        if analysis:
            print(f"\n📉 Análise de Desvio Padrão:")
            for period in [30, 90, 180]:
                stats = analysis['periods'].get(period)
                if stats:
                    print(f"\n   {period} dias:")
                    print(f"      Média: {format_currency(stats['avg_price'])}")
                    print(f"      Desvio Padrão: {format_currency(stats['std_deviation'])}")
                    print(f"      Limite 1 DP: {format_currency(stats['threshold_1_std'])}")
                    print(f"      Limite 2 DP: {format_currency(stats['threshold_2_std'])}")
                    if stats['is_below_2_std']:
                        print(f"      ⚡ ABAIXO DE 2 DESVIOS PADRÃO!")
                    elif stats['is_below_1_std']:
                        print(f"      ✅ Abaixo de 1 desvio padrão")

        # Show recent history
        print(f"\nPreços recentes:")
        table_data = []
        for h in history[:15]:  # Last 15 records
            table_data.append([
                h.recorded_at.strftime("%Y-%m-%d %H:%M"),
                format_currency(h.price),
            ])

        headers = ["Data", "Preço"]
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
        avg_90 = service.get_average_price(product_id, 90)
        avg_180 = service.get_average_price(product_id, 180)

        print("\n" + "=" * 60)
        print(f"📦 {product.title}")
        print("=" * 60)
        print(f"ID:           {product.id}")
        print(f"Loja:         {product.store.display_name}")
        print(f"SKU:          {product.asin}")
        print(f"Categoria:    {product.category or 'Não categorizado'}")
        print(f"URL:          {product.url}")
        print(f"\n💰 Preços:")
        print(f"   Atual:     {format_currency(product.current_price)}")
        print(f"   Mínimo:    {format_currency(product.lowest_price)}")
        print(f"   Máximo:    {format_currency(product.highest_price)}")
        print(f"\n📊 Médias:")
        print(f"   Média (7d):   {format_currency(avg_7)}")
        print(f"   Média (30d):  {format_currency(avg_30)}")
        print(f"   Média (90d):  {format_currency(avg_90)}")
        print(f"   Média (180d): {format_currency(avg_180)}")

        # Get std deviation analysis
        analysis = service.get_product_std_analysis(product_id)
        if analysis:
            print(f"\n📉 Análise de Desvio Padrão:")
            for period in [30, 90, 180]:
                stats = analysis['periods'].get(period)
                if stats:
                    status = ""
                    if stats['is_below_2_std']:
                        status = " 🔥 EXCEPCIONAL!"
                    elif stats['is_below_1_std']:
                        status = " ✅ Bom preço"

                    print(f"   {period}d: Limite 1DP={format_currency(stats['threshold_1_std'])} | 2DP={format_currency(stats['threshold_2_std'])}{status}")

        print(f"\n📅 Criado: {product.created_at}")
        print(f"📅 Atualizado: {product.updated_at}")
        print("=" * 60)

    except Exception as e:
        print(f"Erro ao mostrar produto: {e}")
        sys.exit(1)


def list_categories():
    """List all categories with product counts and price ranges."""
    try:
        service = CategoryService()
        categories = service.get_all_categories()

        if not categories:
            print("Nenhuma categoria encontrada.")
            print("Execute 'categorize' para categorizar produtos existentes.")
            return

        print(f"\n📁 Categorias de Produtos ({len(categories)})")
        print("-" * 80)

        table_data = []
        for cat in categories:
            table_data.append([
                cat['category'],
                cat['product_count'],
                format_currency(Decimal(str(cat['min_price']))) if cat['min_price'] else '-',
                format_currency(Decimal(str(cat['max_price']))) if cat['max_price'] else '-',
                format_currency(Decimal(str(cat['avg_price']))) if cat['avg_price'] else '-',
            ])

        headers = ["Categoria", "Qtd", "Menor Preço", "Maior Preço", "Média"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 80)

    except Exception as e:
        print(f"Erro ao listar categorias: {e}")
        sys.exit(1)


def show_category(category_name: str):
    """Show all products in a specific category."""
    try:
        service = CategoryService()
        products = service.get_products_by_category(category_name)

        if not products:
            print(f"Nenhum produto encontrado na categoria '{category_name}'.")
            print("\nCategorias disponíveis:")
            for cat in service.get_available_categories():
                print(f"  - {cat}")
            return

        print(f"\n📁 Categoria: {category_name} ({len(products)} produtos)")
        print("-" * 90)

        table_data = []
        for p in products:
            store_abbr = "🟢" if p['store'] == 'zaffari' else "🔵"
            table_data.append([
                p['id'],
                store_abbr,
                truncate_string(p['title'], 40),
                format_currency(Decimal(str(p['current_price']))) if p['current_price'] else '-',
                format_currency(Decimal(str(p['lowest_price']))) if p['lowest_price'] else '-',
            ])

        headers = ["ID", "Loja", "Produto", "Preço Atual", "Menor Preço"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 90)

        # Show cheapest
        cheapest = service.get_cheapest_by_category(category_name)
        if cheapest:
            store_name = Store(cheapest['store']).display_name
            print(f"\n💰 Mais barato: {truncate_string(cheapest['title'], 50)}")
            print(f"   Loja: {store_name}")
            print(f"   Preço: {format_currency(Decimal(str(cheapest['current_price'])))}")

    except Exception as e:
        print(f"Erro ao mostrar categoria: {e}")
        sys.exit(1)


def compare_category(category_name: str):
    """Compare prices of products in a category across stores."""
    try:
        service = CategoryService()
        products = service.compare_prices_by_category(category_name)

        if not products:
            print(f"Nenhum produto encontrado na categoria '{category_name}'.")
            return

        print(f"\n📊 Comparação de Preços: {category_name}")
        print("-" * 100)

        table_data = []
        for i, p in enumerate(products):
            store_abbr = "🟢" if p['store'] == 'zaffari' else "🔵"
            rank = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))

            table_data.append([
                rank,
                store_abbr,
                truncate_string(p['title'], 35),
                format_currency(Decimal(str(p['current_price']))),
                format_currency(Decimal(str(p['lowest_price']))) if p['lowest_price'] else '-',
                format_currency(Decimal(str(p['avg_30d']))) if p['avg_30d'] else '-',
            ])

        headers = ["Rank", "Loja", "Produto", "Atual", "Mínimo", "Média 30d"]
        print("Legenda: 🟢 Zaffari | 🔵 Carrefour")
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 100)

        if len(products) >= 2:
            diff = Decimal(str(products[-1]['current_price'])) - Decimal(str(products[0]['current_price']))
            if diff > 0:
                print(f"\n💡 Economia potencial escolhendo o mais barato: {format_currency(diff)}")

    except Exception as e:
        print(f"Erro ao comparar categoria: {e}")
        sys.exit(1)


def categorize_products(recategorize_all: bool = False):
    """Categorize products without a category, or recategorize all."""
    if recategorize_all:
        print("Recategorizando TODOS os produtos...")
        print("Isso irá atualizar as categorias de todos os produtos.\n")
    else:
        print("Categorizando produtos sem categoria...")
    print("Isso pode demorar um pouco.\n")

    try:
        service = CategoryService()

        if recategorize_all:
            categorized = service.recategorize_all()
        else:
            categorized = service.categorize_all_uncategorized()

        if not categorized:
            print("Todos os produtos já estão categorizados!")
            return

        print(f"\n✅ {len(categorized)} produto(s) categorizado(s)")

        # Show summary by category
        categories = {}
        for item in categorized:
            cat = item['category']
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        print("\nResumo por categoria:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} produto(s)")

    except Exception as e:
        print(f"Erro ao categorizar produtos: {e}")
        sys.exit(1)


def search_category(search_term: str):
    """Search for categories containing a term."""
    try:
        service = CategoryService()
        categories = service.search_categories(search_term)

        if not categories:
            print(f"Nenhuma categoria encontrada com '{search_term}'.")
            return

        print(f"\n🔍 Categorias com '{search_term}' ({len(categories)} encontradas)")
        print("-" * 70)

        table_data = []
        for cat in categories:
            table_data.append([
                cat['category'],
                cat['product_count'],
                format_currency(Decimal(str(cat['min_price']))) if cat['min_price'] else '-',
                format_currency(Decimal(str(cat['max_price']))) if cat['max_price'] else '-',
            ])

        headers = ["Categoria", "Qtd", "Menor Preço", "Maior Preço"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("-" * 70)

    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        sys.exit(1)


def run_migration():
    """Run database migrations."""
    print("Executando migrações do banco de dados...")
    db = get_db()

    try:
        # Migration 1: Add store column
        check_store_query = """
            SELECT COUNT(*) as cnt FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'products'
            AND column_name = 'store'
        """
        result = db.execute_query(check_store_query)
        store_exists = result[0]['cnt'] > 0 if result else False

        if not store_exists:
            print("Adicionando coluna 'store' à tabela products...")
            add_store_query = """
                ALTER TABLE products
                ADD COLUMN store ENUM('zaffari', 'carrefour') NOT NULL DEFAULT 'zaffari'
                AFTER image_url
            """
            db.execute_query(add_store_query, fetch=False)
            print("✅ Coluna 'store' adicionada!")
        else:
            print("✅ Coluna 'store' já existe.")

        # Migration 2: Add category column
        check_category_query = """
            SELECT COUNT(*) as cnt FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'products'
            AND column_name = 'category'
        """
        result = db.execute_query(check_category_query)
        category_exists = result[0]['cnt'] > 0 if result else False

        if not category_exists:
            print("Adicionando coluna 'category' à tabela products...")
            add_category_query = """
                ALTER TABLE products
                ADD COLUMN category VARCHAR(100) NULL
                AFTER store
            """
            db.execute_query(add_category_query, fetch=False)
            print("✅ Coluna 'category' adicionada!")

            # Add index for category
            print("Criando índice para categoria...")
            try:
                db.execute_query("CREATE INDEX idx_category ON products(category)", fetch=False)
                print("✅ Índice criado!")
            except Exception:
                print("✅ Índice já existe ou não pôde ser criado.")
        else:
            print("✅ Coluna 'category' já existe.")

        # Migration 3: Remove target_price column if exists (make it nullable first)
        print("Verificando coluna target_price...")
        check_target_query = """
            SELECT COUNT(*) as cnt FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'products'
            AND column_name = 'target_price'
        """
        result = db.execute_query(check_target_query)
        target_exists = result[0]['cnt'] > 0 if result else False

        if target_exists:
            print("Tornando coluna 'target_price' opcional (legacy)...")
            try:
                db.execute_query("ALTER TABLE products MODIFY COLUMN target_price DECIMAL(10, 2) NULL", fetch=False)
                print("✅ Coluna 'target_price' agora é opcional.")
            except Exception as e:
                print(f"Aviso: Não foi possível modificar target_price: {e}")

        # Update the view
        print("Atualizando view product_summary...")
        view_query = """
            CREATE OR REPLACE VIEW product_summary AS
            SELECT
                p.id,
                p.asin,
                p.title,
                p.store,
                p.category,
                p.current_price,
                p.lowest_price,
                p.highest_price,
                ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)), 2) AS avg_price_7days,
                ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)), 2) AS avg_price_30days,
                ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)), 2) AS avg_price_90days,
                ROUND((SELECT AVG(ph.price) FROM price_history ph WHERE ph.product_id = p.id AND ph.recorded_at >= DATE_SUB(NOW(), INTERVAL 180 DAY)), 2) AS avg_price_180days,
                (SELECT COUNT(*) FROM price_history ph WHERE ph.product_id = p.id) AS total_price_records,
                CASE
                    WHEN p.current_price <= p.lowest_price THEN 'AT_LOWEST'
                    ELSE 'MONITORING'
                END AS status,
                p.is_active,
                p.updated_at
            FROM products p
            WHERE p.is_active = TRUE
        """
        db.execute_query(view_query, fetch=False)

        # Update alerts table to support new alert types
        print("Atualizando tabela de alertas...")
        try:
            update_alerts_query = """
                ALTER TABLE alerts
                MODIFY COLUMN alert_type ENUM(
                    'target_reached', 'price_drop', 'below_average',
                    'std_dev_1_30d', 'std_dev_1_90d', 'std_dev_1_180d',
                    'std_dev_2_30d', 'std_dev_2_90d', 'std_dev_2_180d'
                ) NOT NULL
            """
            db.execute_query(update_alerts_query, fetch=False)
            print("✅ Tabela de alertas atualizada!")
        except Exception as e:
            print(f"Aviso: {e}")

        print("\n✅ Migrações executadas com sucesso!")
        print("\nSistema atualizado para alertas por desvio padrão:")
        print("  - 1 desvio padrão: Boas ofertas")
        print("  - 2 desvios padrão: Ofertas excepcionais")
        print("  - Períodos: 30, 90 e 180 dias")

    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DiscountCart Price Monitor - Monitore preços do Zaffari e Carrefour",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s add "https://www.zaffari.com.br/produto-123/p"
  %(prog)s add "https://mercado.carrefour.com.br/produto-456/p"
  %(prog)s list
  %(prog)s list --store zaffari
  %(prog)s check
  %(prog)s update
  %(prog)s alerts
  %(prog)s history 1
  %(prog)s detail 1
  %(prog)s remove 1
  %(prog)s categories
  %(prog)s category "Leite UHT Integral"
  %(prog)s compare "Coração de Frango"
  %(prog)s search-category leite
  %(prog)s categorize
  %(prog)s categorize --all
  %(prog)s init-db
  %(prog)s migrate
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')

    # init-db command
    subparsers.add_parser('init-db', help='Inicializar banco de dados')

    # migrate command
    subparsers.add_parser('migrate', help='Executar migração para suportar alertas de desvio padrão')

    # add command
    add_parser = subparsers.add_parser('add', help='Adicionar produto para monitorar')
    add_parser.add_argument('url', help='URL do produto (Zaffari ou Carrefour)')

    # list command
    list_parser = subparsers.add_parser('list', help='Listar todos os produtos monitorados')
    list_parser.add_argument('--store', '-s', choices=['zaffari', 'carrefour'],
                            help='Filtrar por loja')

    # check command
    subparsers.add_parser('check', help='Verificar preços e mostrar alertas de desvio padrão')

    # update command
    subparsers.add_parser('update', help='Atualizar preços de todos os produtos')

    # alerts command
    subparsers.add_parser('alerts', help='Mostrar alertas de desvio padrão')

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

    # categories command
    subparsers.add_parser('categories', help='Listar todas as categorias de produtos')

    # category command
    category_parser = subparsers.add_parser('category', help='Mostrar produtos de uma categoria')
    category_parser.add_argument('category_name', nargs='+', help='Nome da categoria (ex: Leite UHT Integral)')

    # compare command
    compare_parser = subparsers.add_parser('compare', help='Comparar preços por categoria')
    compare_parser.add_argument('category_name', nargs='+', help='Nome da categoria para comparar')

    # categorize command
    categorize_parser = subparsers.add_parser('categorize', help='Categorizar produtos sem categoria usando IA')
    categorize_parser.add_argument('--all', '-a', action='store_true',
                                   help='Recategorizar TODOS os produtos (não apenas os sem categoria)')

    # search-category command
    search_cat_parser = subparsers.add_parser('search-category', help='Buscar categorias por termo')
    search_cat_parser.add_argument('search_term', help='Termo para buscar nas categorias')

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
        add_product(args.url)
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
    elif args.command == 'categories':
        list_categories()
    elif args.command == 'category':
        show_category(' '.join(args.category_name))
    elif args.command == 'compare':
        compare_category(' '.join(args.category_name))
    elif args.command == 'categorize':
        categorize_products(recategorize_all=args.all)
    elif args.command == 'search-category':
        search_category(args.search_term)


if __name__ == '__main__':
    main()
