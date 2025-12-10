#!/usr/bin/env python3
"""Debug script to find where price values come from."""

import re
import requests
from bs4 import BeautifulSoup

URL = "https://mercado.carrefour.com.br/agua-de-coco-integral-dikoko-caixa-1l-3006379/p"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}

print("Buscando página...")
response = requests.get(URL, headers=headers, timeout=30)
html = response.text

print(f"\nStatus: {response.status_code}")
print(f"Tamanho do HTML: {len(html)} caracteres")

# Search for 11.19 or 11,19 in HTML
print("\n" + "="*60)
print("BUSCANDO '11.19' ou '11,19' no HTML:")
print("="*60)

# Find all occurrences
patterns = ['11.19', '11,19', '1119']
for pattern in patterns:
    if pattern in html:
        # Find context around the match
        idx = html.find(pattern)
        start = max(0, idx - 150)
        end = min(len(html), idx + 150)
        context = html[start:end]
        print(f"\n>>> Encontrado '{pattern}' na posição {idx}:")
        print("-" * 40)
        print(context)
        print("-" * 40)
    else:
        print(f"\n'{pattern}' NÃO encontrado no HTML")

# Search for 10.59 or 10,59
print("\n" + "="*60)
print("BUSCANDO '10.59' ou '10,59' no HTML:")
print("="*60)

patterns = ['10.59', '10,59', '1059']
for pattern in patterns:
    if pattern in html:
        idx = html.find(pattern)
        start = max(0, idx - 150)
        end = min(len(html), idx + 150)
        context = html[start:end]
        print(f"\n>>> Encontrado '{pattern}' na posição {idx}:")
        print("-" * 40)
        print(context)
        print("-" * 40)
    else:
        print(f"\n'{pattern}' NÃO encontrado no HTML")

# Search for text-blue-royal spans
print("\n" + "="*60)
print("BUSCANDO spans com 'text-blue-royal':")
print("="*60)

soup = BeautifulSoup(html, 'html.parser')
blue_spans = soup.find_all('span', class_=lambda x: x and 'text-blue-royal' in ' '.join(x) if isinstance(x, list) else 'text-blue-royal' in str(x))

for i, span in enumerate(blue_spans):
    classes = span.get('class', [])
    text = span.get_text(strip=True)
    print(f"\n{i+1}. Classes: {classes}")
    print(f"   Texto: {text}")

# Search for "Adicionar ao Carrinho" button
print("\n" + "="*60)
print("BUSCANDO botão 'Adicionar ao Carrinho':")
print("="*60)

for button in soup.find_all('button'):
    text = button.get_text(strip=True).lower()
    if 'adicionar' in text or 'carrinho' in text:
        print(f"\nBotão encontrado: {button.get_text(strip=True)}")
        print(f"Classes: {button.get('class', [])}")

# Save full HTML for inspection
with open('/home/user/DiscountCart/debug_html.html', 'w') as f:
    f.write(html)
print("\n\nHTML completo salvo em: debug_html.html")
