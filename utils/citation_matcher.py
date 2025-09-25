"""Load flat file sources into ChromaDB for vector similarity matching."""

from typing import List, Dict, Optional
import logging
import os

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError as exc:  # pragma: no cover - exercised in environments without chromadb
    chromadb = None  # type: ignore[assignment]
    embedding_functions = None  # type: ignore[assignment]
    _CHROMADB_IMPORT_ERROR = exc
else:
    _CHROMADB_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


class CitationMatcher:
    """Load flat files into ChromaDB for vector similarity matching."""

    def __init__(self, session_id: str):
        self.session_id = session_id

        self.collection = None
        self._loaded = False
        self.client = None
        self.embedding_fn = None
        self._chromadb_available = chromadb is not None

        if not self._chromadb_available:
            logger.warning(
                "ChromaDB not installed; citation matching disabled. Install chromadb to enable."
                + (f" ({_CHROMADB_IMPORT_ERROR})" if _CHROMADB_IMPORT_ERROR else "")
            )
            return

        # Get ChromaDB Cloud credentials from environment
        api_key = os.getenv('CHROMADB_API_KEY')
        tenant = os.getenv('CHROMADB_TENANT')
        database = os.getenv('CHROMADB_DATABASE', 'sourcing-agent')

        if api_key and tenant:
            # Use ChromaDB Cloud client if credentials are provided
            self.client = chromadb.CloudClient(
                api_key=api_key,
                tenant=tenant,
                database=database
            )
            # Use default embedding function (ChromaDB Cloud handles embeddings)
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        else:
            # Fall back to ephemeral local client
            logger.warning("ChromaDB Cloud credentials not found, using local ephemeral client")
            self.client = chromadb.Client()
            # Use default embedding function
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    def load_from_flat_files(self):
        """Load sources from flat files into ChromaDB."""
        if not self._chromadb_available:
            return

        if self._loaded:
            return  # Already loaded

        # Read all sources from flat files
        from utils.source_logger import SourceLogger
        source_logger = SourceLogger(self.session_id)
        sources = source_logger.read_all_sources()

        if not sources:
            logger.warning(f"No sources found for session {self.session_id}")
            return

        # Create ChromaDB collection
        collection_name = f"session_{self.session_id}"
        # Delete if exists (for fresh reload)
        try:
            self.client.delete_collection(collection_name)
        except:
            pass  # Collection doesn't exist yet

        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )

        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for i, source in enumerate(sources):
            # Skip sources without content
            content = source.get('content', '').strip()
            if not content:
                continue

            # Combine title + content for embedding
            title = source.get('title', '')
            doc_text = f"{title}\n{content}"
            documents.append(doc_text)

            metadatas.append({
                'url': source.get('url', ''),
                'title': title,
                'agent': source.get('agent', 'unknown'),
                'tool': source.get('tool', 'unknown'),
                'query': source.get('query', ''),
                'timestamp': source.get('timestamp', '')
            })

            ids.append(f"source_{i:05d}")

        if not documents:
            logger.warning(f"No valid documents to index for session {self.session_id}")
            return

        # Batch insert into ChromaDB
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            end_idx = min(i + batch_size, len(documents))
            self.collection.add(
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )

        self._loaded = True
        logger.info(f"Loaded {len(documents)} sources into ChromaDB for citation matching")

    def find_citations(self, text: str, n_results: int = 5) -> List[Dict]:
        """Find most relevant citations for given text.

        Parameters
        ----------
        text : str
            Text to find citations for (e.g., a claim or sentence)
        n_results : int
            Number of citations to return

        Returns
        -------
        List[Dict]
            List of citations with url, title, agent, and similarity score
        """
        if not self._loaded:
            self.load_from_flat_files()

        if not self._chromadb_available or not self.collection:
            return []

        # Handle empty text
        if not text or not text.strip():
            return []

        try:
            # Search for similar content
            results = self.collection.query(
                query_texts=[text],
                n_results=n_results
            )

            # Format as citation list
            citations = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # Get metadata for this result
                    metadata = results['metadatas'][0][i] if results['metadatas'][0] else {}

                    citations.append({
                        'url': metadata.get('url', ''),
                        'title': metadata.get('title', ''),
                        'agent': metadata.get('agent', 'unknown'),
                        'tool': metadata.get('tool', 'unknown'),
                        'similarity': 1.0 - results['distances'][0][i]  # Convert distance to similarity
                    })

            return citations

        except Exception as e:
            logger.error(f"Error finding citations: {e}")
            return []

    def find_citations_for_vendor(self, vendor_name: str, vendor_description: str = "",
                                 n_results: int = 3) -> List[Dict]:
        """Find citations specifically for a vendor.

        Parameters
        ----------
        vendor_name : str
            Name of the vendor
        vendor_description : str
            Description of the vendor
        n_results : int
            Number of citations to return

        Returns
        -------
        List[Dict]
            List of citations relevant to the vendor
        """
        if not self._chromadb_available:
            return []

        # Combine vendor name and description for better search
        search_text = f"{vendor_name} {vendor_description}"
        return self.find_citations(search_text, n_results)

    def find_citations_for_section(self, section_text: str, section_name: str,
                                  n_results_per_claim: int = 2,
                                  max_total_citations: int = 10) -> List[Dict]:
        """Find citations for an entire section of text.

        Parameters
        ----------
        section_text : str
            Full text of the section
        section_name : str
            Name of the section (e.g., "political", "economic")
        n_results_per_claim : int
            Citations per individual claim
        max_total_citations : int
            Maximum total citations for the section

        Returns
        -------
        List[Dict]
            Deduplicated list of citations for the section
        """
        if not self._chromadb_available:
            return []

        import re

        # Split into sentences for more focused citation matching
        sentences = re.split(r'(?<=[.!?])\s+', section_text)

        # Filter for sentences that likely need citations
        claims = []
        for sent in sentences:
            # Check if sentence has factual claims
            if (re.search(r'\d+', sent) or  # Has numbers
                '%' in sent or  # Has percentages
                any(term in sent.lower() for term in
                    ['increase', 'decrease', 'growth', 'report', 'analysis', 'leading', 'major'])):
                claims.append(sent)

        # Find citations for each claim
        all_citations = []
        seen_urls = set()

        for claim in claims[:5]:  # Limit to first 5 claims to avoid too many searches
            citations = self.find_citations(claim, n_results_per_claim)
            for cite in citations:
                if cite['url'] and cite['url'] not in seen_urls:
                    all_citations.append(cite)
                    seen_urls.add(cite['url'])
                    if len(all_citations) >= max_total_citations:
                        break

            if len(all_citations) >= max_total_citations:
                break

        return all_citations
