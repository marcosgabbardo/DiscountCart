#!/usr/bin/env python3
"""Debug - simula: python price_monitor.py add <url> <preco>"""

from price_monitor import add_product

url = "https://www.zaffari.com.br/presunto-cozido-fatiado-sadia-180g-1108724/p"
target_price = "6,55"

add_product(url, target_price)
