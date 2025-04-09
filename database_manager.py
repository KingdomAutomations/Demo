"""
Database manager module to handle interactions with the PostgreSQL database.
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Set, Optional
import re
from sqlalchemy import func, desc, asc
from dotenv import load_dotenv

from models import db, CarListing, MarketAnalysis

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages interactions with the PostgreSQL database for storing Craigslist listings"""
    
    def __init__(self, app=None):
        """Initialize the DatabaseManager with Flask app (if provided)"""
        self.app = app
        # We don't need to initialize the app here since it's done in app_db.py
    
    def get_existing_urls(self) -> Set[str]:
        """
        Get a set of all URLs already in the database to avoid duplicates
        
        Returns:
            Set of URLs already in the database
        """
        try:
            urls = db.session.query(CarListing.url).all()
            return {url[0] for url in urls}
        except Exception as e:
            logger.error(f"Error getting existing URLs: {str(e)}", exc_info=True)
            return set()
    
    def add_listings(self, listings: List[Dict]) -> None:
        """
        Add new listings to the database
        
        Args:
            listings: List of listing dictionaries to add to the database
        """
        if not listings:
            logger.info("No listings to add")
            return
            
        try:
            listings_added = 0
            
            for listing_data in listings:
                # Extract basic listing info
                title = listing_data.get('title', '')
                price = listing_data.get('price', '')
                url = listing_data.get('url', '')
                location = listing_data.get('location', '')
                
                # Skip if URL is missing (shouldn't happen but just in case)
                if not url:
                    continue
                
                # Check if listing with this URL already exists
                existing = CarListing.query.filter_by(url=url).first()
                if existing:
                    continue
                
                # Parse posting time
                posting_time = None
                if listing_data.get('posting_time'):
                    try:
                        posting_time_str = listing_data.get('posting_time')
                        if posting_time_str != 'N/A':
                            posting_time = datetime.strptime(posting_time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass  # Invalid date format
                
                # Parse year, make, and model from the title
                year = self._extract_year(title)
                make = self._extract_make(title)
                model = self._extract_model(title, make)
                
                # Create the listing
                scraped_at = None
                if listing_data.get('scraped_at'):
                    try:
                        scraped_at_str = listing_data.get('scraped_at')
                        if scraped_at_str != 'N/A':
                            scraped_at = datetime.strptime(scraped_at_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        scraped_at = datetime.now()
                        
                if not scraped_at:
                    scraped_at = datetime.now()
                
                # Create new listing
                new_listing = CarListing(
                    title=title,
                    price=price,
                    url=url,
                    location=location,
                    posting_time=posting_time,
                    scraped_at=scraped_at,
                    year=year,
                    make=make,
                    model=model
                )
                
                # Add to database
                db.session.add(new_listing)
                listings_added += 1
            
            # Commit all changes
            db.session.commit()
            logger.info(f"Added {listings_added} new listings to database")
            
        except Exception as e:
            logger.error(f"Error adding listings to database: {str(e)}", exc_info=True)
            db.session.rollback()
    
    def update_market_analysis(self):
        """
        Update market analysis data by calculating stats for different make/model combinations
        """
        try:
            # Get all distinct make/model combinations with at least 3 listings
            query = db.session.query(
                CarListing.make,
                CarListing.model,
                func.count(CarListing.id).label('count')
            ).group_by(
                CarListing.make, 
                CarListing.model
            ).having(
                func.count(CarListing.id) >= 3
            )
            
            make_model_counts = query.all()
            
            for make, model, count in make_model_counts:
                # Skip if make or model is missing
                if not make or not model:
                    continue
                
                # Get price statistics (converting text prices to numeric)
                listings = CarListing.query.filter(
                    CarListing.make == make,
                    CarListing.model == model,
                    CarListing.price.isnot(None)
                ).all()
                
                # Parse prices to float (stripping $ and ,)
                prices = []
                for listing in listings:
                    try:
                        price_str = listing.price.replace('$', '').replace(',', '')
                        price = float(price_str)
                        prices.append(price)
                    except (ValueError, AttributeError):
                        pass
                
                if len(prices) < 3:
                    continue  # Not enough valid prices
                
                # Calculate statistics
                avg_price = sum(prices) / len(prices)
                median_price = sorted(prices)[len(prices) // 2]
                min_price = min(prices)
                max_price = max(prices)
                
                # Get year range
                years = [listing.year for listing in listings if listing.year]
                if years:
                    year_from = min(years)
                    year_to = max(years)
                else:
                    year_from = None
                    year_to = None
                
                # Check if analysis already exists
                existing = MarketAnalysis.query.filter_by(
                    make=make,
                    model=model
                ).first()
                
                if existing:
                    # Update existing analysis
                    existing.avg_price = avg_price
                    existing.median_price = median_price
                    existing.min_price = min_price
                    existing.max_price = max_price
                    existing.sample_size = len(prices)
                    existing.year_from = year_from
                    existing.year_to = year_to
                    existing.created_at = datetime.now()
                else:
                    # Create new analysis
                    new_analysis = MarketAnalysis(
                        make=make,
                        model=model,
                        avg_price=avg_price,
                        median_price=median_price,
                        min_price=min_price,
                        max_price=max_price,
                        sample_size=len(prices),
                        year_from=year_from,
                        year_to=year_to
                    )
                    db.session.add(new_analysis)
            
            # Commit all changes
            db.session.commit()
            logger.info("Updated market analysis data")
            
        except Exception as e:
            logger.error(f"Error updating market analysis: {str(e)}", exc_info=True)
            db.session.rollback()
    
    def get_market_analysis(self, make=None, model=None):
        """
        Get market analysis data, optionally filtered by make and model
        
        Args:
            make: Optional car make to filter by
            model: Optional car model to filter by (only used if make is provided)
            
        Returns:
            List of market analysis dictionaries
        """
        try:
            query = MarketAnalysis.query
            
            if make:
                query = query.filter(MarketAnalysis.make.ilike(f"%{make}%"))
                if model:
                    query = query.filter(MarketAnalysis.model.ilike(f"%{model}%"))
            
            analyses = query.order_by(
                MarketAnalysis.make,
                MarketAnalysis.model
            ).all()
            
            return [
                {
                    'make': a.make,
                    'model': a.model,
                    'year_range': f"{a.year_from}-{a.year_to}" if a.year_from and a.year_to else "N/A",
                    'avg_price': f"${a.avg_price:.2f}",
                    'median_price': f"${a.median_price:.2f}",
                    'price_range': f"${a.min_price:.2f} - ${a.max_price:.2f}",
                    'sample_size': a.sample_size,
                    'updated_at': a.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
                for a in analyses
            ]
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {str(e)}", exc_info=True)
            return []
    
    def _extract_year(self, title: str) -> Optional[int]:
        """Extract the car year from the listing title"""
        match = re.search(r'\b(19[7-9][0-9]|20[0-2][0-9])\b', title)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None
    
    def _extract_make(self, title: str) -> Optional[str]:
        """Extract the car make from the listing title"""
        common_makes = [
            "Toyota", "Honda", "Ford", "Chevrolet", "Chevy", "Nissan", "Hyundai", 
            "Kia", "Mazda", "Subaru", "Volkswagen", "VW", "Jeep", "BMW", 
            "Mercedes", "Lexus", "Acura", "Audi"
        ]
        
        title_lower = title.lower()
        for make in common_makes:
            if make.lower() in title_lower:
                # Normalize some makes
                if make.lower() == "chevy":
                    return "Chevrolet"
                if make.lower() == "vw":
                    return "Volkswagen"
                return make
        
        return None
    
    def _extract_model(self, title: str, make: Optional[str]) -> Optional[str]:
        """Extract the car model from the listing title"""
        if not make:
            return None
            
        title_lower = title.lower()
        make_lower = make.lower()
        
        # Dictionary of common models for each make
        model_dict = {
            "toyota": ["corolla", "camry", "rav4", "highlander", "4runner", "tacoma", "tundra", "prius", "sienna"],
            "honda": ["civic", "accord", "cr-v", "pilot", "odyssey", "fit", "hr-v"],
            "ford": ["f-150", "f150", "escape", "explorer", "focus", "fusion", "mustang"],
            "chevrolet": ["silverado", "equinox", "tahoe", "malibu", "suburban", "colorado", "camaro"],
            "nissan": ["altima", "rogue", "sentra", "murano", "pathfinder", "frontier", "maxima"],
            "hyundai": ["elantra", "sonata", "tucson", "santa fe", "kona", "palisade"],
            "kia": ["forte", "optima", "sorento", "sportage", "telluride", "soul"],
            "mazda": ["mazda3", "mazda6", "cx-5", "cx-9", "mx-5", "miata"],
            "subaru": ["outback", "forester", "impreza", "crosstrek", "legacy", "ascent"],
            "volkswagen": ["jetta", "passat", "tiguan", "atlas", "golf", "beetle"],
            "jeep": ["wrangler", "grand cherokee", "cherokee", "compass", "renegade"],
            "bmw": ["3 series", "5 series", "x3", "x5", "328i", "530i", "m3", "m5"],
            "mercedes": ["c-class", "e-class", "s-class", "gla", "glc", "gle"],
            "lexus": ["rx", "es", "nx", "is", "gx", "lx", "rc"],
            "acura": ["mdx", "rdx", "tlx", "ilx", "rlx"],
            "audi": ["a4", "a6", "q5", "q7", "a3", "tt", "r8"]
        }
        
        # Check for each model of the corresponding make
        if make_lower in model_dict:
            for model in model_dict[make_lower]:
                if model.lower() in title_lower:
                    return model.title()  # Return with title case
        
        # If no model found, try to extract model from text after make
        try:
            make_index = title_lower.find(make_lower)
            if make_index >= 0:
                after_make = title_lower[make_index + len(make_lower):].strip()
                # Get first word after make as potential model
                model_candidate = after_make.split()[0].strip()
                if model_candidate and len(model_candidate) > 1:
                    return model_candidate.title()
        except (IndexError, ValueError):
            pass
            
        return None