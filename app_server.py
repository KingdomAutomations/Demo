"""
This script is a wrapper for the main Flask app to be used with Gunicorn.
"""
try:
    # First try the database-backed app
    from app_db import app
except ImportError:
    try:
        # Fall back to the original app
        from app import app
    except ImportError:
        # Fall back to the simple web app if neither is available
        from simple_web_app import app

# This file is imported by Gunicorn using the command:
# gunicorn --bind 0.0.0.0:5000 --reuse-port --reload app_server:app