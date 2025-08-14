import logging
import re
import asyncio
import math
from typing import Dict, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

class EmbeddingActions:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client
        logging.info("[EMBEDDING_ACTIONS] Initialized")

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
        """Extract page path from URL including hash fragment for SPA URLs."""
        parsed = urlparse(url)
        path = parsed.path or "/"
        
        # Include hash fragment for SPA URLs (e.g., #/login)
        if parsed.fragment:
            path = f"{path}#{parsed.fragment}"
        
        return path

    def _get_url_path(self, url: str) -> str:
        """Extract URL path for metadata including hash fragment."""
        parsed = urlparse(url)
        path = parsed.path or '/'
        
        # Include hash fragment for SPA URLs
        if parsed.fragment:
            path = f"{path}#{parsed.fragment}"
        
        return path

    def _check_embedding_exists(self, domain: str, url: str) -> bool:
        """Check if embeddings already exist for the given domain and URL."""
        try:
            # First check if the collection exists
            try:
                collection = self.chroma_client.get_collection(name=domain)
                logging.debug(f"Collection {domain} exists, checking for URL: {url}")
            except Exception as e:
                logging.debug(f"Collection {domain} does not exist: {str(e)}")
                return False
            
            # Check if embeddings exist for this URL
            results = collection.get(
                where={"url": url},
                limit=1
            )
            
            exists = len(results['ids']) > 0
            logging.info(f"Embedding check for URL {url} in domain {domain}: {'EXISTS' if exists else 'NOT FOUND'}")
            return exists
            
        except Exception as e:
            logging.error(f"Error checking embeddings for domain {domain}, URL {url}: {str(e)}")
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

    async def _fetch_rendered_html_async(self, url: str) -> Dict:
        """Fetch fully rendered HTML using Playwright."""
        logging.info(f"Starting HTML fetch for URL: {url}")
        
        try:
            async with async_playwright() as p:
                logging.debug("Launching Playwright browser...")
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                logging.debug(f"Navigating to URL: {url}")
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                logging.debug("Waiting for page to stabilize...")
                await asyncio.sleep(2)
                
                # Get page content including JavaScript rendered content
                html = await page.content()
                
                # Get page title
                title = await page.title()
                
                # Get page metadata
                meta_description = await page.evaluate("() => document.querySelector('meta[name=\"description\"]')?.content || ''")
                meta_keywords = await page.evaluate("() => document.querySelector('meta[name=\"keywords\"]')?.content || ''")
                
                # Get all text content
                text_content = await page.evaluate("() => document.body.innerText")
                
                # Get JavaScript content
                scripts = await page.evaluate("() => Array.from(document.scripts).map(s => s.textContent).join('\\n')")
                
                # Get CSS content
                styles = await page.evaluate("() => Array.from(document.styleSheets).map(s => s.href).join('\\n')")
                
                html_length = len(html)
                logging.info(f"Successfully fetched HTML for {url} - Content length: {html_length} characters")
                
                await browser.close()
                logging.debug("Browser closed successfully")
                
                return {
                    'html': html,
                    'title': title,
                    'meta_description': meta_description,
                    'meta_keywords': meta_keywords,
                    'text_content': text_content,
                    'scripts': scripts,
                    'styles': styles
                }
                
        except Exception as e:
            logging.error(f"Failed to fetch HTML for URL {url}: {str(e)}")
            logging.error(f"Error type: {type(e).__name__}")
            raise

    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into chunks of specified size, trying to break at word boundaries."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this is not the last chunk, try to break at a word boundary
            if end < len(text):
                # Look for the last space or newline within the chunk
                last_space = text.rfind(' ', start, end)
                last_newline = text.rfind('\n', start, end)
                break_point = max(last_space, last_newline)
                
                if break_point > start:
                    end = break_point + 1
            
            chunks.append(text[start:end].strip())
            start = end
        
        return chunks

    def _create_embeddings(self, domain: str, url: str, page_data: Dict) -> None:
        """Create and store embeddings for page content in chunks of 1000 characters."""
        try:
            # Get or create collection
            try:
                collection = self.chroma_client.get_collection(name=domain)
            except:
                collection = self.chroma_client.create_collection(name=domain)

            # Prepare content chunks
            content_chunks = []
            
            # Add title as first chunk
            if page_data.get('title'):
                content_chunks.append({
                    'content': f"Page Title: {page_data['title']}",
                    'chunk_type': 'title',
                    'chunk_index': 0
                })
            
            # Add meta description as chunk
            if page_data.get('meta_description'):
                content_chunks.append({
                    'content': f"Page Description: {page_data['meta_description']}",
                    'chunk_type': 'meta_description',
                    'chunk_index': len(content_chunks)
                })
            
            # Add meta keywords as chunk
            if page_data.get('meta_keywords'):
                content_chunks.append({
                    'content': f"Page Keywords: {page_data['meta_keywords']}",
                    'chunk_type': 'meta_keywords',
                    'chunk_index': len(content_chunks)
                })
            
            # Split text content into chunks
            if page_data.get('text_content'):
                text_content = page_data['text_content']
                text_chunks = self._split_text_into_chunks(text_content, 1000)
                for i, chunk in enumerate(text_chunks):
                    content_chunks.append({
                        'content': f"Text Content (Part {i+1}): {chunk}",
                        'chunk_type': 'text_content',
                        'chunk_index': len(content_chunks)
                    })
            
            # Split HTML content into chunks
            if page_data.get('html'):
                html_content = page_data['html']
                html_chunks = self._split_text_into_chunks(html_content, 1000)
                for i, chunk in enumerate(html_chunks):
                    content_chunks.append({
                        'content': f"HTML Structure (Part {i+1}): {chunk}",
                        'chunk_type': 'html_structure',
                        'chunk_index': len(content_chunks)
                    })
            
            # Add JavaScript content as chunks
            if page_data.get('scripts'):
                scripts_content = page_data['scripts']
                scripts_chunks = self._split_text_into_chunks(scripts_content, 1000)
                for i, chunk in enumerate(scripts_chunks):
                    content_chunks.append({
                        'content': f"JavaScript (Part {i+1}): {chunk}",
                        'chunk_type': 'javascript',
                        'chunk_index': len(content_chunks)
                    })
            
            # Add CSS content as chunks
            if page_data.get('styles'):
                styles_content = page_data['styles']
                styles_chunks = self._split_text_into_chunks(styles_content, 1000)
                for i, chunk in enumerate(styles_chunks):
                    content_chunks.append({
                        'content': f"CSS (Part {i+1}): {chunk}",
                        'chunk_type': 'css',
                        'chunk_index': len(content_chunks)
                    })

            # Prepare documents, metadatas, and ids for batch insertion
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk_data in enumerate(content_chunks):
                # Base metadata
                metadata = {
                    "url": url,
                    "domain": domain,
                    "path": self._get_url_path(url),
                    "title": page_data.get('title', ''),
                    "meta_description": page_data.get('meta_description', ''),
                    "meta_keywords": page_data.get('meta_keywords', ''),
                    "content_length": len(page_data.get('html', '')),
                    "text_length": len(page_data.get('text_content', '')),
                    "has_scripts": bool(page_data.get('scripts')),
                    "has_styles": bool(page_data.get('styles')),
                    "timestamp": str(asyncio.get_event_loop().time()),
                    "chunk_type": chunk_data['chunk_type'],
                    "chunk_index": chunk_data['chunk_index'],
                    "total_chunks": len(content_chunks),
                    "chunk_content_length": len(chunk_data['content'])
                }
                
                documents.append(chunk_data['content'])
                metadatas.append(metadata)
                ids.append(f"{domain}_{hash(url)}_chunk_{i}")

            # Add all chunks to collection in batch
            if documents:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logging.info(f"Created {len(documents)} embedding chunks for {url} in collection {domain}")
                logging.info(f"Chunk types: {[chunk['chunk_type'] for chunk in content_chunks]}")
            else:
                logging.warning(f"No content chunks created for {url}")

        except Exception as e:
            logging.error(f"Error creating embeddings for {url}: {str(e)}")
            raise

    async def create_embeddings(self, parameters: Dict) -> Dict:
        """Create embeddings for a URL."""
        logging.info(f"Create embeddings called with parameters: {parameters}")
        url = parameters.get("url")
        logging.info(f"Extracted URL from parameters: {url}")
        
        if not url:
            logging.error("No URL provided for embeddings creation")
            return {"status": "error", "error": "No URL provided"}
        
        try:
            logging.info(f"Creating embeddings for URL: {url}")
            
            # Extract domain and page path from URL
            domain = self._get_domain_from_url(url)
            page_path = self._get_page_path_from_url(url)
            
            logging.info(f"Domain: {domain}, Page path: {page_path}")
            
            # Check if embeddings already exist
            logging.info(f"Checking if embeddings already exist for URL: {url}")
            embeddings_exist = self._check_embedding_exists(domain, url)
            
            if embeddings_exist:
                logging.info(f"✅ Embeddings already exist for URL: {url}")
                existing_pages = self._get_existing_pages(domain)
                
                return {
                    "status": "success", 
                    "embeddings_created": False,
                    "embeddings_exist": True,
                    "domain": domain,
                    "url": url,
                    "page_path": page_path,
                    "domain_pages_count": len(existing_pages),
                    "existing_pages": existing_pages[:5],
                    "message": f"Embeddings already exist for page {page_path} in domain {domain}"
                }
            
            logging.info(f"❌ Embeddings do not exist, creating new embeddings for domain: {domain}, page: {page_path}")
            
            # Fetch rendered HTML content
            logging.info(f"Fetching HTML content for URL: {url}")
            page_data = await self._fetch_rendered_html_async(url)
            
            # Create embeddings
            logging.info(f"Creating embeddings for domain: {domain}")
            self._create_embeddings(domain, url, page_data)
            
            existing_pages = self._get_existing_pages(domain)
            
            return {
                "status": "success", 
                "embeddings_created": True,
                "embeddings_exist": False,
                "domain": domain,
                "url": url,
                "page_path": page_path,
                "domain_pages_count": len(existing_pages),
                "existing_pages": existing_pages[:5],
                "content_length": len(page_data.get('html', '')),
                "text_length": len(page_data.get('text_content', '')),
                "title": page_data.get('title', ''),
                "message": f"Embeddings created successfully for page {page_path} in domain {domain}"
            }
            
        except Exception as e:
            logging.error(f"Error creating embeddings: {str(e)}")
            return {"status": "error", "error": str(e)}

    def list_domain_pages(self, parameters: Dict) -> Dict:
        """List all pages for a domain."""
        domain = parameters.get("domain")
        if not domain:
            return {"status": "error", "error": "No domain provided"}
        
        try:
            existing_pages = self._get_existing_pages(domain)
            return {
                "status": "success",
                "domain": domain,
                "pages_count": len(existing_pages),
                "pages": existing_pages,
                "message": f"Found {len(existing_pages)} pages in domain {domain}"
            }
        except Exception as e:
            logging.error(f"Error listing domain pages: {str(e)}")
            return {"status": "error", "error": str(e)} 