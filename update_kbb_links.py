"""
Utility script to add KBB lookup URLs to all existing listings in the Google Sheet.
Run this once to update all existing entries with KBB lookup links.
"""
import logging
import os
from dotenv import load_dotenv
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Add KBB lookup URLs to all existing entries"""
    try:
        logger.info("Starting KBB URL update process")
        
        # Initialize the Google Sheets manager
        sheets_manager = SheetsManager()
        
        # Force update of KBB lookup column
        sheets_manager._ensure_kbb_column()
        
        logger.info("KBB URL update process completed")
        
    except Exception as e:
        logger.error(f"Error in KBB URL update process: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()