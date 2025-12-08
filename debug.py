#!/usr/bin/env python3
"""
Debug do scraper Zaffari.
Uso: python debug.py <url>
"""

import sys
from bs4 import BeautifulSoup
from scraper import ZaffariScraper


def debug(url: str):
    print(f"🔍 Debug: {url}\n")

    scraper = ZaffariScraper()

    # Validar URL
    if not scraper.validate_url(url):
        print("❌ URL inválida")
        return

    # Buscar página
    print("Buscando página...")
    try:
        html = scraper._fetch_page(url)
    except Exception as e:
        print(f"❌ Erro ao buscar página: {e}")
        return

    soup = BeautifulSoup(html, 'html.parser')

    # Debug título
    print("\n📦 TÍTULO:")
    title_elem = soup.select_one('h1')
    if title_elem:
        print(f"   h1: {title_elem.get_text(strip=True)[:80]}")

    # Debug preço - seletor específico
    print("\n💰 PREÇO (seletor Zaffari):")

    # Parent
    parent = soup.select_one('.zaffarilab-zaffari-produto-1-x-ProductPriceSellingPrice')
    print(f"   Parent encontrado: {parent is not None}")

    # Child (preço)
    price_elem = soup.select_one('.zaffarilab-zaffari-produto-1-x-ProductPriceSellingPriceValue')
    print(f"   PriceValue encontrado: {price_elem is not None}")

    if price_elem:
        price_text = price_elem.get_text(strip=True)
        print(f"   Texto do preço: '{price_text}'")
        parsed = scraper._parse_price(price_text)
        print(f"   Preço parseado: {parsed}")

    # Seletor completo
    full_selector = soup.select_one('.zaffarilab-zaffari-produto-1-x-ProductPriceSellingPrice .zaffarilab-zaffari-produto-1-x-ProductPriceSellingPriceValue')
    print(f"   Seletor completo encontrado: {full_selector is not None}")

    # Mostrar todas as classes que contêm "Price" no nome
    print("\n🔎 ELEMENTOS COM 'Price' NA CLASSE:")
    for elem in soup.find_all(class_=True):
        classes = elem.get('class', [])
        for cls in classes:
            if 'price' in cls.lower():
                text = elem.get_text(strip=True)[:50]
                print(f"   .{cls}: '{text}'")
                break


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python debug.py <url>")
        print("Exemplo: python debug.py 'https://www.zaffari.com.br/presunto-cozido-fatiado-sadia-180g-1108724/p'")
        sys.exit(1)

    debug(sys.argv[1])
