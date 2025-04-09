"""
Configuration settings for the Craigslist scraper.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default search URL - can be overridden in .env file
DEFAULT_SEARCH_URL = "https://losangeles.craigslist.org/search/cta?auto_make_model=honda+civic&min_price=1500&max_price=7000&min_auto_year=2012"

# Get the search URL from environment variable or use default
SEARCH_URL = os.getenv('CRAIGSLIST_SEARCH_URL', DEFAULT_SEARCH_URL)

# Keywords to filter out of listings (e.g., "salvage", "rebuilt", etc.)
FILTER_KEYWORDS = os.getenv('FILTER_KEYWORDS', 'salvage,rebuilt,flood,damaged,parts').split(',')

# Google Sheets configuration
SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME', 'Craigslist Car Listings')
