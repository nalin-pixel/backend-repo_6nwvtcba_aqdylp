import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents, db
from schemas import BlogPost, ContactMessage

app = FastAPI(title="Flames Landing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -------- Blog Endpoints --------
class BlogListResponse(BaseModel):
    items: List[BlogPost]
    count: int


@app.get("/blogposts", response_model=BlogListResponse)
def list_blog_posts(limit: Optional[int] = 6, featured: Optional[bool] = None):
    if db is None:
        # Return a friendly empty state if no DB configured
        return BlogListResponse(items=[], count=0)

    filter_dict = {}
    if featured is not None:
        filter_dict["featured"] = featured

    docs = get_documents("blogpost", filter_dict, limit=limit)

    # Convert Mongo docs to Pydantic models (strip _id)
    items: List[BlogPost] = []
    for d in docs:
        d.pop("_id", None)
        try:
            items.append(BlogPost(**d))
        except Exception:
            # Skip invalid documents
            continue

    return BlogListResponse(items=items, count=len(items))


# -------- Contact Endpoint --------
class ContactResponse(BaseModel):
    ok: bool
    message: str
    id: Optional[str] = None


@app.post("/contact", response_model=ContactResponse)
def submit_contact(payload: ContactMessage):
    try:
        inserted_id = create_document("contactmessage", payload)
        return ContactResponse(ok=True, message="Thanks! Your message has been received.", id=inserted_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit message: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
