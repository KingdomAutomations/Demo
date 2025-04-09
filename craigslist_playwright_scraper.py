"""
Enhanced Craigslist scraper using Playwright for more detailed extraction.
This module allows for browser-based scraping to get more information from listings.
"""
import asyncio
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime
import random
import time
from playwright.async_api import async_playwright, Page

from utils import parse_posting_time, clean_price

logger = logging.getLogger(__name__)

async def scrape_craigslist_with_playwright(url: str, existing_urls: Set[str], filter_keywords: List[str]) -> List[Dict[str, any]]:
    """
    Scrape Craigslist using Playwright for more detailed information.
    
    Args:
        url: The Craigslist search URL to scrape
        existing_urls: Set of URLs already in the Google Sheet (to avoid duplicates)
        filter_keywords: List of keywords to filter out (e.g. "salvage")
        
    Returns:
        List of dictionaries containing detailed listing information
    """
    logger.info(f"Scraping Craigslist with Playwright: {url}")
    
    listings = []
    
    async with async_playwright() as p:
        # Launch the browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        try:
            # Create a new page
            page = await context.new_page()
            
            # Navigate to the URL
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for the page to load
            await page.wait_for_load_state("networkidle")
            
            # Current time for timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get all listing URLs
            listings_results = await page.query_selector_all('li.cl-static-search-result')
            
            if not listings_results:
                logger.warning("No listings found with Playwright")
                return listings
                
            logger.info(f"Found {len(listings_results)} listings with Playwright")
            
            # Process only a subset of listings if there are many (to avoid timeouts)
            max_listings = min(50, len(listings_results))
            
            # Process each listing
            for i in range(max_listings):
                try:
                    # Get the listing element
                    listing_element = listings_results[i]
                    
                    # Get the link element
                    link_element = await listing_element.query_selector('a')
                    if not link_element:
                        continue
                        
                    # Get the URL
                    url_attr = await link_element.get_attribute('href')
                    if not url_attr:
                        continue
                        
                    url = url_attr
                    
                    # Skip if URL already exists in our database
                    if url in existing_urls:
                        continue
                    
                    # Get the title
                    title_element = await listing_element.query_selector('div.title')
                    title = await title_element.text_content() if title_element else "N/A"
                    
                    # Skip if title contains any of the filter keywords (case-insensitive)
                    if any(keyword.lower() in title.lower() for keyword in filter_keywords):
                        logger.info(f"Filtered out listing: '{title}' (contains filter keyword)")
                        continue
                    
                    # Get the price
                    price_element = await listing_element.query_selector('div.price')
                    price_text = await price_element.text_content() if price_element else "N/A"
                    price = clean_price(price_text)
                    
                    # Get the location
                    location_element = await listing_element.query_selector('div.location')
                    location = await location_element.text_content() if location_element else "N/A"
                    
                    # Visit the individual listing to get more details
                    listing_page = await context.new_page()
                    
                    # Add a small delay to avoid hitting the server too hard
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    # Navigate to the listing page
                    logger.debug(f"Visiting individual listing page: {url}")
                    await listing_page.goto(url, wait_until="domcontentloaded")
                    await listing_page.wait_for_load_state("networkidle")
                    
                    # Extract posting time
                    posting_time = "N/A"
                    posting_info = await listing_page.query_selector('p.postinginfo time, .date.timeago')
                    
                    if posting_info:
                        datetime_value = await posting_info.get_attribute('datetime')
                        if datetime_value:
                            posting_time = parse_posting_time(datetime_value)
                            logger.debug(f"Found posting time: {posting_time}")
                    
                    # If no posting time found, look for any time element
                    if posting_time == "N/A":
                        time_elements = await listing_page.query_selector_all('time')
                        for time_elem in time_elements:
                            datetime_value = await time_elem.get_attribute('datetime')
                            if datetime_value:
                                posting_time = parse_posting_time(datetime_value)
                                logger.debug(f"Found posting time from alternate source: {posting_time}")
                                break
                    
                    # If still no posting time, use current date
                    if posting_time == "N/A":
                        posting_time = datetime.now().strftime("%Y-%m-%d")
                        logger.debug(f"Using fallback posting time: {posting_time}")
                    
                    # Extract additional details (optional)
                    details_section = await listing_page.query_selector('.mapAndAttrs')
                    additional_details = {}
                    
                    # Get all attribute groups
                    if details_section:
                        attr_groups = await details_section.query_selector_all('.attrgroup')
                        for group in attr_groups:
                            spans = await group.query_selector_all('span')
                            for span in spans:
                                attr_text = await span.text_content()
                                if ':' in attr_text:
                                    key, value = attr_text.split(':', 1)
                                    additional_details[key.strip()] = value.strip()
                                elif attr_text.strip():
                                    # For attributes without keys (like features)
                                    additional_details[f"feature_{len(additional_details)}"] = attr_text.strip()
                    
                    # Create a dictionary for the listing
                    listing = {
                        'title': title,
                        'price': price,
                        'url': url,
                        'location': location,
                        'posting_time': posting_time,
                        'scraped_at': current_time,
                        'additional_details': additional_details
                    }
                    
                    # Add to our list
                    listings.append(listing)
                    
                    # Close the listing page to free resources
                    await listing_page.close()
                    
                except Exception as e:
                    logger.error(f"Error processing listing: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping Craigslist with Playwright: {str(e)}", exc_info=True)
        
        finally:
            # Close the browser
            await browser.close()
    
    logger.info(f"Scraped {len(listings)} new listings with Playwright")
    return listings

# For direct testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test URL
    test_url = "https://losangeles.craigslist.org/search/cta?min_price=1000&max_price=10000"
    
    # Run the scraper
    asyncio.run(scrape_craigslist_with_playwright(
        test_url, 
        set(),  # Empty set of existing URLs
        ["salvage", "rebuilt", "flood", "damaged", "parts"]  # Filter keywords
    ))