#!/bin/bash

# Update the workflows to use our database scripts
echo "Updating workflows..."

# Restart the workflows with our database-backed version
echo "Restarting workflows..."
replit workflow restart Start application
replit workflow restart craigslist_scraper