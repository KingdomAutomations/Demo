"""
Google Sheets manager module to handle interactions with Google Sheets.
"""
import os
import logging
import json
import time
from typing import List, Dict, Set, Optional
from datetime import datetime
import re
import urllib.parse

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    logging.error("Required packages not found. Make sure gspread and google-auth are installed.")
    raise

logger = logging.getLogger(__name__)

class SheetsManager:
    """Manages interactions with Google Sheets for storing Craigslist listings"""
    
    def __init__(self):
        """Initialize the SheetsManager with Google Sheets API credentials"""
        try:
            # Scope for Google Sheets API
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Try different methods to get credentials
            try:
                # First try using a credentials.json file
                creds_file = 'credentials.json'
                if os.path.exists(creds_file):
                    logger.info("Using credentials.json file for authentication")
                    credentials = Credentials.from_service_account_file(
                        creds_file, scopes=scope
                    )
                else:
                    # Fall back to environment variable
                    logger.info("credentials.json not found, trying environment variable")
                    creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
                    
                    if not creds_json:
                        raise ValueError("Google Sheets credentials not found in environment variables or credentials.json")
                    
                    # Try to parse the JSON string
                    try:
                        credentials_info = json.loads(creds_json)
                        credentials = Credentials.from_service_account_info(
                            credentials_info, scopes=scope
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse credentials JSON: {str(e)}")
                        raise ValueError(f"Invalid credentials format: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to authenticate with Google Sheets API: {str(e)}")
                raise
            
            self.client = gspread.authorize(credentials)
            
            # Get spreadsheet information from environment variables
            spreadsheet_key = os.getenv('SPREADSHEET_KEY')
            worksheet_name = os.getenv('WORKSHEET_NAME', 'Craigslist Car Listings')
            
            if not spreadsheet_key:
                raise ValueError("Spreadsheet key not found in environment variables.")
            
            # Open the spreadsheet
            self.spreadsheet = self.client.open_by_key(spreadsheet_key)
            
            # Try to open the worksheet, create it if it doesn't exist
            try:
                self.worksheet = self.spreadsheet.worksheet(worksheet_name)
                logger.info(f"Opened existing worksheet: {worksheet_name}")
                
                # Check if the worksheet has the KBB lookup column and add it if not
                self._ensure_kbb_column()
            except gspread.exceptions.WorksheetNotFound:
                # Create a new worksheet with headers
                self.worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name, 
                    rows=1000, 
                    cols=8
                )
                headers = [
                    'Title', 'Price', 'URL', 'Location', 'Posting Time', 
                    'Scraped At', 'Added At', 'KBB Lookup'
                ]
                self.worksheet.append_row(headers)
                logger.info(f"Created new worksheet: {worksheet_name}")
                
        except Exception as e:
            logger.error(f"Error initializing SheetsManager: {str(e)}", exc_info=True)
            raise
    
    def generate_kbb_lookup_url(self, title: str) -> str:
        """
        Generate a Kelley Blue Book lookup URL based on the listing title.
        
        Args:
            title: The title of the Craigslist listing
            
        Returns:
            A formatted URL for KBB lookup
        """
        try:
            # Extract year from title (assuming it's 4 digits between 1990 and 2030)
            year_match = re.search(r'\b(19[9][0-9]|20[0-2][0-9])\b', title)
            year = year_match.group(1) if year_match else ""
            
            # Extract make and model - common car makes
            common_makes = [
                "Toyota", "Honda", "Ford", "Chevrolet", "Chevy", "Nissan", "Hyundai", 
                "Kia", "Mazda", "Subaru", "Volkswagen", "VW", "Jeep", "BMW", 
                "Mercedes", "Lexus", "Acura", "Audi"
            ]
            
            # Try to find a make in the title
            make = ""
            for potential_make in common_makes:
                if potential_make.lower() in title.lower():
                    make = potential_make
                    # Special case for Chevy -> Chevrolet
                    if make.lower() == "chevy":
                        make = "Chevrolet"
                    # Special case for VW -> Volkswagen
                    if make.lower() == "vw":
                        make = "Volkswagen"
                    break
            
            # Extract model - just use everything after make as the query
            model = ""
            if make and make in title:
                # Get everything after the make
                make_index = title.lower().find(make.lower())
                if make_index >= 0:
                    after_make = title[make_index + len(make):].strip()
                    # Clean up the model (remove price, year, etc.)
                    model = re.sub(r'(\$[\d,]+|\d{4}|\(|\))', '', after_make).strip()
                    # Limit to first 20 chars to avoid including too much detail
                    model = model.split()[0] if model else ""
            
            # Build the KBB URL - use search format if we can't parse details
            if year and make:
                # We have at least year and make
                if model:
                    # Base URL for KBB
                    kbb_url = "https://www.kbb.com/cars-for-sale/year-{}/make-{}/model-{}/"
                    # Clean up and encode parameters
                    year_clean = urllib.parse.quote(year)
                    make_clean = urllib.parse.quote(make.lower())
                    model_clean = urllib.parse.quote(model.lower())
                    # Format the URL
                    return kbb_url.format(year_clean, make_clean, model_clean)
                else:
                    # Just year and make
                    kbb_url = "https://www.kbb.com/cars-for-sale/year-{}/make-{}/"
                    year_clean = urllib.parse.quote(year)
                    make_clean = urllib.parse.quote(make.lower())
                    return kbb_url.format(year_clean, make_clean)
            else:
                # Fallback to search
                search_terms = title.replace('$', '').replace(',', '')
                search_clean = urllib.parse.quote(search_terms)
                return f"https://www.kbb.com/cars-for-sale/all?search={search_clean}"
        
        except Exception as e:
            logger.warning(f"Error generating KBB URL for title '{title}': {str(e)}")
            # Fallback - just search with the title
            search_clean = urllib.parse.quote(title)
            return f"https://www.kbb.com/cars-for-sale/all?search={search_clean}"
            
    def get_existing_urls(self) -> Set[str]:
        """
        Get a set of all URLs already in the sheet to avoid duplicates
        
        Returns:
            Set of URLs already in the spreadsheet
        """
        try:
            # Get all values from the URL column (column 3) excluding the header
            all_rows = self.worksheet.get_all_values()
            
            # Check if there are any rows beyond the header
            if len(all_rows) <= 1:
                return set()
                
            # Extract URLs (column 3, index 2) from all rows except the header
            urls = [row[2] for row in all_rows[1:] if len(row) > 2]
            
            return set(urls)
            
        except Exception as e:
            logger.error(f"Error getting existing URLs: {str(e)}", exc_info=True)
            return set()
    
    def _ensure_kbb_column(self) -> None:
        """
        Ensures that the worksheet has a KBB lookup column.
        If it doesn't exist, adds the column and populates it for existing entries.
        """
        try:
            # Get the headers
            all_values = self.worksheet.get_all_values()
            
            if not all_values:
                logger.warning("Worksheet is empty, can't ensure KBB column")
                return
                
            headers = all_values[0]
            
            # Check if KBB Lookup column exists
            if 'KBB Lookup' not in headers:
                logger.info("Adding KBB Lookup column to worksheet")
                
                # Add the header
                header_col = len(headers) + 1  # 1-indexed for gspread
                self.worksheet.update_cell(1, header_col, 'KBB Lookup')
                
                # Generate KBB lookup URLs for existing entries
                if len(all_values) > 1:
                    # Find title column index (usually 0)
                    title_col_idx = headers.index('Title') if 'Title' in headers else 0
                    
                    # Process in batches to avoid rate limits
                    batch_size = 10
                    for i in range(1, len(all_values), batch_size):
                        batch_end = min(i + batch_size, len(all_values))
                        batch = all_values[i:batch_end]
                        
                        for j, row in enumerate(batch):
                            if len(row) > title_col_idx:
                                title = row[title_col_idx]
                                kbb_url = self.generate_kbb_lookup_url(title)
                                
                                # Row numbers are 1-indexed in gspread and we skip the header row
                                row_idx = i + j + 1
                                self.worksheet.update_cell(row_idx, header_col, kbb_url)
                        
                        # Small delay to avoid rate limits
                        if batch_end < len(all_values):
                            time.sleep(1)
                            
                logger.info("KBB Lookup column added and populated for existing entries")
        
        except Exception as e:
            logger.error(f"Error ensuring KBB column: {str(e)}")
            # Don't raise the exception - we can continue without the column if needed
    
    def add_listings(self, listings: List[Dict]) -> None:
        """
        Add new listings to the Google Sheet
        
        Args:
            listings: List of listing dictionaries to add to the sheet
        """
        if not listings:
            logger.info("No listings to add")
            return
            
        try:
            rows_to_add = []
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for listing in listings:
                # Get the title for KBB lookup URL generation
                title = listing.get('title', 'N/A')
                
                # Generate KBB lookup URL
                kbb_lookup_url = self.generate_kbb_lookup_url(title)
                
                # Create a row for the spreadsheet with safe access to dictionary keys
                row = [
                    title,
                    listing.get('price', 'N/A'),
                    listing.get('url', 'N/A'),
                    listing.get('location', 'N/A'),
                    listing.get('posting_time', 'N/A'),
                    listing.get('scraped_at', 'N/A'),
                    current_time,
                    kbb_lookup_url  # Add the KBB lookup URL
                ]
                rows_to_add.append(row)
            
            # Add all rows to the spreadsheet
            self.worksheet.append_rows(rows_to_add)
            logger.info(f"Added {len(rows_to_add)} new listings to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error adding listings to Google Sheets: {str(e)}", exc_info=True)
            raise
