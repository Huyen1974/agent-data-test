from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from settings import settings
from google.cloud import firestore

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo kết nối tới Firestore
db = firestore.Client()

def format_tree(docs):
    """Helper function to format Firestore docs into a tree structure for Vuetify."""
    nodes = {doc.id: {**doc.to_dict(), 'id': doc.id, 'children': []} for doc in docs}
    tree = []
    for doc_id, node_data in nodes.items():
        parent_id = node_data.get('parent')
        if parent_id in nodes:
            nodes[parent_id]['children'].append(node_data)
        else:
            tree.append(node_data)
    return tree

@app.get("/api/v1/knowledge-tree", tags=["Knowledge Tree"])
def get_knowledge_tree():
    """
    Retrieves the entire knowledge tree structure from Firestore.
    """
    docs_ref = db.collection(u'knowledge_documents').stream()
    tree_data = format_tree(docs_ref)
    return {"tree": tree_data}


@app.get("/api/v1/documents/{document_id}", tags=["Knowledge Tree"])
def get_document(document_id: str):
    """Fetch a knowledge document from the canonical kb_documents collection."""

    try:
        doc_ref = db.collection(u'kb_documents').document(document_id)
        snapshot = doc_ref.get()
    except Exception as exc:  # pragma: no cover - network/credential errors
        raise HTTPException(status_code=500, detail=f"Firestore error: {exc}") from exc

    if not getattr(snapshot, "exists", False):
        raise HTTPException(status_code=404, detail="Document not found")

    data = snapshot.to_dict() or {}
    return {
        "document_id": document_id,
        "content": data.get("content"),
        "metadata": data.get("metadata"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "revision": data.get("revision"),
        "vector_status": data.get("vector_status"),
    }

@app.get("/healthz", tags=["Health"])
def health_check():
    """Confirms the API is running."""
    return {"status": "ok", "app_name": settings.APP_NAME}

@app.get("/readyz", tags=["Health"])
def readiness_check():
    """Confirms the API is ready to serve traffic."""
    return {"status": "ready"}
