"""
This module creates a simple Flask web server to keep the Replit instance alive.
"""
from flask import Flask
from threading import Thread
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    """Simple route to respond to pings."""
    return "Craigslist Scraper is running!"

def run():
    """Run the Flask web server on port 8080."""
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Start the Flask server in a separate thread."""
    try:
        logger.info("Starting keep-alive server")
        server_thread = Thread(target=run)
        server_thread.daemon = True
        server_thread.start()
        logger.info("Keep-alive server started")
    except Exception as e:
        logger.error(f"Error starting keep-alive server: {str(e)}", exc_info=True)
