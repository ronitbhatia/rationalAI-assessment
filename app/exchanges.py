"""Utilities to detect exchange and ticker from text and external sources."""

import re
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

# Common exchange patterns
EXCHANGE_PATTERNS = {
    'NYSE': [r'NYSE[:\s]+([A-Z]{1,5})', r'New York Stock Exchange[:\s]+([A-Z]{1,5})'],
    'NASDAQ': [r'NASDAQ[:\s]+([A-Z]{1,5})', r'Nasdaq[:\s]+([A-Z]{1,5})'],
    'AMEX': [r'AMEX[:\s]+([A-Z]{1,5})', r'American Stock Exchange[:\s]+([A-Z]{1,5})'],
    'OTC': [r'OTC[:\s]+([A-Z]{1,5})', r'OTC Markets[:\s]+([A-Z]{1,5})'],
}

TICKER_PATTERN = re.compile(r'\b([A-Z]{1,5})\s*[:\-]?\s*(NYSE|NASDAQ|AMEX|OTC)', re.IGNORECASE)
STANDALONE_TICKER = re.compile(r'\b([A-Z]{1,5})\b')


def extract_ticker_from_text(text: str) -> Optional[str]:
    """
    Extract ticker symbol from text using pattern matching.
    
    Args:
        text: Raw text to search
        
    Returns:
        Ticker symbol if found, None otherwise
    """
    if not text:
        return None
    
    # Try pattern with exchange
    match = TICKER_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    
    # Try exchange-specific patterns
    for exchange, patterns in EXCHANGE_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
    
    return None


def extract_exchange_from_text(text: str) -> Optional[str]:
    """
    Extract exchange name from text.
    
    Args:
        text: Raw text to search
        
    Returns:
        Exchange name if found, None otherwise
    """
    if not text:
        return None
    
    text_upper = text.upper()
    
    if 'NYSE' in text_upper or 'NEW YORK STOCK EXCHANGE' in text_upper:
        return 'NYSE'
    elif 'NASDAQ' in text_upper:
        return 'NASDAQ'
    elif 'AMEX' in text_upper or 'AMERICAN STOCK EXCHANGE' in text_upper:
        return 'AMEX'
    elif 'OTC' in text_upper or 'OTC MARKETS' in text_upper:
        return 'OTC'
    
    return None


def lookup_ticker_wikipedia(company_name: str) -> Optional[Tuple[str, str]]:
    """
    Look up ticker and exchange from Wikipedia.
    
    Args:
        company_name: Name of the company
        
    Returns:
        Tuple of (ticker, exchange) if found, None otherwise
    """
    try:
        # Search Wikipedia - try direct article first
        encoded_name = company_name.replace(' ', '_')
        article_url = f"https://en.wikipedia.org/wiki/{quote(encoded_name, safe='')}"
        response = requests.get(article_url, timeout=10, allow_redirects=True)
        
        # If direct article not found (404 or redirect to search), try search
        if response.status_code != 200 or 'Special:Search' in response.url:
            search_url = "https://en.wikipedia.org/wiki/Special:Search"
            params = {'search': company_name, 'go': 'Go'}
            search_response = requests.get(search_url, params=params, timeout=10)
            
            if search_response.status_code == 200:
                # Try to find the main article URL from search results
                soup = BeautifulSoup(search_response.text, 'html.parser')
                first_result = soup.find('div', class_='mw-search-result-heading')
                if first_result:
                    link = first_result.find('a')
                    if link:
                        article_url = 'https://en.wikipedia.org' + link.get('href', '')
                        response = requests.get(article_url, timeout=10)
        
        if response.status_code == 200:
            article_soup = BeautifulSoup(response.text, 'html.parser')
            infobox = article_soup.find('table', class_='infobox')
            
            if infobox:
                text = infobox.get_text()
                exchange = extract_exchange_from_text(text)
                ticker = extract_ticker_from_text(text)
                
                if ticker and exchange:
                    return (ticker, exchange)
    
    except Exception as e:
        logger.debug(f"Wikipedia lookup failed for {company_name}: {e}")
    
    return None


def resolve_exchange_ticker(
    text_snippets: list[str],
    company_name: str,
    url: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve exchange and ticker from multiple sources.
    
    Args:
        text_snippets: List of text snippets to search
        company_name: Name of the company
        url: Optional company URL
        
    Returns:
        Tuple of (exchange, ticker) if found
    """
    # First, try to extract from provided snippets
    combined_text = ' '.join(text_snippets)
    exchange = extract_exchange_from_text(combined_text)
    ticker = extract_ticker_from_text(combined_text)
    
    if exchange and ticker:
        return (exchange, ticker)
    
    # If missing, try Wikipedia lookup
    if not ticker or not exchange:
        wiki_result = lookup_ticker_wikipedia(company_name)
        if wiki_result:
            ticker, exchange = wiki_result
            return (ticker, exchange)
    
    # Return what we have (might be partial)
    return (exchange, ticker)

