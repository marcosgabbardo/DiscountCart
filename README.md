# DiscountCart - Price Monitor

A price monitoring tool for **Zaffari** and **Carrefour** supermarket products (Brazil). Get terminal alerts when prices reach your target and compare prices between stores.

## Features

- **Multi-Store Support**: Monitor products from Zaffari and Carrefour
- **Add Products**: Monitor any product via URL (auto-detects store)
- **Set Target Price**: Define the price you want to pay
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

## Supported Stores

| Store | Website | URL Format |
|-------|---------|------------|
| Zaffari | zaffari.com.br | `https://www.zaffari.com.br/produto-SKU/p` |
| Carrefour | mercado.carrefour.com.br | `https://mercado.carrefour.com.br/produto-SKU/p` |

## Requirements

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+

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
# Edit .env with your database credentials
```

5. **Initialize the database**:
```bash
python price_monitor.py init-db
```

6. **If upgrading from a previous version** (Zaffari-only):
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

# Alert Configuration
PRICE_DROP_THRESHOLD_PERCENT=10
```

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

The store is automatically detected from the URL.

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

Output includes the store name:
```
============================================================
📦 Arroz Branco Tipo 1 Carrefour 5kg
============================================================
ID:           3
Loja:         Carrefour
SKU:          3043
URL:          https://mercado.carrefour.com.br/arroz-branco-tipo-1-carrefour-5-kg-3043/p
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

If you're upgrading from the Zaffari-only version:

```bash
python price_monitor.py migrate
```

This adds the `store` column to existing products (defaults to 'zaffari').

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

- **products**: Monitored products with URLs, store, and target prices
- **price_history**: Historical price records
- **alerts**: Alert configurations and status

Key fields in `products`:
- `store`: ENUM('zaffari', 'carrefour') - identifies the source store
- `asin`: Product SKU (unique per store)

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

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `init-db` | Initialize database schema |
| `migrate` | Run migration for multi-store support |
| `add URL PRICE` | Add product to monitor |
| `list [--store]` | List all products (optionally filtered) |
| `check` | Check prices and show alerts |
| `update` | Update all product prices |
| `alerts` | Show triggered alerts |
| `history ID [--days]` | Show price history |
| `detail ID` | Show product details |
| `remove ID` | Remove product from monitoring |

## Limitations

- **Web Scraping**: This tool uses web scraping which may break if stores change page structure
- **Rate Limiting**: Built-in delays to avoid being blocked
- **Brazil Only**: Currently optimized for Brazilian store websites
- **No Product Matching**: Same product in different stores are tracked separately (different SKUs)

## Future Improvements

- [ ] Telegram/Discord notifications
- [ ] Browser automation (Selenium) for more reliable scraping
- [ ] Price prediction based on historical data
- [ ] Web dashboard interface
- [ ] AI-powered product matching across stores
- [ ] Support for more supermarkets (Big, Nacional, etc.)

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Respect each store's terms of service and use responsibly.
