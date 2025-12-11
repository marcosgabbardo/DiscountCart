"""
Configuration settings for Amazon Price Monitor.
Loads settings from environment variables or .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Database settings
        self.DB_HOST = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT = int(os.getenv('DB_PORT', '3306'))
        self.DB_USER = os.getenv('DB_USER', 'root')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        self.DB_NAME = os.getenv('DB_NAME', 'amazon_price_monitor')

        # Scraping settings
        self.SCRAPE_DELAY_MIN = int(os.getenv('SCRAPE_DELAY_MIN', '2'))
        self.SCRAPE_DELAY_MAX = int(os.getenv('SCRAPE_DELAY_MAX', '5'))
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

        # Alert settings
        self.CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '60'))
        self.PRICE_DROP_THRESHOLD_PERCENT = float(os.getenv('PRICE_DROP_THRESHOLD_PERCENT', '10'))

        # Regional settings (CEP for Carrefour pricing)
        self.CEP = os.getenv('CEP', '90420-010')

        # Anthropic API settings (for product categorization)
        self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

        # User agents for scraping (rotated to avoid detection)
        self.USER_AGENTS = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

    @property
    def database_url(self) -> str:
        """Returns the MySQL connection URL."""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
