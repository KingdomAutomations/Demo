"""
Utility script to expand the number of columns in the Google Sheet.
This is needed to add the KBB lookup column.
"""
import logging
import os
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Expand the number of columns in the worksheet"""
    try:
        logger.info("Starting sheet expansion process")
        
        # Google Sheets API setup
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials from file
        creds_file = 'credentials.json'
        if not os.path.exists(creds_file):
            raise ValueError(f"Credentials file not found: {creds_file}")
            
        credentials = Credentials.from_service_account_file(
            creds_file, scopes=scope
        )
        client = gspread.authorize(credentials)
        
        # Get spreadsheet info from environment
        spreadsheet_key = os.getenv('SPREADSHEET_KEY')
        worksheet_name = os.getenv('WORKSHEET_NAME', 'Craigslist Car Listings')
        
        if not spreadsheet_key:
            raise ValueError("SPREADSHEET_KEY not found in environment variables")
            
        # Open the spreadsheet and worksheet
        spreadsheet = client.open_by_key(spreadsheet_key)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Get current properties
        props = worksheet.get_all_values()
        rows = len(props) if props else 1
        cols = len(props[0]) if props and props[0] else 7
        
        # Resize to include more columns (at least 8 for the KBB lookup column)
        new_cols = max(cols, 8)
        rows = max(rows, 1000)  # Ensure at least 1000 rows
        
        logger.info(f"Resizing worksheet from {cols} to {new_cols} columns")
        worksheet.resize(rows=rows, cols=new_cols)
        
        logger.info(f"Worksheet successfully resized to {rows} rows x {new_cols} columns")
        
    except Exception as e:
        logger.error(f"Error expanding sheet: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()