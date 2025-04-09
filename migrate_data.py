"""
Migration script to transfer existing data from Google Sheets to the PostgreSQL database.
"""
import os
import logging
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database components
from models import db, CarListing
from database_manager import DatabaseManager
from sheets_manager import SheetsManager

# Create Flask app for database connection
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

def migrate_data():
    """
    Migrate data from Google Sheets to PostgreSQL database
    """
    try:
        logger.info("Starting data migration from Google Sheets to PostgreSQL")
        
        # Initialize managers
        sheets_manager = SheetsManager()
        db_manager = DatabaseManager()
        
        # Get all data from Google Sheets
        with app.app_context():
            # Get existing URLs in database to avoid duplicates
            existing_urls = db_manager.get_existing_urls()
            logger.info(f"Found {len(existing_urls)} existing listings in database")
            
            # Get all rows from the sheet (skip header row)
            all_rows = sheets_manager.worksheet.get_all_values()
            logger.info(f"Found {len(all_rows) - 1} rows in Google Sheets")
            
            if len(all_rows) <= 1:
                logger.info("No data to migrate from Google Sheets")
                return
            
            # Extract headers and data
            headers = all_rows[0]
            data_rows = all_rows[1:]
            
            # Map column indices
            title_idx = headers.index('Title') if 'Title' in headers else 0
            price_idx = headers.index('Price') if 'Price' in headers else 1
            url_idx = headers.index('URL') if 'URL' in headers else 2
            location_idx = headers.index('Location') if 'Location' in headers else 3
            posting_time_idx = headers.index('Posting Time') if 'Posting Time' in headers else 4
            scraped_at_idx = headers.index('Scraped At') if 'Scraped At' in headers else 5
            
            # Convert rows to listing dictionaries
            listings = []
            for row in data_rows:
                # Skip rows that are too short
                if len(row) <= max(title_idx, price_idx, url_idx, location_idx, posting_time_idx, scraped_at_idx):
                    continue
                
                # Get values from row
                title = row[title_idx]
                price = row[price_idx]
                url = row[url_idx]
                
                # Skip if URL is missing or already in database
                if not url or url in existing_urls:
                    continue
                
                location = row[location_idx]
                posting_time = row[posting_time_idx]
                scraped_at = row[scraped_at_idx]
                
                # Create listing dictionary
                listing = {
                    'title': title,
                    'price': price,
                    'url': url,
                    'location': location,
                    'posting_time': posting_time,
                    'scraped_at': scraped_at
                }
                
                listings.append(listing)
            
            # Add listings to database
            logger.info(f"Migrating {len(listings)} listings to database")
            db_manager.add_listings(listings)
            
            # Update market analysis
            logger.info("Updating market analysis")
            db_manager.update_market_analysis()
            
            logger.info("Data migration completed successfully")
    
    except Exception as e:
        logger.error(f"Error migrating data: {str(e)}", exc_info=True)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        migrate_data()