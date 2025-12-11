# DiscountCart - Price Monitor

A price monitoring tool for **Zaffari** and **Carrefour** supermarket products (Brazil). Get terminal alerts when prices reach your target, compare prices between stores, and find the cheapest products by category using AI-powered categorization.

## Features

- **Multi-Store Support**: Monitor products from Zaffari and Carrefour
- **Add Products**: Monitor any product via URL (auto-detects store)
- **Set Target Price**: Define the price you want to pay
- **AI-Powered Categorization**: Automatic product categorization using Anthropic Claude API
- **Price Comparison by Category**: Compare prices of similar products across stores (e.g., all "Leite UHT Integral")
- **Price History**: Track price variations over time
- **Smart Alerts**: Get notified when:
  - Price reaches your target
  - Price drops below 7/30 day average
  - Price falls 1 standard deviation below 30-day average
  - New lowest price detected
- **Statistics**: View average, minimum, and maximum prices
- **Daily Scheduler**: Automatic updates at 8:00 AM with Excel reports
- **Excel Reports**: Generated reports with price changes, store info, and alert status
- **Filter by Store**: List products from a specific store

## Product Categorization

The AI categorization system creates **granular categories** that represent the generic product type (without brand), enabling direct price comparison between equivalent products from different stores/brands.

### Examples of categorization:

| Product Title | Category |
|--------------|----------|
| Leite Italac UHT Integral 1L | Leite UHT Integral |
| Leite Piracanjuba Desnatado 1L | Leite UHT Desnatado |
| Coração de Frango Sadia 1kg | Coração de Frango |
| Peito de Frango Seara | Peito de Frango |
| Requeijão Vigor Cremoso 200g | Requeijão |
| YoPro Morango 250ml | Bebida Láctea |
| Kefir Natural Keffy 170g | Kefir |
| Água de Coco Sococo 1L | Água de Coco |
| Castanha de Caju Torrada 100g | Castanha de Caju |
| Picanha Bovina Resfriada kg | Picanha |

## Supported Stores

| Store | Website | URL Format |
|-------|---------|------------|
| Zaffari | zaffari.com.br | `https://www.zaffari.com.br/produto-SKU/p` |
| Carrefour | mercado.carrefour.com.br | `https://mercado.carrefour.com.br/produto-SKU/p` |

## Requirements

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- Anthropic API Key (for product categorization)

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/DiscountCart.git
cd DiscountCart
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your database credentials and Anthropic API key
```

5. **Initialize the database**:
```bash
python price_monitor.py init-db
```

6. **If upgrading from a previous version**:
```bash
python price_monitor.py migrate
```

## Configuration

Edit the `.env` file with your settings:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=amazon_price_monitor

# Scraping Configuration
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5
REQUEST_TIMEOUT=30

# Alert Configuration
CHECK_INTERVAL_MINUTES=60
PRICE_DROP_THRESHOLD_PERCENT=10

# Regional Configuration (for Carrefour pricing)
CEP=90420-010

# Anthropic API Configuration (for product categorization)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Getting an Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key to your `.env` file

## Usage

### Add a Product to Monitor

**Zaffari:**
```bash
python price_monitor.py add "https://www.zaffari.com.br/produto-123/p" "R$80,99"
```

**Carrefour:**
```bash
python price_monitor.py add "https://mercado.carrefour.com.br/produto-456/p" "R$75,00"
```

The store is automatically detected from the URL, and the product is automatically categorized using AI.

Output:
```
✅ Produto adicionado com sucesso!
--------------------------------------------------
ID: 5
Loja: Carrefour
Título: Leite Integral Piracanjuba 1L
SKU: 12345
Categoria: Leite UHT Integral
Preço Atual: R$ 5,49
Preço Alvo: R$ 5,00
```

Accepted price formats:
- `R$80,99`
- `80,99`
- `80.99`
- `R$ 1.234,56`

### List All Monitored Products

```bash
python price_monitor.py list
```

Output:
```
📦 Produtos Monitorados (4)
Legenda: 🟢 Zaffari | 🔵 Carrefour
------------------------------------------------------------------------------------------
ID   Loja   Produto                              Atual          Alvo           Diferença   Status
1    🟢     Presunto Cozido Fatiado Sadia...     R$ 6,99        R$ 6,55        R$ 0,44     👀
2    🟢     Queijo Mussarela President...        R$ 12,90       R$ 10,99       R$ 1,91     👀
3    🔵     Arroz Branco Carrefour 5kg           R$ 24,90       R$ 22,00       R$ 2,90     👀
4    🔵     Leite Integral Piracanjuba...        R$ 5,49        R$ 5,49        R$ 0,00     ✅
```

### Filter by Store

```bash
# Only Zaffari products
python price_monitor.py list --store zaffari

# Only Carrefour products
python price_monitor.py list --store carrefour
```

---

## Category Commands

### List All Categories

View all product categories with statistics:

```bash
python price_monitor.py categories
```

Output:
```
📁 Categorias de Produtos (12)
--------------------------------------------------------------------------------
Categoria              Qtd    Menor Preço    Maior Preço    Média
Arroz Branco           3      R$ 22,90       R$ 28,50       R$ 25,30
Coração de Frango      2      R$ 12,99       R$ 15,90       R$ 14,45
Leite UHT Integral     4      R$ 4,99        R$ 6,29        R$ 5,50
Requeijão              2      R$ 8,49        R$ 9,99        R$ 9,24
...
--------------------------------------------------------------------------------
```

### View Products in a Category

```bash
python price_monitor.py category Leite UHT Integral
```

Output:
```
📁 Categoria: Leite UHT Integral (4 produtos)
------------------------------------------------------------------------------------------
ID   Loja   Produto                                     Preço Atual    Menor Preço
12   🔵     Leite Integral Piracanjuba 1L               R$ 4,99        R$ 4,79
5    🟢     Leite Italac Integral UHT 1L                R$ 5,29        R$ 5,09
8    🔵     Leite Integral Parmalat 1L                  R$ 5,49        R$ 5,29
3    🟢     Leite Integral Elegê 1L                     R$ 6,29        R$ 5,99
------------------------------------------------------------------------------------------

💰 Mais barato: Leite Integral Piracanjuba 1L
   Loja: Carrefour
   Preço: R$ 4,99
```

### Compare Prices by Category

Compare all products in a category, ranked by price:

```bash
python price_monitor.py compare Coração de Frango
```

Output:
```
📊 Comparação de Preços: Coração de Frango
----------------------------------------------------------------------------------------------------
Legenda: 🟢 Zaffari | 🔵 Carrefour
Rank   Loja   Produto                              Atual          Mínimo         Média 30d
🥇     🔵     Coração de Frango Sadia 1kg          R$ 12,99       R$ 11,90       R$ 13,50
🥈     🟢     Coração de Frango Perdigão 1kg       R$ 14,49       R$ 13,99       R$ 14,80
🥉     🔵     Coração de Frango Aurora 1kg         R$ 15,90       R$ 14,50       R$ 15,20
----------------------------------------------------------------------------------------------------

💡 Economia potencial escolhendo o mais barato: R$ 2,91
```

### Search Categories

Find categories by keyword:

```bash
python price_monitor.py search-category leite
```

Output:
```
🔍 Categorias com 'leite' (3 encontradas)
----------------------------------------------------------------------
Categoria              Qtd    Menor Preço    Maior Preço
Leite UHT Integral     4      R$ 4,99        R$ 6,29
Leite UHT Desnatado    2      R$ 5,19        R$ 5,89
Leite Condensado       3      R$ 6,49        R$ 8,99
----------------------------------------------------------------------
```

### Categorize Products

**Categorize only uncategorized products:**
```bash
python price_monitor.py categorize
```

**Recategorize ALL products** (useful after updating categorization logic):
```bash
python price_monitor.py categorize --all
```

Output:
```
Recategorizando TODOS os produtos...
Isso irá atualizar as categorias de todos os produtos.

[1/15] Categorizando: Leite Italac UHT Integral 1L...
  -> Categoria: Leite UHT Integral
[2/15] Categorizando: Coração de Frango Sadia Congelado 1kg...
  -> Categoria: Coração de Frango
...

✅ 15 produto(s) categorizado(s)

Resumo por categoria:
  Arroz Branco: 2 produto(s)
  Coração de Frango: 3 produto(s)
  Leite UHT Integral: 4 produto(s)
  ...
```

---

## Other Commands

### Check Prices and Alerts

```bash
python price_monitor.py check
```

### Update All Prices

```bash
python price_monitor.py update
```

Fetches current prices from all stores for all monitored products.

### View Price History

```bash
python price_monitor.py history 1 --days 30
```

### View Product Details

```bash
python price_monitor.py detail 1
```

Output includes category:
```
============================================================
📦 Arroz Branco Tipo 1 Carrefour 5kg
============================================================
ID:           3
Loja:         Carrefour
SKU:          3043
Categoria:    Arroz Branco
URL:          https://mercado.carrefour.com.br/arroz-branco-tipo-1-carrefour-5-kg-3043/p

💰 Preços:
   Atual:     R$ 24,90
   Alvo:      R$ 22,00
   Mínimo:    R$ 23,50
   Máximo:    R$ 26,90
   Média (7d):  R$ 24,50
   Média (30d): R$ 24,80
...
```

### View Triggered Alerts

```bash
python price_monitor.py alerts
```

### Remove a Product

```bash
python price_monitor.py remove 1
```

### Run Database Migration

If you're upgrading from a previous version:

```bash
python price_monitor.py migrate
```

This adds the `store` and `category` columns to existing products.

## Scheduler

### Run the Daily Scheduler

The scheduler runs price updates daily at 8:00 AM and generates Excel reports:

```bash
python scheduler.py
```

### Run Update Immediately (for testing)

```bash
python scheduler.py --now
```

This will:
1. Update all product prices (from both stores)
2. Check for products at target price
3. Check for products below standard deviation threshold
4. Generate an Excel report with all price changes and alerts

### Using Cron (Linux/Mac)

Add to crontab for scheduled execution:

```bash
crontab -e
```

Add:
```
0 8 * * * cd /path/to/DiscountCart && /path/to/venv/bin/python scheduler.py --now >> /var/log/price_monitor.log 2>&1
```

### Using Task Scheduler (Windows)

Create a scheduled task to run:
```
python C:\path\to\DiscountCart\scheduler.py --now
```

## Database Schema

The application uses 3 main tables:

- **products**: Monitored products with URLs, store, category, and target prices
- **price_history**: Historical price records
- **alerts**: Alert configurations and status

Key fields in `products`:
- `store`: ENUM('zaffari', 'carrefour') - identifies the source store
- `category`: VARCHAR(100) - AI-assigned product category
- `asin`: Product SKU (unique per store)

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `init-db` | Initialize database schema |
| `migrate` | Run migration for multi-store and category support |
| `add URL PRICE` | Add product to monitor (auto-categorizes) |
| `list [--store]` | List all products (optionally filtered by store) |
| `check` | Check prices and show alerts |
| `update` | Update all product prices |
| `alerts` | Show triggered alerts |
| `history ID [--days]` | Show price history |
| `detail ID` | Show product details with category |
| `remove ID` | Remove product from monitoring |
| `categories` | List all categories with statistics |
| `category NAME` | Show products in a specific category |
| `compare NAME` | Compare prices by category across stores |
| `search-category TERM` | Search categories by keyword |
| `categorize [--all]` | Categorize products using AI |

## Alert Types

| Alert Type | Description |
|------------|-------------|
| `TARGET_REACHED` | Price reached or fell below target |
| `PRICE_DROP` | Significant price drop detected |
| `BELOW_AVERAGE` | Price below 7-day average |
| `STD_DEVIATION` | Price 1 std deviation below 30-day average |

## Excel Reports

Generated reports include:
- Product ID and store
- Product name
- Previous and current price
- Price variation percentage
- Target price
- 30-day average and standard deviation
- Alert indicators (Target reached, Std deviation)

Reports are saved as `relatorio_precos_YYYYMMDD_HHMMSS.xlsx`

## Limitations

- **Web Scraping**: This tool uses web scraping which may break if stores change page structure
- **Rate Limiting**: Built-in delays to avoid being blocked
- **Brazil Only**: Currently optimized for Brazilian store websites
- **API Costs**: Product categorization uses Anthropic API (pay-per-use)

## Future Improvements

- [ ] Telegram/Discord notifications
- [ ] Browser automation (Selenium) for more reliable scraping
- [ ] Price prediction based on historical data
- [ ] Web dashboard interface
- [ ] Support for more supermarkets (Big, Nacional, etc.)
- [ ] Batch categorization optimization

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Respect each store's terms of service and use responsibly.
