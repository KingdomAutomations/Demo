"""
Utility functions for the Craigslist scraper.
"""
import re
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def clean_price(price_text: str) -> Optional[str]:
    """
    Clean price text by extracting the numeric value.
    
    Args:
        price_text: Raw price text from Craigslist (e.g. "$4,500")
        
    Returns:
        Cleaned price as a string or None if invalid
    """
    try:
        # Handle None or empty input
        if not price_text:
            return None
            
        # Convert to string if it's not already
        if not isinstance(price_text, str):
            price_text = str(price_text)
            
        # Extract digits from the price text
        digits = re.sub(r'[^\d]', '', price_text)
        
        if not digits:
            return None
            
        return digits
    except Exception as e:
        logger.error(f"Error cleaning price text: {str(e)}, input was: {price_text}")
        return None

def parse_posting_time(time_string: str) -> str:
    """
    Parse the posting time from Craigslist's datetime format.
    
    Args:
        time_string: ISO format datetime string from Craigslist
        
    Returns:
        Formatted date and time string (YYYY-MM-DD HH:MM:SS)
    """
    try:
        # Handle None or empty values
        if not time_string:
            return "N/A"
        
        # Remove any timezone suffix to avoid parsing errors
        if '+' in time_string:
            time_string = time_string.split('+')[0]
        
        # Handle various date formats
        try:
            # Try standard ISO format with 'T' separator (e.g. "2023-04-08T12:30:00")
            if 'T' in time_string:
                dt = datetime.fromisoformat(time_string)
            
            # Try ISO format without 'T' separator (e.g. "2023-04-08 12:30:00")
            elif '-' in time_string and ':' in time_string:
                dt = datetime.fromisoformat(time_string)
            
            # Try MM/DD/YYYY format variations
            elif '/' in time_string:
                time_formats = [
                    "%m/%d/%Y",
                    "%m/%d/%Y %H:%M",
                    "%m/%d/%y",
                    "%m/%d/%y %H:%M"
                ]
                
                for fmt in time_formats:
                    try:
                        dt = datetime.strptime(time_string, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # If no format matched, raise error to try next method
                    raise ValueError("No MM/DD/YYYY format matched")
            
            # Try text month formats like "Apr 8" or "April 8, 2023"
            else:
                time_formats = [
                    "%b %d",
                    "%B %d",
                    "%b %d, %Y",
                    "%B %d, %Y",
                    "%b %d, %Y %H:%M",
                    "%B %d, %Y %H:%M",
                    "%b %d %H:%M",
                    "%B %d %H:%M"
                ]
                
                for fmt in time_formats:
                    try:
                        # If year is missing, use current year
                        parsed_dt = datetime.strptime(time_string, fmt)
                        if "/%Y" not in fmt and ", %Y" not in fmt:
                            current_year = datetime.now().year
                            dt = parsed_dt.replace(year=current_year)
                        else:
                            dt = parsed_dt
                        break
                    except ValueError:
                        continue
                else:
                    # If we got here, no format matched
                    return time_string  # Return original as a last resort
            
            # Format as a sortable string (YYYY-MM-DD HH:MM:SS)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            return formatted_time
            
        except Exception as inner_e:
            logger.debug(f"Detailed parsing error: {str(inner_e)}")
            # Return the original string if all parsing methods fail
            return time_string
            
    except Exception as e:
        logger.error(f"Error parsing posting time: {str(e)}, input was: {time_string}")
        # Return the original string if parsing fails
        return str(time_string)
