"""
Knowledge Base Search Module
Loads FAISS index and provides semantic search functionality using FastEmbed.
"""

import numpy as np
import faiss
from fastembed import TextEmbedding
from typing import List, Dict, Optional
import pickle
import os
from pathlib import Path


class KnowledgeBaseSearch:
    """Semantic search for Q&A knowledge base using FAISS and FastEmbed."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model = None  # Lazy load
        self.model_name = model_name
        self.index = None
        self.documents = []
        self.metadata = []
        self.is_loaded = False
    
    def load_index(self, vector_store_dir: str = None):
        """Load existing FAISS index and metadata."""
        if vector_store_dir is None:
            # Use absolute path relative to this file
            vector_store_dir = Path(__file__).parent.parent / "knowledgebase" / "vector_store"
        vector_store_path = Path(vector_store_dir)
        index_path = vector_store_path / 'index.faiss'
        metadata_path = vector_store_path / 'metadata.pkl'
        
        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                f"Index not found in {vector_store_dir}. "
                "Run 'python build_index.py' first."
            )
        
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))
        
        # Load metadata
        with open(metadata_path, 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.metadata = data['metadata']
        
        self.is_loaded = True
        print(f"✅ Loaded knowledge base with {self.index.ntotal} Q&A pairs")
        return True
    
    def _load_model(self):
        """Load model only when needed (lazy loading)."""
        if self.model is None:
            print(f"Loading FastEmbed model: {self.model_name}")
            print("💡 Using FastEmbed with ONNX Runtime - lightweight, no PyTorch needed!")
            self.model = TextEmbedding(model_name=self.model_name)
            print("Model loaded!")
    
    def search(self, query: str, k: int = 3) -> List[Dict]:
        """
        Search for similar Q&A pairs.
        
        Args:
            query: User's question
            k: Number of results to return
            
        Returns:
            List of matching Q&A pairs with scores
        """
        if not self.is_loaded:
            raise ValueError("Index not loaded. Call load_index() first.")
        
        # Load model on first search
        self._load_model()
        
        # Generate query embedding with query prefix for better retrieval
        query_with_prefix = f"query: {query}"
        
        # FastEmbed returns an iterator
        embeddings_list = list(self.model.embed([query_with_prefix]))
        query_embedding_np = np.array(embeddings_list[0], dtype='float32').reshape(1, -1)
        
        # Normalize for Inner Product similarity
        norm = np.linalg.norm(query_embedding_np)
        if norm > 0:
            query_embedding_np = query_embedding_np / norm
        
        # Search
        scores, indices = self.index.search(query_embedding_np, k)
        
        # Format results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            metadata = self.metadata[idx]
            results.append({
                'rank': i + 1,
                'score': float(score),
                'question': metadata['question'],
                'answer': metadata['answer'],
                'full_text': self.documents[idx],
                'document': metadata['document'],
                'chunk_id': metadata['chunk_id']
            })
        
        return results
    
    def get_best_answer(self, query: str, threshold: float = 0.5) -> Optional[Dict]:
        """
        Get the best matching answer for a query.
        
        Args:
            query: User's question
            threshold: Minimum similarity score (0-1)
            
        Returns:
            Best matching Q&A pair or None if below threshold
        """
        results = self.search(query, k=1)
        
        if results and results[0]['score'] >= threshold:
            return results[0]
        
        return None
    
    def get_all_questions(self) -> List[str]:
        """Get all questions in the knowledge base."""
        if not self.is_loaded:
            raise ValueError("Index not loaded. Call load_index() first.")
        
        return [meta['question'] for meta in self.metadata]
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics."""
        if not self.is_loaded:
            raise ValueError("Index not loaded. Call load_index() first.")
        
        documents = set(meta['document'] for meta in self.metadata)
        
        return {
            'total_qa_pairs': len(self.metadata),
            'total_documents': len(documents),
            'documents': list(documents)
        }


def test_search():
    """Test the knowledge base search."""
    
    print("\n" + "="*60)
    print("🔍 TESTING KNOWLEDGE BASE SEARCH")
    print("="*60)
    
    # Initialize search
    kb = KnowledgeBaseSearch()
    kb.load_index()
    
    # Show stats
    stats = kb.get_stats()
    print(f"\n📊 Knowledge Base Stats:")
    print(f"   Total Q&A pairs: {stats['total_qa_pairs']}")
    print(f"   Documents: {', '.join(stats['documents'])}")
    
    # Test queries
    test_queries = [
        "Who is Bean & Brew?",
        "What makes specialty coffee different?",
        "How can I increase revenue with coffee?",
        "Tell me about the founders"
    ]
    
    print("\n" + "="*60)
    print("🧪 TEST QUERIES")
    print("="*60)
    
    for query in test_queries:
        print(f"\n❓ Query: {query}")
        print("-" * 40)
        
        results = kb.search(query, k=2)
        
        for result in results:
            print(f"\n{result['rank']}. Score: {result['score']:.4f}")
            print(f"Q: {result['question'][:100]}...")
            print(f"A: {result['answer'][:150]}...")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    test_search()
