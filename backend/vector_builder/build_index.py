"""
Build FAISS Index for Q&A Knowledge Base
Chunks documents by Q&A pairs and creates vector embeddings.
"""

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import normalize_embeddings
from typing import List, Dict
import pickle
import os
from pathlib import Path


class QAIndexBuilder:
    """Builds FAISS index from Q&A formatted documents."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Loading Sentence Transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("Model loaded successfully!")
    
    def chunk_qa_document(self, text: str, doc_name: str) -> List[Dict]:
        """
        Chunk Q&A document by Q:A: pairs.
        Each Q&A pair becomes one chunk.
        """
        chunks = []
        lines = text.split('\n')
        
        current_question = ""
        current_answer = ""
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is a question
            if line.startswith('Q:'):
                # Save previous Q&A if exists
                if current_question and current_answer:
                    qa_text = f"{current_question}\n{current_answer}"
                    chunks.append({
                        'text': qa_text.strip(),
                        'chunk_id': len(chunks),
                        'question': current_question.replace('Q:', '').strip(),
                        'answer': current_answer.replace('A:', '').strip(),
                        'document': doc_name
                    })
                
                # Start new Q&A
                current_question = line
                current_answer = ""
                
            elif line.startswith('A:'):
                # This is an answer
                current_answer = line
                
            elif current_answer:
                # Continuation of answer (multi-line)
                current_answer += " " + line
        
        # Add the last Q&A pair
        if current_question and current_answer:
            qa_text = f"{current_question}\n{current_answer}"
            chunks.append({
                'text': qa_text.strip(),
                'chunk_id': len(chunks),
                'question': current_question.replace('Q:', '').strip(),
                'answer': current_answer.replace('A:', '').strip(),
                'document': doc_name
            })
        
        return chunks
    
    def build_index_from_documents(self, documents_dir: str, output_dir: str):
        """
        Build FAISS index from all Q&A documents in the directory.
        """
        documents_path = Path(documents_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all .txt files in documents directory
        txt_files = list(documents_path.glob("*.txt"))
        
        if not txt_files:
            print(f"❌ No .txt files found in {documents_dir}")
            return False
        
        print(f"\n📚 Found {len(txt_files)} document(s) to process")
        
        all_chunks = []
        
        # Process each document
        for txt_file in txt_files:
            print(f"\n📄 Processing: {txt_file.name}")
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            chunks = self.chunk_qa_document(text, txt_file.stem)
            all_chunks.extend(chunks)
            
            print(f"   ✅ Created {len(chunks)} Q&A chunks")
        
        print(f"\n📊 Total chunks created: {len(all_chunks)}")
        
        if not all_chunks:
            print("❌ No chunks created. Check your document format.")
            return False
        
        # Extract text for embedding
        texts = [chunk['text'] for chunk in all_chunks]
        
        print("\n🧠 Generating embeddings...")
        embeddings = self.model.encode(
            texts, 
            convert_to_tensor=True, 
            show_progress_bar=True
        )
        
        print("📐 Normalizing embeddings...")
        embeddings = normalize_embeddings(embeddings)
        embeddings_np = embeddings.cpu().numpy()
        
        print("🔨 Creating FAISS index...")
        dimension = embeddings_np.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity
        index.add(embeddings_np)
        
        print(f"✅ Index created with {index.ntotal} vectors")
        
        # Save everything
        self.save_index(index, texts, all_chunks, output_path)
        
        print(f"\n🎉 Index building completed successfully!")
        print(f"📁 Saved to: {output_path}")
        
        return True
    
    def save_index(self, index, documents, metadata, output_dir: Path):
        """Save the FAISS index and metadata."""
        
        # Save FAISS index
        index_path = output_dir / 'index.faiss'
        faiss.write_index(index, str(index_path))
        print(f"   💾 Saved FAISS index: {index_path}")
        
        # Save metadata
        metadata_path = output_dir / 'metadata.pkl'
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'documents': documents,
                'metadata': metadata
            }, f)
        print(f"   💾 Saved metadata: {metadata_path}")


def main():
    """Build the index from Q&A documents."""
    
    print("\n" + "="*60)
    print("🚀 FAISS INDEX BUILDER FOR Q&A KNOWLEDGE BASE")
    print("="*60)
    
    # Paths relative to backend directory
    documents_dir = "../knowledgebase/documents"
    output_dir = "../knowledgebase/vector_store"
    
    # Build the index
    builder = QAIndexBuilder()
    success = builder.build_index_from_documents(documents_dir, output_dir)
    
    if success:
        print("\n✅ Ready to use! The knowledge base is now searchable.")
    else:
        print("\n❌ Failed to build index. Please check your documents.")


if __name__ == "__main__":
    main()
