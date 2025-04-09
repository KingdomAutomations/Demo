"""
Main entry point for the Craigslist car listing scraper with database storage.
This script coordinates the scraping and PostgreSQL database storage processes.
"""
import os
import time
import logging
import schedule
from dotenv import load_dotenv
from flask import Flask

from craigslist_scraper import scrape_craigslist
from database_manager import DatabaseManager
from keep_alive import keep_alive
from config import SEARCH_URL, FILTER_KEYWORDS
from models import db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
with app.app_context():
    db.create_all()

# Initialize database manager
db_manager = DatabaseManager()

def main():
    """Main function to scrape Craigslist and update database"""
    with app.app_context():
        try:
            logger.info("Starting Craigslist scraper")
            
            # Get existing listing URLs to avoid duplicates
            existing_urls = db_manager.get_existing_urls()
            
            # Scrape Craigslist for new listings
            new_listings = scrape_craigslist(SEARCH_URL, existing_urls, FILTER_KEYWORDS)
            
            if new_listings:
                logger.info(f"Found {len(new_listings)} new listings")
                
                # Sort listings by posting time (newest first)
                try:
                    from datetime import datetime
                    # Sort by posting time, newest first
                    sorted_listings = sorted(
                        new_listings,
                        key=lambda x: datetime.strptime(x['posting_time'], "%Y-%m-%d %H:%M:%S") 
                        if (x['posting_time'] != "N/A" and len(x['posting_time']) >= 10) 
                        else datetime(1970, 1, 1),
                        reverse=True
                    )
                    logger.info("Listings sorted by posting time (newest first)")
                    new_listings = sorted_listings
                except Exception as e:
                    logger.error(f"Error sorting listings: {str(e)}")
                    # If sorting fails, continue with unsorted listings
                
                # Add new listings to the database
                db_manager.add_listings(new_listings)
                logger.info("Successfully added new listings to database")
                
                # Update market analysis data
                db_manager.update_market_analysis()
                logger.info("Updated market analysis data")
            else:
                logger.info("No new listings found")
        
        except Exception as e:
            logger.error(f"Error in main execution: {str(e)}", exc_info=True)

def run_scheduler():
    """Set up and run the scheduler for hourly execution"""
    logger.info("Setting up scheduler")
    
    # Run once immediately
    main()
    
    # Schedule to run every hour
    schedule.every(1).hour.do(main)
    
    logger.info("Scheduler set up - will run every hour")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute for pending tasks

if __name__ == "__main__":
    # Start the keep-alive server
    keep_alive()
    
    # Start the scheduler
    run_scheduler()

# Import the Flask app for Gunicorn
try:
    from app_db import app
except ImportError:
    logger.error("Failed to import app_db")
    
    # Create a placeholder app if app_db is not available
    @app.route('/')
    def home():
        return "Craigslist Scraper with Database is running!"