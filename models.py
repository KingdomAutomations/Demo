"""
Database models for the Craigslist car listings.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.sql import func

db = SQLAlchemy()

class CarListing(db.Model):
    """Model for car listings scraped from Craigslist"""
    __tablename__ = 'car_listings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(50))
    url = db.Column(db.String(255), unique=True, nullable=False)
    location = db.Column(db.String(255))
    posting_time = db.Column(db.DateTime)
    scraped_at = db.Column(db.DateTime)
    added_at = db.Column(db.DateTime, server_default=func.now())
    
    # Additional fields for enhanced data
    description = db.Column(TEXT)
    vin = db.Column(db.String(50))
    year = db.Column(db.Integer)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    odometer = db.Column(db.Integer)
    
    # Market value related fields
    market_value = db.Column(db.Float)
    market_value_source = db.Column(db.String(100))
    market_value_updated_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<CarListing {self.id}: {self.title} - ${self.price}>"

class MarketAnalysis(db.Model):
    """Model for market analysis of car listings"""
    __tablename__ = 'market_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year_from = db.Column(db.Integer)
    year_to = db.Column(db.Integer)
    avg_price = db.Column(db.Float)
    median_price = db.Column(db.Float)
    min_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    sample_size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<MarketAnalysis {self.make} {self.model} ({self.year_from}-{self.year_to})>"