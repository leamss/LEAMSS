"""Knowledge Base Router — FAQ & Help Articles"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from core.database import knowledge_base_col
from core.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


class ArticleCreate(BaseModel):
    title: str
    content: str
    category: str = "general"
    tags: list = []
    is_published: bool = True


@router.get("/articles")
async def list_articles(category: Optional[str] = None, search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List knowledge base articles"""
    query = {"is_published": True}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}}
        ]
    articles = await knowledge_base_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    for a in articles:
        if isinstance(a.get("created_at"), datetime):
            a["created_at"] = a["created_at"].isoformat()
        if isinstance(a.get("updated_at"), datetime):
            a["updated_at"] = a["updated_at"].isoformat()
    return articles


@router.get("/articles/{article_id}")
async def get_article(article_id: str, current_user: dict = Depends(get_current_user)):
    """Get single article"""
    article = await knowledge_base_col.find_one({"id": article_id}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    await knowledge_base_col.update_one({"id": article_id}, {"$inc": {"views": 1}})
    for f in ["created_at", "updated_at"]:
        if isinstance(article.get(f), datetime):
            article[f] = article[f].isoformat()
    return article


@router.post("/articles")
async def create_article(request: ArticleCreate, current_user: dict = Depends(get_current_user)):
    """Create new knowledge base article (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    article = {
        "id": str(uuid.uuid4()), "title": request.title, "content": request.content,
        "category": request.category, "tags": request.tags,
        "is_published": request.is_published, "views": 0,
        "author_id": current_user["id"], "author_name": current_user["name"],
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
    }
    await knowledge_base_col.insert_one(article)
    article.pop("_id", None)
    article["created_at"] = article["created_at"].isoformat()
    article["updated_at"] = article["updated_at"].isoformat()
    await log_activity(current_user["id"], current_user["name"], "create_kb_article", "knowledge_base", article["id"], {"title": request.title})
    return article


@router.put("/articles/{article_id}")
async def update_article(article_id: str, request: ArticleCreate, current_user: dict = Depends(get_current_user)):
    """Update article (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await knowledge_base_col.find_one({"id": article_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    await knowledge_base_col.update_one({"id": article_id}, {"$set": {
        "title": request.title, "content": request.content, "category": request.category,
        "tags": request.tags, "is_published": request.is_published,
        "updated_at": datetime.now(timezone.utc)
    }})
    return {"message": "Updated"}


@router.delete("/articles/{article_id}")
async def delete_article(article_id: str, current_user: dict = Depends(get_current_user)):
    """Delete article (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await knowledge_base_col.delete_one({"id": article_id})
    return {"message": "Deleted"}


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    """Get all categories"""
    articles = await knowledge_base_col.find({"is_published": True}, {"_id": 0, "category": 1}).to_list(1000)
    cats = {}
    for a in articles:
        c = a.get("category", "general")
        cats[c] = cats.get(c, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(cats.items())]
