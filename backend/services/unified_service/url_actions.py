import logging
import re
from typing import Dict, List
from urllib.parse import urlparse

class URLActions:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client
        logging.info("[URL_ACTIONS] Initialized")

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        parsed = urlparse(url)
        domain = parsed.netloc
        domain = re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
        domain = domain.strip('_')
        if not domain:
            domain = 'default_domain'
        return domain

    def _get_page_path_from_url(self, url: str) -> str:
        """Extract page path from URL."""
        parsed = urlparse(url)
        return parsed.path or "/"

    def _check_embedding_exists(self, domain: str, url: str) -> bool:
        """Check if embeddings already exist for the given domain and URL."""
        try:
            collection = self.chroma_client.get_collection(name=domain)
            results = collection.get(
                where={"url": url},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception as e:
            logging.debug(f"Error checking embeddings for domain {domain}: {str(e)}")
            return False

    def _get_existing_pages(self, domain: str) -> List[Dict]:
        """Get list of existing pages for a domain."""
        try:
            collection = self.chroma_client.get_collection(name=domain)
            results = collection.get(
                include=['metadatas', 'documents']
            )
            
            pages = []
            for i, metadata in enumerate(results['metadatas']):
                if metadata and 'url' in metadata:
                    pages.append({
                        'url': metadata['url'],
                        'path': self._get_page_path_from_url(metadata['url']),
                        'title': metadata.get('title', 'Unknown'),
                        'created_at': metadata.get('created_at', 'Unknown')
                    })
            
            return pages
        except Exception as e:
            logging.debug(f"Error getting existing pages for domain {domain}: {str(e)}")
            return []

    def extract_url(self, parameters: Dict) -> Dict:
        """Extract URL from parameters or user message."""
        logging.info(f"Extract URL called with parameters: {parameters}")
        url = parameters.get("url")
        logging.info(f"Extracted URL from parameters: {url}")
        
        if url:
            logging.info(f"URL extracted: {url}")
            
            # Get domain and check existing pages
            domain = self._get_domain_from_url(url)
            page_path = self._get_page_path_from_url(url)
            embeddings_exist = self._check_embedding_exists(domain, url)
            existing_pages = self._get_existing_pages(domain)
            
            # Check if this specific page exists
            current_page_exists = any(page['url'] == url for page in existing_pages)
            
            result = {
                "status": "success", 
                "url": url,
                "domain": domain,
                "page_path": page_path,
                "embeddings_exist": embeddings_exist,
                "current_page_exists": current_page_exists,
                "domain_pages_count": len(existing_pages),
                "existing_pages": existing_pages[:5],  # Show first 5 pages
                "message": self._generate_page_status_message(url, domain, current_page_exists, existing_pages)
            }
            logging.info(f"Extract URL returning: {result}")
            return result
        
        logging.error("No URL provided in parameters")
        return {"status": "error", "error": "No URL provided"}

    def _generate_page_status_message(self, url: str, domain: str, current_page_exists: bool, existing_pages: List[Dict]) -> str:
        """Generate a human-readable message about the page status."""
        page_path = self._get_page_path_from_url(url)
        
        if current_page_exists:
            return f"Page {page_path} already exists in domain {domain}"
        elif existing_pages:
            existing_paths = [page['path'] for page in existing_pages[:3]]
            return f"Page {page_path} is new. Domain {domain} has {len(existing_pages)} existing pages: {', '.join(existing_paths)}"
        else:
            return f"Page {page_path} is the first page for domain {domain}" 