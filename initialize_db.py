"""
Initialization script for the PostgreSQL database.
This creates the necessary tables and migrates data from Google Sheets if needed.
"""
import os
import logging
import argparse
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
from models import db, CarListing, MarketAnalysis

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

def initialize_database(migrate_data=True):
    """
    Initialize the database by creating tables and optionally migrating data
    """
    with app.app_context():
        try:
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully.")
            
            # Check if the database is empty
            listing_count = CarListing.query.count()
            logger.info(f"Found {listing_count} existing listings in database.")
            
            # Migrate data from Google Sheets if requested and database is empty
            if migrate_data and listing_count == 0:
                logger.info("Database is empty. Migrating data from Google Sheets...")
                try:
                    # Import and run migration script
                    from migrate_data import migrate_data
                    migrate_data()
                    logger.info("Data migration completed.")
                except Exception as e:
                    logger.error(f"Error migrating data from Google Sheets: {str(e)}", exc_info=True)
            
            # Run initial market analysis if there's data
            if CarListing.query.count() > 0:
                logger.info("Running initial market analysis...")
                try:
                    from database_manager import DatabaseManager
                    db_manager = DatabaseManager()
                    db_manager.update_market_analysis()
                    logger.info("Market analysis completed.")
                except Exception as e:
                    logger.error(f"Error running market analysis: {str(e)}", exc_info=True)
            
            logger.info("Database initialization completed successfully.")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the PostgreSQL database")
    parser.add_argument("--no-migrate", action="store_true", help="Skip data migration from Google Sheets")
    args = parser.parse_args()
    
    initialize_database(migrate_data=not args.no_migrate)