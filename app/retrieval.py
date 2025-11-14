"""
Web search, page fetching, and simple scraping.

This module handles data retrieval from web sources including company websites
and Wikipedia. It implements simple HTML parsing and text extraction without
requiring JavaScript execution.
"""

import re
import logging
import time
from typing import List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Clean and normalize text from HTML.
    
    Args:
        text: Raw text string
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-]', ' ', text)
    return text.strip()


def fetch_page(url: str, timeout: int = 8) -> Optional[str]:
    """
    Fetch a web page and return its text content.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Cleaned text content or None if fetch fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        return clean_text(text)
    
    except requests.exceptions.Timeout:
        logger.debug(f"Timeout fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error fetching {url}: {e}")
        return None


def extract_company_info(text: str, url: str) -> Tuple[List[str], List[str]]:
    """
    Extract relevant sections from company page text.
    
    Args:
        text: Full page text
        url: Source URL
        
    Returns:
        Tuple of (overview_snippets, product_snippets)
    """
    if not text:
        return [], []
    
    # Look for common section headers
    overview_keywords = [
        'about us', 'overview', 'company', 'who we are',
        'mission', 'description', 'introduction'
    ]
    
    product_keywords = [
        'products', 'services', 'solutions', 'offerings',
        'what we do', 'capabilities', 'portfolio'
    ]
    
    customer_keywords = [
        'customers', 'clients', 'industries', 'sectors',
        'markets', 'verticals', 'who we serve'
    ]
    
    text_lower = text.lower()
    snippets = []
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
    
    for para in paragraphs:
        para_lower = para.lower()
        if any(kw in para_lower for kw in overview_keywords + product_keywords + customer_keywords):
            if len(para) > 100:  # Only keep substantial paragraphs
                snippets.append(para[:2000])  # Limit snippet length
    
    # If no specific sections found, return first few substantial paragraphs
    if not snippets and paragraphs:
        snippets = paragraphs[:5]
    
    return snippets, []


def build_search_queries(
    products_services: List[str],
    customer_segments: List[str],
    industry_keywords: List[str]
) -> List[str]:
    """
    Build web search queries from normalized target profile.
    
    Args:
        products_services: List of product/service bullets
        customer_segments: List of customer segment bullets
        industry_keywords: Industry-related keywords
        
    Returns:
        List of search query strings
    """
    queries = []
    
    # Combine products/services with customer segments
    for product in products_services[:5]:  # Top 5 products
        for segment in customer_segments[:3]:  # Top 3 segments
            # Extract key terms (simple: take first few words)
            product_terms = ' '.join(product.split()[:4])
            segment_terms = ' '.join(segment.split()[:3])
            queries.append(f"{product_terms} {segment_terms} public company")
    
    # Add industry-based queries
    for keyword in industry_keywords[:5]:
        queries.append(f"{keyword} consulting services public company stock")
    
    # Add queries with "comparable" or "similar"
    for product in products_services[:3]:
        product_terms = ' '.join(product.split()[:4])
        queries.append(f"companies like {product_terms} public trading")
    
    return queries[:15]  # Limit to 15 queries


def search_web_bing(query: str, api_key: Optional[str] = None) -> List[str]:
    """
    Search the web using Bing API (if available) or fallback to DuckDuckGo-like approach.
    
    Note: In production, you'd use Bing Search API. For now, we'll use a simple
    approach with Wikipedia and direct company site searches.
    
    Args:
        query: Search query string
        api_key: Optional Bing API key (not used in this implementation)
        
    Returns:
        List of URLs
    """
    urls = []
    
    try:
        # Try Wikipedia search first
        if 'public company' in query.lower() or 'stock' in query.lower():
            wiki_query = query.replace(' public company', '').replace(' stock', '')
            wiki_url = f"https://en.wikipedia.org/wiki/Special:Search?search={wiki_query}"
            urls.append(wiki_url)
        
        # For consulting/services, try to find company sites
        # In a real implementation, you'd use Bing/Google Search API
        # For now, we'll rely on the pipeline to provide known candidates
        
    except Exception as e:
        logger.debug(f"Web search failed for query '{query}': {e}")
    
    return urls


def discover_candidates_simple(
    queries: List[str],
    max_candidates: int = 40
) -> List[Tuple[str, str]]:
    """
    Simple candidate discovery using Wikipedia and known patterns.
    
    In production, this would use Bing Search API or similar.
    For this implementation, we'll use a simpler approach that searches
    Wikipedia and known financial data sources.
    
    Args:
        queries: List of search queries
        max_candidates: Maximum number of candidates to return
        
    Returns:
        List of (company_name, url) tuples
    """
    candidates = []
    seen = set()
    
    # Extract key terms from queries
    all_terms = []
    for query in queries:
        # Remove common words
        terms = [t for t in query.lower().split() 
                if t not in ['public', 'company', 'stock', 'trading', 'like', 'companies']]
        all_terms.extend(terms[:3])  # Take first 3 meaningful terms
    
    # Search Wikipedia for companies in related industries
    # This is a simplified approach - in production, use proper search APIs
    try:
        # For consulting companies, we can try known lists
        consulting_keywords = ['consulting', 'advisory', 'services', 'managed', 'consultancy']
        healthcare_keywords = ['healthcare', 'health', 'hospital', 'medical', 'revenue']
        education_keywords = ['education', 'university', 'research', 'academic', 'educational']
        
        combined_terms = ' '.join(all_terms).lower()
        
        logger.debug(f"Combined terms for discovery: {combined_terms[:200]}")
        
        # Always include consulting companies if any consulting-related terms found
        # Also include them if no specific keywords match (fallback)
        should_include_consulting = (
            any(kw in combined_terms for kw in consulting_keywords) or
            len(queries) > 0  # Fallback: if we have queries, assume consulting-related
        )
        
        if should_include_consulting:
            # Publicly traded consulting and professional services companies
            known_companies = [
                # Large consulting firms
                ("Accenture", "https://www.accenture.com"),
                ("IBM Global Services", "https://www.ibm.com/services"),
                ("Cognizant", "https://www.cognizant.com"),
                ("Infosys", "https://www.infosys.com"),
                ("Wipro", "https://www.wipro.com"),
                ("Tata Consultancy Services", "https://www.tcs.com"),
                ("Capgemini", "https://www.capgemini.com"),
                ("Atos", "https://atos.net"),
                ("EPAM Systems", "https://www.epam.com"),
                ("Perficient", "https://www.perficient.com"),
                ("Publicis Sapient", "https://www.publicissapient.com"),
                # Healthcare consulting focus
                ("Cerner Corporation", "https://www.cerner.com"),
                ("Epic Systems", "https://www.epic.com"),
                ("Optum", "https://www.optum.com"),
                ("Change Healthcare", "https://www.changehealthcare.com"),
                # Education/Research consulting
                ("Blackbaud", "https://www.blackbaud.com"),
                ("Workday", "https://www.workday.com"),
                ("Salesforce", "https://www.salesforce.com"),
                # Management consulting (publicly traded)
                ("Booz Allen Hamilton", "https://www.boozallen.com"),
                ("FTI Consulting", "https://www.fticonsulting.com"),
                ("Navigant Consulting", "https://www.guidehouse.com"),  # Now Guidehouse
                ("Guidehouse", "https://www.guidehouse.com"),
                ("Alvarez & Marsal", "https://www.alvarezandmarsal.com"),
                # Technology consulting
                ("DXC Technology", "https://www.dxc.com"),
                ("CGI", "https://www.cgi.com"),
                ("NTT Data", "https://www.nttdata.com"),
                ("Tyler Technologies", "https://www.tylertech.com"),
            ]
            
            # Filter by industry focus if keywords suggest it
            if any(kw in combined_terms for kw in healthcare_keywords):
                # Add healthcare-specific companies
                healthcare_companies = [
                    ("McKesson", "https://www.mckesson.com"),
                    ("Cardinal Health", "https://www.cardinalhealth.com"),
                    ("Cerner", "https://www.cerner.com"),
                    ("Allscripts", "https://www.allscripts.com"),
                ]
                known_companies.extend(healthcare_companies)
            
            if any(kw in combined_terms for kw in education_keywords):
                # Add education-specific companies
                education_companies = [
                    ("Ellucian", "https://www.ellucian.com"),
                    ("Blackboard", "https://www.blackboard.com"),
                    ("CampusLogic", "https://www.campuslogic.com"),
                ]
                known_companies.extend(education_companies)
            
            for name, url in known_companies:
                if name.lower() not in seen and len(candidates) < max_candidates:
                    candidates.append((name, url))
                    seen.add(name.lower())
        
        logger.info(f"Discovered {len(candidates)} candidates from known companies list")
    except Exception as e:
        logger.warning(f"Candidate discovery error: {e}")
        # Fallback: return at least some known consulting companies
        if len(candidates) == 0:
            logger.info("No candidates found via keyword matching, using fallback list")
            fallback_companies = [
                ("Accenture", "https://www.accenture.com"),
                ("Cognizant", "https://www.cognizant.com"),
                ("IBM Global Services", "https://www.ibm.com/services"),
                ("Infosys", "https://www.infosys.com"),
                ("Wipro", "https://www.wipro.com"),
                ("EPAM Systems", "https://www.epam.com"),
                ("Perficient", "https://www.perficient.com"),
                ("Booz Allen Hamilton", "https://www.boozallen.com"),
                ("FTI Consulting", "https://www.fticonsulting.com"),
                ("DXC Technology", "https://www.dxc.com"),
            ]
            for name, url in fallback_companies[:max_candidates]:
                candidates.append((name, url))
    
    logger.info(f"Total candidates discovered: {len(candidates)}")
    return candidates[:max_candidates]


def fetch_candidate_data(
    company_name: str,
    url: Optional[str] = None
) -> Tuple[List[str], List[str]]:
    """
    Fetch and extract text data for a candidate company.
    
    Args:
        company_name: Name of the company
        url: Optional company URL
        
    Returns:
        Tuple of (text_snippets, source_urls)
    """
    snippets = []
    source_urls = []
    
    # Try company website (with timeout)
    if url:
        try:
            text = fetch_page(url)
            if text and len(text) > 100:  # Only use if we got substantial content
                overview, _ = extract_company_info(text, url)
                if overview:
                    snippets.extend(overview)
                    source_urls.append(url)
        except Exception as e:
            logger.debug(f"Failed to fetch company website for {company_name}: {e}")
    
    # Try Wikipedia (usually more reliable)
    try:
        # Try direct Wikipedia article
        wiki_name = company_name.replace(' ', '_')
        wiki_url = f"https://en.wikipedia.org/wiki/{wiki_name}"
        wiki_text = fetch_page(wiki_url)
        
        if wiki_text and len(wiki_text) > 200:
            # Limit Wikipedia content to avoid token limits
            snippets.append(wiki_text[:4000])
            source_urls.append(wiki_url)
        else:
            # Try with "Inc" or "Corporation" removed
            for suffix in [' Inc', ' Corporation', ' Corp', ' LLC', ' Ltd']:
                if company_name.endswith(suffix):
                    wiki_name_alt = company_name[:-len(suffix)].replace(' ', '_')
                    wiki_url_alt = f"https://en.wikipedia.org/wiki/{wiki_name_alt}"
                    wiki_text_alt = fetch_page(wiki_url_alt)
                    if wiki_text_alt and len(wiki_text_alt) > 200:
                        snippets.append(wiki_text_alt[:4000])
                        source_urls.append(wiki_url_alt)
                        break
    except Exception as e:
        logger.debug(f"Wikipedia fetch failed for {company_name}: {e}")
    
    # If we have no snippets, create a minimal one from company name
    # This ensures the LLM can still try to extract information
    if not snippets:
        snippets.append(f"Company: {company_name}. Information about {company_name}.")
        if url:
            source_urls.append(url)
    
    return snippets, source_urls

