"""
Craigslist scraper module to extract car listings from Craigslist.
"""
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
from typing import List, Dict, Set
from utils import clean_price, parse_posting_time

logger = logging.getLogger(__name__)

def scrape_craigslist(url: str, existing_urls: Set[str], filter_keywords: List[str]) -> List[Dict[str, any]]:
    """
    Scrape Craigslist for car listings.
    
    Args:
        url: The Craigslist search URL to scrape
        existing_urls: Set of URLs already in the Google Sheet (to avoid duplicates)
        filter_keywords: List of keywords to filter out (e.g. "salvage")
        
    Returns:
        List of dictionaries containing listing information
    """
    logger.info(f"Scraping Craigslist: {url}")
    
    listings = []
    
    try:
        # Add a random delay to avoid being detected as a bot
        time.sleep(random.uniform(1, 3))
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://craigslist.org/'
        }
        
        # Request the page
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch URL: {url}, Status code: {response.status_code}")
            return listings
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all listing elements - try different selectors for newer Craigslist layouts
        # Clear the listings list first
        listings = []
        results = []
        
        # Try the classic selector
        results = soup.select('.result-info')
        
        # If no results found, try alternative selectors for newer Craigslist layout
        if not results:
            logger.info("No results found with classic selector, trying alternative selectors")
            results = soup.select('li.cl-static-search-result')
            if results:
                logger.info(f"Found {len(results)} listings with new selector")
                # Print the first listing HTML for debugging
                if len(results) > 0:
                    logger.debug(f"Sample listing HTML: {results[0]}")
        
        # Debug the HTML output if no results found
        if not results:
            logger.info("No listings found with any selectors, dumping sample HTML for analysis")
            sample_html = response.text[:500] + "..." if len(response.text) > 500 else response.text
            logger.debug(f"Sample HTML: {sample_html}")
            
        # Current time for timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for result in results:
            try:
                # Extract data from the listing depending on the layout
                title = None
                url = None
                
                # Try classic layout first
                title_element = result.select_one('.result-title, .titlestring')
                
                # If not found, try newer layout elements
                if not title_element:
                    title_element = result.select_one('div.title a, a.posting-title')
                
                # If still not found, try direct div.title
                if not title_element:
                    title_div = result.select_one('div.title')
                    if title_div:
                        title = title_div.text.strip()
                        # For the newer layout, the parent <a> contains the href
                        parent_link = result.find('a')
                        if parent_link and parent_link.get('href'):
                            url = parent_link.get('href')
                
                # If we found a title_element, extract title and url from it
                if title_element:
                    title = title_element.text.strip()
                    url_attr = title_element.get('href')
                    if url_attr and isinstance(url_attr, str):
                        url = url_attr
                
                # If we still don't have a title or url, debug and skip
                if not title or not url:
                    logger.debug(f"Couldn't extract title/url from result: {result}")
                    continue
                    
                # Skip if URL already exists in our database
                if url in existing_urls:
                    continue
                
                # Skip if title contains any of the filter keywords (case-insensitive)
                if any(keyword.lower() in title.lower() for keyword in filter_keywords):
                    logger.info(f"Filtered out listing: '{title}' (contains filter keyword)")
                    continue
                
                # Extract price - try different selectors based on layout
                price_element = result.select_one('.result-price, .price, span.priceinfo')
                price = clean_price(price_element.text) if price_element else None
                
                # Extract location - try different selectors
                location_element = result.select_one('.result-hood, .location, .housing')
                location = location_element.text.strip('()') if location_element else "N/A"
                
                # Extract posting time from the individual listing page
                # This is more accurate than relying on the search results page
                posting_time = "N/A"
                try:
                    # Add a small delay to avoid hitting the server too hard
                    time.sleep(random.uniform(0.2, 0.5))
                    
                    # Visit the individual listing page to get the exact posting time
                    logger.debug(f"Visiting individual listing page: {url}")
                    listing_response = requests.get(url, headers=headers, timeout=10)
                    
                    if listing_response.status_code == 200:
                        listing_soup = BeautifulSoup(listing_response.text, 'html.parser')
                        
                        # Look for the posting time in the individual listing page
                        # Try different selectors for the posting date/time
                        posting_info = listing_soup.select_one('p.postinginfo time, .date.timeago')
                        
                        if posting_info and hasattr(posting_info, 'get') and posting_info.get('datetime'):
                            datetime_value = posting_info.get('datetime')
                            if isinstance(datetime_value, str):
                                posting_time = parse_posting_time(datetime_value)
                                logger.debug(f"Found posting time: {posting_time}")
                        else:
                            # As a backup, look for any element with a datetime attribute
                            time_elements = listing_soup.find_all('time')
                            for time_elem in time_elements:
                                if hasattr(time_elem, 'get') and time_elem.get('datetime'):
                                    datetime_value = time_elem.get('datetime')
                                    if isinstance(datetime_value, str):
                                        posting_time = parse_posting_time(datetime_value)
                                        logger.debug(f"Found posting time from alternate source: {posting_time}")
                                        break
                    else:
                        logger.warning(f"Failed to fetch individual listing page: {url}, Status code: {listing_response.status_code}")
                except Exception as e:
                    logger.warning(f"Error getting posting time from individual listing: {str(e)}")
                
                # If we still don't have a posting time, fall back to current date
                if posting_time == "N/A":
                    posting_time = datetime.now().strftime("%Y-%m-%d")
                    logger.debug(f"Using fallback posting time: {posting_time}")
                
                # Create a dictionary for the listing
                listing = {
                    'title': title,
                    'price': price,
                    'url': url,
                    'location': location,
                    'posting_time': posting_time,
                    'scraped_at': current_time
                }
                
                listings.append(listing)
                
            except Exception as e:
                logger.error(f"Error processing listing: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error scraping Craigslist: {str(e)}", exc_info=True)
    
    logger.info(f"Scraped {len(listings)} new listings")
    return listings
