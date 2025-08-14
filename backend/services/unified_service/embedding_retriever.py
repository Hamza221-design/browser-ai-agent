import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

class EmbeddingRetriever:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client
        logging.info("[EMBEDDING_RETRIEVER] Initialized")

    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain name from URL for collection naming."""
        parsed = urlparse(url)
        domain = parsed.netloc
        domain = re.sub(r'[^a-zA-Z0-9_-]', '_', domain)
        domain = domain.strip('_')
        if not domain:
            domain = 'default_domain'
        return domain

    def get_relevant_embeddings(self, query: str, domain: str, max_distance: float = 1.8, max_results: int = 3) -> List[Dict]:
        """
        Retrieve relevant embeddings based on query and distance threshold.
        
        Args:
            query: The search query (user prompt)
            domain: The domain to search in
            max_distance: Maximum distance threshold (default 1.8)
            max_results: Maximum number of results to return (default 3)
            
        Returns:
            List of relevant embeddings with content and metadata
        """
        logging.info(f"Getting relevant embeddings for query: '{query[:100]}...' in domain: {domain}")
        logging.info(f"Max distance: {max_distance}, Max results: {max_results}")
        
        try:
            # Get collection for the domain
            try:
                collection = self.chroma_client.get_collection(name=domain)
            except Exception as e:
                logging.info(f"Collection {domain} does not exist yet: {str(e)}")
                return []
            
            # Query embeddings with the user prompt
            results = collection.query(
                query_texts=[query],
                n_results=max_results * 2,  # Get more results to filter by distance
                where={"domain": domain}
            )
            
            relevant_embeddings = []
            
            if results['ids'] and results['ids'][0]:
                for i, distance in enumerate(results['distances'][0]):
                    if distance <= max_distance:
                        embedding_data = {
                            'content': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'distance': distance,
                            'id': results['ids'][0][i]
                        }
                        relevant_embeddings.append(embedding_data)
                        logging.debug(f"Found relevant embedding with distance {distance:.3f}")
                        
                        # Stop if we have enough results
                        if len(relevant_embeddings) >= max_results:
                            break
                    else:
                        logging.debug(f"Skipping embedding with distance {distance:.3f} (above threshold {max_distance})")
            
            logging.info(f"Found {len(relevant_embeddings)} relevant embeddings within distance {max_distance}")
            
            # Sort by distance (closest first)
            relevant_embeddings.sort(key=lambda x: x['distance'])
            
            return relevant_embeddings
            
        except Exception as e:
            logging.error(f"Error retrieving embeddings for domain {domain}: {str(e)}")
            return []

    def get_relevant_embeddings_for_url(self, query: str, url: str, max_distance: float = 1.8, max_results: int = 3) -> List[Dict]:
        """
        Get relevant embeddings for a specific URL and query.
        
        Args:
            query: The search query (user prompt)
            url: The URL to get embeddings for
            max_distance: Maximum distance threshold (default 1.8)
            max_results: Maximum number of results to return (default 3)
            
        Returns:
            List of relevant embeddings
        """
        domain = self._get_domain_from_url(url)
        return self.get_relevant_embeddings(query, domain, max_distance, max_results)

    def get_all_domain_embeddings(self, domain: str, max_results: int = 10) -> List[Dict]:
        """
        Get all embeddings for a domain (useful for fallback when no relevant embeddings found).
        
        Args:
            domain: The domain to get embeddings for
            max_results: Maximum number of results to return
            
        Returns:
            List of all embeddings in the domain
        """
        logging.info(f"Getting all embeddings for domain: {domain}")
        
        try:
            try:
                collection = self.chroma_client.get_collection(name=domain)
            except Exception as e:
                logging.info(f"Collection {domain} does not exist yet: {str(e)}")
                return []
            
            results = collection.get(
                limit=max_results,
                include=['metadatas', 'documents']
            )
            
            embeddings = []
            for i, doc in enumerate(results['documents']):
                embedding_data = {
                    'content': doc,
                    'metadata': results['metadatas'][i],
                    'distance': 3.0,  # High distance to indicate it's a fallback
                    'id': results['ids'][i]
                }
                embeddings.append(embedding_data)
            
            logging.info(f"Retrieved {len(embeddings)} embeddings from domain {domain}")
            return embeddings
            
        except Exception as e:
            logging.error(f"Error retrieving all embeddings for domain {domain}: {str(e)}")
            return []

    def format_embeddings_for_prompt(self, embeddings: List[Dict]) -> str:
        """
        Format embeddings into a string suitable for inclusion in GPT prompts.
        
        Args:
            embeddings: List of embedding dictionaries
            
        Returns:
            Formatted string with embedding content and metadata
        """
        if not embeddings:
            return "No relevant context found."
        
        formatted_parts = []
        formatted_parts.append(f"Relevant context from {len(embeddings)} embeddings:")
        
        for i, emb in enumerate(embeddings, 1):
            content = emb['content']
            metadata = emb['metadata']
            distance = emb['distance']
            
            # Truncate content if too long
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted_part = f"""
Embedding {i} (Distance: {distance:.3f}):
- Type: {metadata.get('chunk_type', 'unknown')}
- URL: {metadata.get('url', 'unknown')}
- Title: {metadata.get('title', 'unknown')}
- Content: {content}
"""
            formatted_parts.append(formatted_part)
        
        return "\n".join(formatted_parts)

    def get_context_for_prompt(self, query: str, url: str, max_distance: float = 1.8, max_results: int = 3) -> str:
        """
        Get formatted context for a prompt based on query and URL.
        
        Args:
            query: The user's query/prompt
            url: The URL to get context for
            max_distance: Maximum distance threshold
            max_results: Maximum number of results
            
        Returns:
            Formatted context string for GPT prompt
        """
        domain = self._get_domain_from_url(url)
        
        # Try to get relevant embeddings
        relevant_embeddings = self.get_relevant_embeddings(query, domain, max_distance, max_results)
        
        # If no relevant embeddings found, get some general embeddings as fallback
        if not relevant_embeddings:
            logging.info(f"No relevant embeddings found for query, using fallback embeddings")
            fallback_embeddings = self.get_all_domain_embeddings(domain, max_results=2)
            if fallback_embeddings:
                return self.format_embeddings_for_prompt(fallback_embeddings)
            else:
                return "No context available for this domain."
        
        return self.format_embeddings_for_prompt(relevant_embeddings)

    def check_embeddings_exist(self, domain: str) -> bool:
        """
        Check if any embeddings exist for a domain.
        
        Args:
            domain: The domain to check
            
        Returns:
            True if embeddings exist, False otherwise
        """
        try:
            try:
                collection = self.chroma_client.get_collection(name=domain)
            except Exception as e:
                logging.debug(f"Collection {domain} does not exist: {str(e)}")
                return False
                
            results = collection.get(limit=1)
            return len(results['ids']) > 0
        except Exception as e:
            logging.debug(f"Error checking embeddings for domain {domain}: {str(e)}")
            return False

    def get_embedding_stats(self, domain: str) -> Dict:
        """
        Get statistics about embeddings in a domain.
        
        Args:
            domain: The domain to get stats for
            
        Returns:
            Dictionary with embedding statistics
        """
        try:
            try:
                collection = self.chroma_client.get_collection(name=domain)
            except Exception as e:
                logging.debug(f"Collection {domain} does not exist: {str(e)}")
                return {
                    'total_embeddings': 0,
                    'unique_urls': 0,
                    'chunk_types': {},
                    'domain': domain,
                    'error': 'Collection does not exist'
                }
            
            results = collection.get()
            
            total_embeddings = len(results['ids'])
            
            # Count by chunk type
            chunk_types = {}
            for metadata in results['metadatas']:
                chunk_type = metadata.get('chunk_type', 'unknown')
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            # Get unique URLs
            unique_urls = set()
            for metadata in results['metadatas']:
                if metadata and 'url' in metadata:
                    unique_urls.add(metadata['url'])
            
            return {
                'total_embeddings': total_embeddings,
                'unique_urls': len(unique_urls),
                'chunk_types': chunk_types,
                'domain': domain
            }
            
        except Exception as e:
            logging.error(f"Error getting embedding stats for domain {domain}: {str(e)}")
            return {
                'total_embeddings': 0,
                'unique_urls': 0,
                'chunk_types': {},
                'domain': domain,
                'error': str(e)
            } 