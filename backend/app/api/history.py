from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.query import QueryHistory
from app.schemas.schemas import QueryHistoryResponse

router = APIRouter()


@router.get("/", response_model=list[QueryHistoryResponse])
async def get_history(
    page: int = 1,
    limit: int = 20,
    query_type: Optional[str] = None,
    status: Optional[str] = None,
    favorites_only: bool = False,
    search: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(QueryHistory).filter(QueryHistory.user_id == current_user.id)
    if query_type:
        q = q.filter(QueryHistory.query_type == query_type.upper())
    if status:
        q = q.filter(QueryHistory.status == status)
    if favorites_only:
        q = q.filter(QueryHistory.is_favorite == True)
    if search:
        q = q.filter(QueryHistory.natural_language.ilike(f"%{search}%"))
    total = q.count()
    items = q.order_by(QueryHistory.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return items


@router.patch("/{query_id}/favorite")
async def toggle_favorite(
    query_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(QueryHistory).filter(
        QueryHistory.id == query_id, QueryHistory.user_id == current_user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Query not found")
    entry.is_favorite = not entry.is_favorite
    db.commit()
    return {"is_favorite": entry.is_favorite}


@router.delete("/{query_id}")
async def delete_history_entry(
    query_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(QueryHistory).filter(
        QueryHistory.id == query_id, QueryHistory.user_id == current_user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Query not found")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted"}
