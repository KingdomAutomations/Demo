"""
Flask web application for viewing Craigslist car listings.
This provides a simple web interface to view the scraped data.
"""
import os
import logging
import gspread
from datetime import datetime
from flask import Flask, render_template, jsonify
from oauth2client.service_account import ServiceAccountCredentials

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "craigslist-scraper-secret-key")

# Google Sheets configuration
SPREADSHEET_KEY = os.environ.get('SPREADSHEET_KEY')
WORKSHEET_NAME = os.environ.get('WORKSHEET_NAME', 'Craigslist Car Listings')

def get_sheet_data():
    """
    Get data from Google Sheets
    """
    try:
        # Define the scope
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        # Get credentials from file
        credentials_path = 'credentials.json'
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        
        # Authorize the client
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(WORKSHEET_NAME)
        
        # Get all data
        data = sheet.get_all_records()
        
        return data
    except Exception as e:
        logger.error(f"Error getting sheet data: {str(e)}")
        return []

@app.route('/')
def index():
    """Home page with listing of cars"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/api/listings')
def get_listings():
    """API endpoint to get the listings data"""
    try:
        listings = get_sheet_data()
        return jsonify(listings)
    except Exception as e:
        logger.error(f"Error getting listings: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """API endpoint to get statistics about the listings"""
    try:
        listings = get_sheet_data()
        
        # Get some basic stats
        total_listings = len(listings)
        
        # Get count by make/model
        models = {}
        for listing in listings:
            title = listing.get('title', '').lower()
            # Check for common Toyota models
            for model in ['camry', 'corolla', 'prius', 'rav4', 'tacoma', 'tundra', 'sienna', 'highlander']:
                if model in title:
                    models[model] = models.get(model, 0) + 1
                    break
        
        # Get average price
        prices = [float(listing.get('price', '0').replace('$', '').replace(',', '')) 
                 for listing in listings if listing.get('price') and listing.get('price') != 'N/A']
        avg_price = sum(prices) / len(prices) if prices else 0
        
        # Get newest listings (top 5)
        newest = sorted(
            listings,
            key=lambda x: datetime.strptime(x.get('posting_time', '1970-01-01'), "%Y-%m-%d %H:%M:%S") 
                if (x.get('posting_time') and x.get('posting_time') != 'N/A' and len(x.get('posting_time', '')) >= 10) 
                else datetime(1970, 1, 1),
            reverse=True
        )[:5]
        
        return jsonify({
            'total_listings': total_listings,
            'models': models,
            'average_price': avg_price,
            'newest_listings': newest
        })
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Create necessary directories for templates and static files
if not os.path.exists('templates'):
    os.makedirs('templates')
if not os.path.exists('static'):
    os.makedirs('static')