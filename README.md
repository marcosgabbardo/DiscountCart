# Amazon Price Monitor 🛒

Monitor Amazon Brazil product prices and get alerts when prices drop to your target.

## Features

- **Add Products**: Monitor any Amazon Brazil product by URL
- **Set Target Prices**: Define the price you want to pay
- **Price History**: Track price changes over time
- **Smart Alerts**: Get notified when:
  - Price reaches your target
  - Price drops below 7/30-day average
  - New lowest price detected
- **Statistics**: View average prices, lowest/highest prices
- **Multiple Notifications**: Console, Email, and Telegram support

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

5. **Initialize database**:
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
DB_NAME=amazon_price_monitor

# Scraping Configuration
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5

# Alert Configuration
PRICE_DROP_THRESHOLD_PERCENT=10

# Optional: Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

### Add a Product to Monitor

```bash
python price_monitor.py add "https://www.amazon.com.br/dp/B0BTXDTD6H" "R$80,99"
```

You can use different price formats:
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
📦 Monitored Products (3)
--------------------------------------------------------------------------------
ID   Product                                   Current       Target        Difference   Status
1    Wild Side American Whiskey...             R$ 89,90      R$ 80,99      ⬇️ R$ 8,91   👀
2    Echo Dot 5ª Geração...                    R$ 299,00     R$ 249,99     ⬇️ R$ 49,01  👀
3    Kindle Paperwhite...                      R$ 499,00     R$ 499,00     ✅ R$ 0,00   ✅
```

### Check Prices and Alerts

```bash
python price_monitor.py check
```

### Update All Prices

```bash
python price_monitor.py update
```

This fetches current prices from Amazon for all monitored products.

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

## Automation

### Using Cron (Linux/Mac)

Add to crontab to check prices every hour:

```bash
crontab -e
```

Add:
```
0 * * * * cd /path/to/DiscountCart && /path/to/venv/bin/python price_monitor.py update >> /var/log/price_monitor.log 2>&1
```

### Using Task Scheduler (Windows)

Create a scheduled task to run:
```
python C:\path\to\DiscountCart\price_monitor.py update
```

## Database Schema

The application uses 4 main tables:

- **products**: Monitored products with URLs and target prices
- **price_history**: Historical price records
- **alerts**: Alert configurations and status
- **notifications**: Notification history

## Telegram Notifications Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
3. Add to `.env`:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

## Limitations

- **Web Scraping**: This tool uses web scraping which may break if Amazon changes their page structure
- **Rate Limiting**: Built-in delays to avoid being blocked by Amazon
- **Amazon Brazil Only**: Currently optimized for amazon.com.br

## Future Improvements

- [ ] Support for other Amazon regions
- [ ] Browser automation (Selenium) for more reliable scraping
- [ ] Price prediction based on historical data
- [ ] Web dashboard interface
- [ ] Mobile app notifications
- [ ] Price comparison with other e-commerce sites

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Be respectful of Amazon's terms of service and use responsibly. The developers are not responsible for any misuse of this tool.
