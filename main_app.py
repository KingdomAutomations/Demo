"""
Main entry point for the Flask web application.
This file is used by Gunicorn to run the web server.
"""
from app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)