#!/usr/bin/env python3
"""
Scheduler para atualização automática de preços.
Executa às 8:00 da manhã e gera relatório Excel.
Suporta Zaffari e Carrefour.
"""

import schedule
import time
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from services import ProductService, AlertService
from database.models import AlertType, Store


def generate_excel_report(
    products_with_changes: List[Dict[str, Any]],
    products_at_target: List[Dict[str, Any]],
    products_below_std: List[Dict[str, Any]]
) -> str:
    """
    Gera relatório Excel com produtos que tiveram alteração de preço.
    Retorna o caminho do arquivo gerado.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Relatório de Preços"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    target_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # Verde
    std_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")  # Amarelo
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Headers
    headers = [
        "ID", "Loja", "Produto", "Preço Anterior", "Preço Atual", "Variação",
        "Preço Alvo", "Média 30d", "Desvio Padrão", "Alerta"
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    # Dados
    row = 2
    for item in products_with_changes:
        product = item['product']
        prev_price = item.get('previous_price')
        variation = item.get('variation', 0)
        avg_price = item.get('avg_price')
        std_dev = item.get('std_deviation')

        # Determinar tipo de alerta
        alert_type = ""
        row_fill = None

        # Verificar se está no target
        if product.current_price and product.current_price <= product.target_price:
            alert_type = "🎯 ALVO ATINGIDO"
            row_fill = target_fill

        # Verificar se está abaixo do desvio padrão
        if std_dev and avg_price:
            threshold = avg_price - std_dev
            if product.current_price and product.current_price <= threshold:
                if alert_type:
                    alert_type += " | "
                alert_type += "📉 DESVIO PADRÃO"
                if not row_fill:
                    row_fill = std_fill

        # Get store display name
        store_name = product.store.display_name if hasattr(product.store, 'display_name') else str(product.store)

        # Preencher linha
        ws.cell(row=row, column=1, value=product.id).border = border
        ws.cell(row=row, column=2, value=store_name).border = border
        ws.cell(row=row, column=3, value=product.title[:45] if product.title else "").border = border
        ws.cell(row=row, column=4, value=float(prev_price) if prev_price else None).border = border
        ws.cell(row=row, column=5, value=float(product.current_price) if product.current_price else None).border = border
        ws.cell(row=row, column=6, value=f"{variation:+.2f}%").border = border
        ws.cell(row=row, column=7, value=float(product.target_price)).border = border
        ws.cell(row=row, column=8, value=float(avg_price) if avg_price else None).border = border
        ws.cell(row=row, column=9, value=float(std_dev) if std_dev else None).border = border
        ws.cell(row=row, column=10, value=alert_type).border = border

        # Aplicar cor se tem alerta
        if row_fill:
            for col in range(1, 11):
                ws.cell(row=row, column=col).fill = row_fill

        row += 1

    # Ajustar largura das colunas
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 45
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 15
    ws.column_dimensions['J'].width = 30

    # Salvar arquivo
    filename = f"relatorio_precos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(filename)

    return filename


def run_daily_update():
    """Executa atualização diária e gera relatório."""
    print(f"\n{'='*60}")
    print(f"⏰ Atualização diária iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    product_service = ProductService()
    alert_service = AlertService()

    # Guardar preços anteriores
    products = product_service.get_all_products(active_only=True)
    previous_prices = {p.id: p.current_price for p in products}

    # Atualizar preços
    print("\n📦 Atualizando preços...")
    updated = product_service.update_all_prices()
    print(f"✅ {len(updated)} produto(s) atualizado(s)")

    # Identificar produtos com alteração
    products_with_changes = []
    for product in updated:
        prev_price = previous_prices.get(product.id)
        if prev_price and product.current_price and prev_price != product.current_price:
            variation = float((product.current_price - prev_price) / prev_price * 100)
            stats = product_service.get_std_deviation(product.id, 30)
            avg_price = stats[0] if stats else None
            std_dev = stats[1] if stats else None

            products_with_changes.append({
                'product': product,
                'previous_price': prev_price,
                'variation': variation,
                'avg_price': avg_price,
                'std_deviation': std_dev
            })

    # Produtos no alvo
    products_at_target = product_service.get_products_at_target()

    # Produtos abaixo do desvio padrão
    products_below_std = product_service.get_products_below_std_deviation(30)

    # Gerar relatório Excel se houver alterações
    if products_with_changes:
        print(f"\n📊 {len(products_with_changes)} produto(s) com alteração de preço")
        filename = generate_excel_report(
            products_with_changes,
            [{'product': p} for p in products_at_target],
            products_below_std
        )
        print(f"📄 Relatório gerado: {filename}")
    else:
        print("\n📊 Nenhuma alteração de preço detectada")

    # Resumo de alertas
    if products_at_target:
        print(f"\n🎯 {len(products_at_target)} produto(s) no preço alvo!")
        for p in products_at_target:
            store_name = p.store.display_name if hasattr(p.store, 'display_name') else str(p.store)
            print(f"   • [{store_name}] {p.title[:35]}: R$ {p.current_price}")

    if products_below_std:
        print(f"\n📉 {len(products_below_std)} produto(s) abaixo do desvio padrão!")
        for item in products_below_std:
            p = item['product']
            store_name = p.store.display_name if hasattr(p.store, 'display_name') else str(p.store)
            print(f"   • [{store_name}] {p.title[:35]}: R$ {p.current_price} (limite: R$ {item['threshold']})")

    print(f"\n{'='*60}")
    print(f"✅ Atualização concluída: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)


def main():
    """Inicia o scheduler."""
    print("🕐 Scheduler iniciado")
    print("   Atualização programada para 08:00 todos os dias")
    print("   Pressione Ctrl+C para parar\n")

    # Agendar para 8:00
    schedule.every().day.at("08:00").do(run_daily_update)

    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verifica a cada minuto


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        # Executar imediatamente (para testes)
        run_daily_update()
    else:
        main()
