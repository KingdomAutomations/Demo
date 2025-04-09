"""
Main entry point for the Craigslist car listing scraper.
This script coordinates the scraping and Google Sheets storage processes.

Note: The Flask app is imported at the end of this file for Gunicorn to find it.
"""
import os
import time
import logging
import schedule
from dotenv import load_dotenv

from craigslist_scraper import scrape_craigslist
from sheets_manager import SheetsManager
from keep_alive import keep_alive
from config import SEARCH_URL, FILTER_KEYWORDS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Main function to scrape Craigslist and update Google Sheets"""
    try:
        logger.info("Starting Craigslist scraper")
        
        # Initialize the Google Sheets manager
        sheets_manager = SheetsManager()
        
        # Get existing listing URLs to avoid duplicates
        existing_urls = sheets_manager.get_existing_urls()
        
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
            
            # Add new listings to the Google Sheet
            sheets_manager.add_listings(new_listings)
            logger.info("Successfully added new listings to Google Sheets")
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
    # First try the database-backed app
    from app_db import app
except ImportError:
    try:
        # Fall back to the simple web app
        from simple_web_app import app
    except ImportError:
        # Create a placeholder app if neither is available
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "Craigslist Scraper is running!"
