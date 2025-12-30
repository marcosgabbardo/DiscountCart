# DiscountCart - Price Monitor

A price monitoring tool for **Zaffari** and **Carrefour** supermarket products (Brazil). Get alerts when prices drop significantly below average using standard deviation analysis, compare prices between stores, and find the cheapest products by category using AI-powered categorization.

## Features

- **Multi-Store Support**: Monitor products from Zaffari and Carrefour
- **Add Products**: Monitor any product via URL (auto-detects store)
- **AI-Powered Categorization**: Automatic product categorization using Anthropic Claude API
- **Price Comparison by Category**: Compare prices of similar products across stores (e.g., all "Leite UHT Integral")
- **Price History**: Track price variations over time
- **Standard Deviation Alerts**: Get notified when prices are significantly below average:
  - **1 Standard Deviation**: Good deals (price below avg - 1σ)
  - **2 Standard Deviations**: Exceptional deals (price below avg - 2σ)
  - **Multiple Periods**: Analyzed for 30, 90, and 180 days
- **Statistics**: View average, minimum, maximum prices and standard deviation analysis
- **Daily Scheduler**: Automatic updates at 8:00 AM with Excel reports
- **Excel Reports**: Generated reports with price changes, store info, and std deviation alerts
- **Filter by Store**: List products from a specific store

## Standard Deviation Alerts

The system uses statistical analysis to identify truly exceptional prices:

| Alert Level | Meaning | Interpretation |
|-------------|---------|----------------|
| 🔥 2 Std Dev | Price is 2+ standard deviations below average | Exceptional deal - rarely this low |
| ✅ 1 Std Dev | Price is 1+ standard deviation below average | Good deal - below typical price |

Alerts are calculated for three time periods:
- **30 days**: Recent price behavior
- **90 days**: Medium-term trend
- **180 days**: Long-term historical comparison

> **Important**: Standard deviation calculations require a **minimum of 30 data points** (price records) to ensure statistical significance. Products with less historical data won't generate std deviation alerts.

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
python price_monitor.py add "https://www.zaffari.com.br/produto-123/p"
```

**Carrefour:**
```bash
python price_monitor.py add "https://mercado.carrefour.com.br/produto-456/p"
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

📢 Produto será monitorado para alertas de desvio padrão.
   Use 'check' para ver alertas quando o preço estiver abaixo da média.
```

### List All Monitored Products

```bash
python price_monitor.py list
```

Output:
```
📦 Produtos Monitorados (4)
Legenda: 🟢 Zaffari | 🔵 Carrefour
----------------------------------------------------------------------------------------------------
ID   Loja   Produto                              Atual          Mínimo         Máximo         Status
1    🟢     Presunto Cozido Fatiado Sadia...     R$ 6,99        R$ 6,55        R$ 7,49        +6.7%
2    🟢     Queijo Mussarela President...        R$ 12,90       R$ 10,99       R$ 14,50       +17.4%
3    🔵     Arroz Branco Carrefour 5kg           R$ 24,90       R$ 22,00       R$ 28,90       +13.2%
4    🔵     Leite Integral Piracanjuba...        R$ 5,49        R$ 5,49        R$ 6,29        📉 Mínimo
```

### Filter by Store

```bash
# Only Zaffari products
python price_monitor.py list --store zaffari

# Only Carrefour products
python price_monitor.py list --store carrefour
```

---

## Alert Commands

### Check Standard Deviation Alerts

```bash
python price_monitor.py check
```

Output:
```
Verificando preços e alertas de desvio padrão...

======================================================================
📊 RESUMO DE ALERTAS POR DESVIO PADRÃO
======================================================================

🔥 OFERTAS EXCEPCIONAIS (2 Desvios Padrão)
----------------------------------------------------------------------

  📅 Período: 30d
    • Leite Integral Piracanjuba 1L...
      R$ 4,99 (limite: R$ 5,45)

  📅 Período: 90d - Nenhum produto

  📅 Período: 180d - Nenhum produto


💰 BOAS OFERTAS (1 Desvio Padrão)
----------------------------------------------------------------------

  📅 Período: 30d
    • Arroz Branco Carrefour 5kg...
      R$ 22,90 (limite: R$ 24,50)
    • Coração de Frango Sadia 1kg...
      R$ 12,99 (limite: R$ 14,20)

  📅 Período: 90d
    • Leite Integral Piracanjuba 1L...
      R$ 4,99 (limite: R$ 5,60)

  📅 Período: 180d - Nenhum produto

======================================================================

🎯 1 oferta(s) excepcional(is) encontrada(s)!
```

### View All Alerts

```bash
python price_monitor.py alerts
```

Shows the complete standard deviation alert summary organized by period and severity.

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

### Update All Prices

```bash
python price_monitor.py update
```

Fetches current prices from all stores for all monitored products and shows updated alerts.

### View Price History

```bash
python price_monitor.py history 1 --days 30
```

Output includes standard deviation analysis:
```
📊 Histórico de Preços: Leite Integral Piracanjuba 1L
--------------------------------------------------

Estatísticas (últimos 30 dias):
   Média:   R$ 5,35
   Mínimo:  R$ 4,99
   Máximo:  R$ 5,89
   Registros: 28

📉 Análise de Desvio Padrão:

   30 dias:
      Média: R$ 5,35
      Desvio Padrão: R$ 0,28
      Limite 1 DP: R$ 5,07
      Limite 2 DP: R$ 4,79
      ⚡ ABAIXO DE 2 DESVIOS PADRÃO!

   90 dias:
      Média: R$ 5,50
      Desvio Padrão: R$ 0,35
      Limite 1 DP: R$ 5,15
      Limite 2 DP: R$ 4,80
      ✅ Abaixo de 1 desvio padrão

   180 dias:
      (dados insuficientes)

Preços recentes:
Data                  Preço
2024-01-15 08:00      R$ 4,99
2024-01-14 08:00      R$ 5,29
...
```

### View Price Chart

Display an interactive ASCII chart of price history directly in the terminal:

```bash
python price_monitor.py chart 1 --days 30
```

Output:
```
          📈 Histórico de Preços: Leite Integral Piracanjuba 1L
    ┌──────────────────────────────────────────────────────────────────┐
5.89┤                          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀                          │
    │                    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣤⣤⣶⣿⣿⣿⣿⣿⣶⣤⣄⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀                          │
5.50┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ ← Média
    │        ⠀⠀⠀⢀⣀⣤⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣤⣀⡀⠀                          │
5.07┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ ← 1 DP
    │⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿│
4.79┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ ← 2 DP
    │                                                              ⣿⣿⣿│
4.99┤                                                              ⣿⣿⣿│ ← Atual
    └┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┘
     01/12 05/12 09/12 13/12 17/12 21/12 25/12 29/12 02/01 06/01 10/01
                                   Data

────────────────────────────────────────────────────────────
📊 Estatísticas (30 dias) - 28 registros
────────────────────────────────────────────────────────────
  Atual:    R$ 4,99
  Média:    R$ 5,35 ━━ (linha amarela)
  Mínimo:   R$ 4,99
  Máximo:   R$ 5,89
  1 DP:     R$ 5,07 ━━ (linha verde)
  2 DP:     R$ 4,79 ━━ (linha vermelha)

  🔥 OFERTA EXCEPCIONAL! Preço abaixo de 2 desvios padrão!
────────────────────────────────────────────────────────────
```

The chart shows:
- **Cyan line**: Price history over time
- **Yellow line**: Average price for the period
- **Green line**: 1 standard deviation threshold (good deals)
- **Red line**: 2 standard deviations threshold (exceptional deals)

### View Product Details

```bash
python price_monitor.py detail 1
```

Output includes category and standard deviation analysis:
```
============================================================
📦 Leite Integral Piracanjuba 1L
============================================================
ID:           12
Loja:         Carrefour
SKU:          45678
Categoria:    Leite UHT Integral
URL:          https://mercado.carrefour.com.br/leite-integral-piracanjuba-1l-45678/p

💰 Preços:
   Atual:     R$ 4,99
   Mínimo:    R$ 4,79
   Máximo:    R$ 6,29

📊 Médias:
   Média (7d):   R$ 5,15
   Média (30d):  R$ 5,35
   Média (90d):  R$ 5,50
   Média (180d): R$ 5,65

📉 Análise de Desvio Padrão:
   30d: Limite 1DP=R$ 5,07 | 2DP=R$ 4,79 🔥 EXCEPCIONAL!
   90d: Limite 1DP=R$ 5,15 | 2DP=R$ 4,80 ✅ Bom preço
   180d: Limite 1DP=R$ 5,30 | 2DP=R$ 4,95

📅 Criado: 2024-01-01 10:30:00
📅 Atualizado: 2024-01-15 08:00:00
============================================================
```

### Remove a Product

```bash
python price_monitor.py remove 1
```

---

## Analyze Command

The `analyze` command provides advanced analysis of products based on various indicators. This is useful for finding buying opportunities using different metrics.

### Available Indicators

| Indicator | Description |
|-----------|-------------|
| `--min` | Products currently at their historical minimum price |
| `--max` | Products currently at their historical maximum price |
| `--below-avg` | Products priced below the period average |
| `--above-avg` | Products priced above the period average |
| `--drop` | Products that had a price drop in the last measurement |
| `--rise` | Products that had a price increase in the last measurement |
| `--std1` | Products below 1 standard deviation (requires 30+ records) |
| `--std2` | Products below 2 standard deviations (requires 30+ records) |
| `--volatile` | Products with high price volatility (coefficient of variation) |
| `--stable` | Products with stable prices (low coefficient of variation) |
| `--near-min` | Products within X% of their historical minimum |
| `--score` | Opportunity ranking combining multiple factors |

### Options

| Option | Description |
|--------|-------------|
| `--store`, `-s` | Filter by store (zaffari, carrefour) |
| `--days`, `-d` | Analysis period in days (default: 30) |
| `--threshold`, `-t` | Percentage threshold for some indicators |

### Examples

**Find products at historical minimum:**
```bash
python price_monitor.py analyze --min
```

Output:
```
📉 Produtos no PREÇO MÍNIMO histórico (3)
------------------------------------------------------------------------------------------
ID   Loja   Produto                                     Preço Atual (Mín)  Máximo
12   🔵     Leite Integral Piracanjuba 1L               R$ 4,99            R$ 6,29
5    🟢     Arroz Branco Tio João 5kg                   R$ 22,90           R$ 28,50
8    🔵     Coração de Frango Sadia 1kg                 R$ 12,99           R$ 16,90
------------------------------------------------------------------------------------------
Legenda: 🟢 Zaffari | 🔵 Carrefour
```

**Find products below average (custom period):**
```bash
python price_monitor.py analyze --below-avg --days 60
```

**Find products with recent price drop:**
```bash
python price_monitor.py analyze --drop
```

Output:
```
📉 Produtos com QUEDA DE PREÇO recente (2)
----------------------------------------------------------------------------------------------------
ID   Loja   Produto                              Anterior       Atual          Queda
12   🔵     Leite Integral Piracanjuba 1L        R$ 5,29        R$ 4,99        -5.7%
3    🟢     Queijo Mussarela President           R$ 14,50       R$ 12,90       -11.0%
----------------------------------------------------------------------------------------------------
```

**Find volatile products (filter by store):**
```bash
python price_monitor.py analyze --volatile --store zaffari --threshold 15
```

**View opportunity ranking:**
```bash
python price_monitor.py analyze --score
```

Output:
```
🏆 RANKING DE OPORTUNIDADES (15)
--------------------------------------------------------------------------------------------------------------
#    Loja   Produto                         Preço          Score     Fatores
🥇   🔵     Leite Integral Piracanjuba...   R$ 4,99        95 pts    No mínimo histórico (+20pts), Abaixo de 2 DP (+10pts)
🥈   🟢     Arroz Branco Tio João 5kg       R$ 22,90       75 pts    Próximo do mínimo (35pts), Abaixo da média 30d (+15pts)
🥉   🔵     Coração de Frango Sadia 1kg     R$ 12,99       60 pts    No mínimo histórico (+20pts), Abaixo da média 30d (+15pts)
 4   🟢     Queijo Mussarela President       R$ 12,90       45 pts    Abaixo da média 30d (+15pts), Abaixo de 1 DP (+15pts)
--------------------------------------------------------------------------------------------------------------

Score máximo: 100 pontos
```

The opportunity score considers:
- **Position in price range** (0-40 pts): How close to minimum vs maximum
- **At minimum** (+20 pts): Currently at historical low
- **Below 30d average** (+15 pts): Below the monthly average
- **Below 1 std deviation** (+15 pts): Statistically good price
- **Below 2 std deviations** (+10 pts): Exceptional statistical price

---

### Run Database Migration

If you're upgrading from a previous version:

```bash
python price_monitor.py migrate
```

This updates the database schema for the new standard deviation alert system.

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
2. Analyze all products for standard deviation alerts
3. Generate an Excel report with all price changes and alerts

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

- **products**: Monitored products with URLs, store, category, and price data
- **price_history**: Historical price records
- **alerts**: Alert configurations based on standard deviation

Key fields in `products`:
- `store`: ENUM('zaffari', 'carrefour') - identifies the source store
- `category`: VARCHAR(100) - AI-assigned product category
- `asin`: Product SKU (unique per store)
- `current_price`, `lowest_price`, `highest_price`: Price tracking

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `init-db` | Initialize database schema |
| `migrate` | Run migration for std deviation alert system |
| `add URL` | Add product to monitor (auto-categorizes) |
| `list [--store]` | List all products (optionally filtered by store) |
| `check` | Check prices and show std deviation alerts |
| `update` | Update all product prices |
| `alerts` | Show standard deviation alerts summary |
| `analyze --INDICATOR` | Analyze products by indicator (see below) |
| `history ID [--days]` | Show price history with std deviation analysis |
| `chart ID [--days]` | View price chart in terminal with std deviation lines |
| `detail ID` | Show product details with std deviation thresholds |
| `remove ID` | Remove product from monitoring |
| `categories` | List all categories with statistics |
| `category NAME` | Show products in a specific category |
| `compare NAME` | Compare prices by category across stores |
| `search-category TERM` | Search categories by keyword |
| `categorize [--all]` | Categorize products using AI |

### Analyze Indicators

| Indicator | Description |
|-----------|-------------|
| `--min` | Products at historical minimum price |
| `--max` | Products at historical maximum price |
| `--below-avg` | Products below period average |
| `--above-avg` | Products above period average |
| `--drop` | Products with recent price drop |
| `--rise` | Products with recent price increase |
| `--std1` | Products below 1 std deviation (30+ records) |
| `--std2` | Products below 2 std deviations (30+ records) |
| `--volatile` | High volatility products |
| `--stable` | Stable price products |
| `--near-min` | Products near historical minimum |
| `--score` | Opportunity ranking (combines all factors) |

## Alert Types

| Alert Type | Description |
|------------|-------------|
| `STD_DEV_1_30D` | Price 1 std deviation below 30-day average |
| `STD_DEV_1_90D` | Price 1 std deviation below 90-day average |
| `STD_DEV_1_180D` | Price 1 std deviation below 180-day average |
| `STD_DEV_2_30D` | Price 2 std deviations below 30-day average |
| `STD_DEV_2_90D` | Price 2 std deviations below 90-day average |
| `STD_DEV_2_180D` | Price 2 std deviations below 180-day average |

## Excel Reports

Generated reports include:
- Product ID and store
- Product name
- Previous and current price
- Price variation percentage
- Average and standard deviation for 30, 90, and 180 days
- Alert indicators:
  - 🔥 Green highlight: 2 standard deviations (exceptional deal)
  - ✅ Yellow highlight: 1 standard deviation (good deal)

Reports are saved as `relatorio_precos_YYYYMMDD_HHMMSS.xlsx`

## Limitations

- **Web Scraping**: This tool uses web scraping which may break if stores change page structure
- **Rate Limiting**: Built-in delays to avoid being blocked
- **Brazil Only**: Currently optimized for Brazilian store websites
- **API Costs**: Product categorization uses Anthropic API (pay-per-use)
- **Historical Data**: Standard deviation alerts work better with more price history

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
