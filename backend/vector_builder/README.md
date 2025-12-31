# Vector Builder for Q&A Knowledge Base

This folder contains scripts to build and test the FAISS vector index for your Q&A knowledge base.

## Structure

```
backend/
├── knowledgebase/
│   ├── documents/          # Put your Q&A .txt files here
│   └── vector_store/       # Generated FAISS index (auto-created)
└── vector_builder/         # Build scripts (this folder)
    ├── build_index.py      # Builds the FAISS index
    ├── knowledge_search.py # Search functionality
    └── requirements.txt    # Dependencies
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your Q&A documents:**
   - Place `.txt` files in `backend/knowledgebase/documents/`
   - Format: Each Q&A pair on separate lines
     ```
     Q: Your question here?
     A: Your answer here.
     
     Q: Another question?
     A: Another answer.
     ```

## Usage

### 1. Build the Index

Run this whenever you add or update Q&A documents:

```bash
cd backend/vector_builder
python build_index.py
```

This will:
- Read all `.txt` files from `knowledgebase/documents/`
- Chunk by Q&A pairs
- Generate embeddings using Sentence Transformers
- Create FAISS index in `knowledgebase/vector_store/`

### 2. Test the Search

Test your knowledge base:

```bash
python knowledge_search.py
```

This will run test queries and show you the results.

## How It Works

1. **Chunking**: Each Q&A pair becomes one chunk
2. **Embeddings**: Uses `all-MiniLM-L6-v2` model for semantic embeddings
3. **Index**: FAISS IndexFlatIP for fast cosine similarity search
4. **Search**: Returns top K most relevant Q&A pairs with scores

## Integration with Voice Agent

The voice agent will use `KnowledgeBaseSearch` class to answer questions:

```python
from vector_builder.knowledge_search import KnowledgeBaseSearch

kb = KnowledgeBaseSearch()
kb.load_index()

# Search for answer
results = kb.search("What is Bean & Brew?", k=3)
best_answer = kb.get_best_answer("What is Bean & Brew?")
```

## Notes

- **First run**: Model download (~90MB) happens automatically
- **Rebuild**: Run `build_index.py` after updating documents
- **Performance**: Fast search (~10-50ms per query)
- **Format**: Strictly Q: and A: format required
