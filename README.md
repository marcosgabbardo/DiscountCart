# Zaffari Price Monitor

A price monitoring tool for Zaffari supermarket products (Brazil). Get terminal alerts when prices reach your target.

## Features

- **Add Products**: Monitor any Zaffari product via URL
- **Set Target Price**: Define the price you want to pay
- **Price History**: Track price variations over time
- **Smart Alerts**: Get notified when:
  - Price reaches your target
  - Price drops below 7/30 day average
  - Price falls 1 standard deviation below 30-day average
  - New lowest price detected
- **Statistics**: View average, minimum, and maximum prices
- **Daily Scheduler**: Automatic updates at 8:00 AM with Excel reports
- **Excel Reports**: Generated reports with price changes and alert status

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

## Configuration

Edit the `.env` file with your settings:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=zaffari_price_monitor

# Scraping Configuration
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5

# Alert Configuration
PRICE_DROP_THRESHOLD_PERCENT=10
```

## Usage

### Add a Product to Monitor

```bash
python price_monitor.py add "https://www.zaffari.com.br/produto-123/p" "R$80,99"
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
Monitored Products (3)
--------------------------------------------------------------------------------
ID   Product                                   Current       Target        Difference   Status
1    Presunto Cozido Fatiado Sadia...          R$ 6,99       R$ 6,55       R$ 0,44
2    Queijo Mussarela President...             R$ 12,90      R$ 10,99      R$ 1,91
3    Leite Integral Piracanjuba...             R$ 5,49       R$ 5,49       R$ 0,00      OK
```

### Check Prices and Alerts

```bash
python price_monitor.py check
```

### Update All Prices

```bash
python price_monitor.py update
```

Fetches current prices from Zaffari for all monitored products.

### View Price History

```bash
python price_monitor.py history 1 --days 30
```

### View Product Details

```bash
python price_monitor.py detail 1
```

### View Triggered Alerts

```bash
python price_monitor.py alerts
```

### Remove a Product

```bash
python price_monitor.py remove 1
```

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
1. Update all product prices
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

- **products**: Monitored products with URLs and target prices
- **price_history**: Historical price records
- **alerts**: Alert configurations and status

## Alert Types

| Alert Type | Description |
|------------|-------------|
| `TARGET_REACHED` | Price reached or fell below target |
| `PRICE_DROP` | Significant price drop detected |
| `BELOW_AVERAGE` | Price below 7-day average |
| `STD_DEVIATION` | Price 1 std deviation below 30-day average |

## Excel Reports

Generated reports include:
- Product ID and name
- Previous and current price
- Price variation percentage
- Target price
- 30-day average and standard deviation
- Alert indicators (Target reached, Std deviation)

Reports are saved as `relatorio_precos_YYYYMMDD_HHMMSS.xlsx`

## Limitations

- **Web Scraping**: This tool uses web scraping which may break if Zaffari changes page structure
- **Rate Limiting**: Built-in delays to avoid being blocked
- **Zaffari Brazil Only**: Currently optimized for zaffari.com.br

## Future Improvements

- [ ] Telegram/Discord notifications
- [ ] Browser automation (Selenium) for more reliable scraping
- [ ] Price prediction based on historical data
- [ ] Web dashboard interface
- [ ] Price comparison with other supermarkets

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Respect Zaffari's terms of service and use responsibly.
