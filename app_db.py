"""
Flask web application for viewing Craigslist car listings with database backend.
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
from sqlalchemy import func, desc, asc

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import models and database after app is created
from models import db, CarListing, MarketAnalysis
from database_manager import DatabaseManager

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()

# Initialize database manager
db_manager = DatabaseManager()

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Craigslist Car Listings</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .car-card { margin-bottom: 20px; transition: transform 0.2s; }
        .car-card:hover { transform: translateY(-5px); }
        .new-badge { position: absolute; top: 10px; right: 10px; }
        .deal-great { color: #28a745; font-weight: bold; }
        .deal-fair { color: #ffc107; }
        .deal-poor { color: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <header class="mb-4">
            <h1 class="display-4">Craigslist Car Market Analyzer</h1>
            <p class="lead">Automatically analyzes Toyota listings from Los Angeles Craigslist</p>
        </header>

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Current Search Parameters</h5>
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">Make/Model: Toyota</li>
                            <li class="list-group-item">Price Range: $5,000 - $15,000</li>
                            <li class="list-group-item">Year: 2010 or newer</li>
                            <li class="list-group-item">Location: Los Angeles</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Filter Keywords</h5>
                        <p>Listings with these words are filtered out:</p>
                        <div class="d-flex flex-wrap gap-2">
                            <span class="badge bg-danger">salvage</span>
                            <span class="badge bg-danger">rebuilt</span>
                            <span class="badge bg-danger">flood</span>
                            <span class="badge bg-danger">damaged</span>
                            <span class="badge bg-danger">parts</span>
                            <span class="badge bg-danger">mechanic</span>
                            <span class="badge bg-danger">special</span>
                            <span class="badge bg-danger">repair</span>
                            <span class="badge bg-danger">project</span>
                            <span class="badge bg-danger">needs</span>
                            <span class="badge bg-danger">issue</span>
                            <span class="badge bg-danger">problem</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h2>Scraper Status</h2>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5>Craigslist Scraper</h5>
                                <p class="text-success">
                                    <i class="bi bi-check-circle-fill"></i> Running
                                </p>
                            </div>
                            <div>
                                <h5>Scrape Frequency</h5>
                                <p>Every 1 hour</p>
                            </div>
                            <div>
                                <h5>Last Run</h5>
                                <p id="last-run">{{ last_run }}</p>
                            </div>
                            <div>
                                <h5>Database Status</h5>
                                <p class="text-success">
                                    <i class="bi bi-check-circle-fill"></i> Connected
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Market Analysis Section -->
        <div class="row my-4">
            <div class="col-12">
                <h2 class="mb-3">Market Analysis</h2>
                <div class="card">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <span>Current Market Prices by Model</span>
                            <button class="btn btn-sm btn-primary" id="refresh-market-data">
                                Refresh Analysis
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Make</th>
                                        <th>Model</th>
                                        <th>Years</th>
                                        <th>Avg Price</th>
                                        <th>Median Price</th>
                                        <th>Price Range</th>
                                        <th>Sample Size</th>
                                    </tr>
                                </thead>
                                <tbody id="market-data">
                                    {% for analysis in market_analysis %}
                                    <tr>
                                        <td>{{ analysis.make }}</td>
                                        <td>{{ analysis.model }}</td>
                                        <td>{{ analysis.year_range }}</td>
                                        <td>{{ analysis.avg_price }}</td>
                                        <td>{{ analysis.median_price }}</td>
                                        <td>{{ analysis.price_range }}</td>
                                        <td>{{ analysis.sample_size }}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Listings Section -->
        <div class="row">
            <div class="col-12">
                <h2 class="mb-3">Recent Listings</h2>
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Posted</th>
                                <th>Title</th>
                                <th>Price</th>
                                <th>Location</th>
                                <th>Market Comparison</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="listings-data">
                            {% for listing in listings %}
                            <tr>
                                <td>{{ listing.posting_time }}</td>
                                <td>{{ listing.title }}</td>
                                <td>{{ listing.price }}</td>
                                <td>{{ listing.location }}</td>
                                <td class="{{ listing.deal_class }}">{{ listing.deal_status }}</td>
                                <td>
                                    <a href="{{ listing.url }}" target="_blank" class="btn btn-sm btn-outline-primary">View</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                <div class="text-center my-3">
                    <button id="load-more" class="btn btn-outline-secondary">Load More</button>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <h2 class="mb-4">Recent Enhancements</h2>
                <div class="card mb-4 bg-primary-subtle">
                    <div class="card-body">
                        <h5 class="card-title">📊 Market Value Analysis</h5>
                        <p>Added database-backed market analysis that calculates average, median, and range prices for each make/model</p>
                        <p class="small">The system automatically compares each listing to the market average to help identify good deals</p>
                    </div>
                </div>
                <div class="card mb-4">
                    <div class="card-body">
                        <h5 class="card-title">🚗 Kelly Blue Book Lookup URLs</h5>
                        <p>Added automatic KBB lookup links for each listing to help you quickly check vehicle values</p>
                    </div>
                </div>
                <div class="card mb-4">
                    <div class="card-body">
                        <h5 class="card-title">Enhanced Web Scraping</h5>
                        <p>Added Playwright-based scraper for more detailed information extraction</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Update UI elements with AJAX
        document.addEventListener('DOMContentLoaded', function() {
            // Reload market data
            document.getElementById('refresh-market-data').addEventListener('click', function() {
                fetch('/api/update-market-analysis')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            location.reload();
                        } else {
                            alert('Failed to update market analysis: ' + data.error);
                        }
                    });
            });
            
            // Load more listings
            let page = 1;
            document.getElementById('load-more').addEventListener('click', function() {
                page++;
                fetch('/api/listings?page=' + page)
                    .then(response => response.json())
                    .then(data => {
                        if (data.listings.length > 0) {
                            const tbody = document.getElementById('listings-data');
                            data.listings.forEach(listing => {
                                const row = document.createElement('tr');
                                row.innerHTML = `
                                    <td>${listing.posting_time}</td>
                                    <td>${listing.title}</td>
                                    <td>${listing.price}</td>
                                    <td>${listing.location}</td>
                                    <td class="${listing.deal_class}">${listing.deal_status}</td>
                                    <td>
                                        <a href="${listing.url}" target="_blank" class="btn btn-sm btn-outline-primary">View</a>
                                    </td>
                                `;
                                tbody.appendChild(row);
                            });
                        }
                        
                        // Hide load more button if no more results
                        if (data.listings.length === 0) {
                            document.getElementById('load-more').style.display = 'none';
                        }
                    });
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Home page with listings and market analysis"""
    # Get last scrape time
    last_scrape = CarListing.query.order_by(CarListing.scraped_at.desc()).first()
    last_run = last_scrape.scraped_at.strftime("%Y-%m-%d %H:%M:%S") if last_scrape else "Never"
    
    # Get market analysis data
    market_analysis = db_manager.get_market_analysis()
    
    # Get recent listings with market comparison
    listings = get_recent_listings(page=1)
    
    return render_template_string(
        HTML_TEMPLATE, 
        last_run=last_run,
        market_analysis=market_analysis,
        listings=listings
    )

@app.route('/api/listings')
def api_listings():
    """API endpoint to get the listings data with pagination"""
    page = request.args.get('page', 1, type=int)
    listings = get_recent_listings(page=page)
    return jsonify({"listings": listings})

@app.route('/api/update-market-analysis')
def update_market_analysis():
    """API endpoint to update market analysis data"""
    try:
        db_manager.update_market_analysis()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating market analysis: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})

def get_recent_listings(page=1, per_page=20):
    """Get recent listings with market comparison"""
    # Calculate offset for pagination
    offset = (page - 1) * per_page
    
    # Get listings with pagination
    query = CarListing.query.order_by(CarListing.posting_time.desc().nullslast())
    listings = query.offset(offset).limit(per_page).all()
    
    # Get market analysis data for price comparison
    analyses = MarketAnalysis.query.all()
    analysis_dict = {}
    for analysis in analyses:
        key = f"{analysis.make}_{analysis.model}".lower()
        analysis_dict[key] = analysis
    
    # Format listing data with market comparison
    formatted_listings = []
    for listing in listings:
        # Format posting time
        posting_time = "N/A"
        if listing.posting_time:
            posting_time = listing.posting_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate deal status compared to market average
        deal_status = "Unknown"
        deal_class = ""
        
        if listing.make and listing.model:
            # Get market analysis for this make/model
            key = f"{listing.make}_{listing.model}".lower()
            if key in analysis_dict:
                analysis = analysis_dict[key]
                
                # Extract numeric price
                try:
                    price_str = listing.price.replace('$', '').replace(',', '')
                    price = float(price_str)
                    
                    # Compare to average
                    avg_price = analysis.avg_price
                    if price < avg_price * 0.85:  # 15% below average
                        deal_status = "Great Deal"
                        deal_class = "deal-great"
                    elif price < avg_price * 0.95:  # 5% below average
                        deal_status = "Good Deal"
                        deal_class = "deal-fair"
                    elif price < avg_price * 1.05:  # Within 5% of average
                        deal_status = "Fair Price"
                        deal_class = ""
                    else:  # Above average
                        deal_status = "Above Market"
                        deal_class = "deal-poor"
                        
                except (ValueError, AttributeError):
                    deal_status = "Price Unknown"
        
        formatted_listings.append({
            "title": listing.title,
            "price": listing.price,
            "url": listing.url,
            "location": listing.location,
            "posting_time": posting_time,
            "deal_status": deal_status,
            "deal_class": deal_class
        })
    
    return formatted_listings

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)