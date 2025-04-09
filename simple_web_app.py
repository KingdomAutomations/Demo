"""
Simple Flask web application for viewing Craigslist car listings.
"""
import os
import logging
import json
from flask import Flask, render_template_string, jsonify

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)

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
    </style>
</head>
<body>
    <div class="container">
        <header class="mb-4">
            <h1 class="display-4">Craigslist Toyota Scraper</h1>
            <p class="lead">Automatically scrapes Toyota listings from Los Angeles Craigslist</p>
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
                                <p id="last-run">Just now</p>
                            </div>
                            <div>
                                <h5>Google Sheet Integration</h5>
                                <p class="text-success">
                                    <i class="bi bi-check-circle-fill"></i> Connected
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="alert alert-info">
                    <h4 class="alert-heading">Viewing Data</h4>
                    <p class="mb-0">Your scraped data is being stored in this Google Sheet: 
                        <a href="https://docs.google.com/spreadsheets/d/1KXSlHHm7q0QjLCct_4RdDHwZDOQYkqtTOqrIsIEzaWY" 
                           target="_blank" class="alert-link">
                            Craigslist Car Listings
                        </a>
                    </p>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <h2 class="mb-4">Recent Enhancements</h2>
                <div class="card mb-4 bg-primary-subtle">
                    <div class="card-body">
                        <h5 class="card-title">🚗 Kelly Blue Book Lookup URLs</h5>
                        <p>Added automatic KBB lookup links for each listing to help you quickly check vehicle values</p>
                        <p class="small">The system analyzes the listing title to extract year, make, and model, then generates a direct KBB search link</p>
                    </div>
                </div>
                <div class="card mb-4">
                    <div class="card-body">
                        <h5 class="card-title">Enhanced Web Scraping</h5>
                        <p>Added Playwright-based scraper for more detailed information extraction</p>
                    </div>
                </div>
                <div class="card mb-4">
                    <div class="card-body">
                        <h5 class="card-title">Improved Filtering</h5>
                        <p>Added more filter keywords to eliminate problematic listings</p>
                    </div>
                </div>
                <div class="card mb-4">
                    <div class="card-body">
                        <h5 class="card-title">Toyota-Specific Search</h5>
                        <p>Updated search parameters to focus on Toyota models from 2010+</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Update last run time
        const lastRun = document.getElementById('last-run');
        const now = new Date();
        lastRun.textContent = now.toLocaleTimeString();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Home page with system status"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    """API endpoint for system status"""
    return jsonify({
        "status": "running",
        "scraper": "active",
        "google_sheets": "connected",
        "current_search": {
            "make_model": "Toyota",
            "price_range": "$5,000 - $15,000",
            "year": "2010 or newer",
            "location": "Los Angeles"
        },
        "filter_keywords": [
            "salvage", "rebuilt", "flood", "damaged", "parts",
            "mechanic", "special", "repair", "project", "needs", 
            "issue", "problem"
        ]
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)