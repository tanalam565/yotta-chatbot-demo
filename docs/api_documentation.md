# API


## POST /api/ingest
Rebuilds the FAISS index from files in `data/sample_documents`.


**Response**
```json
{ "status": "ok", "chunks": 42 }