from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.query import QueryHistory
from app.schemas.schemas import QueryHistoryResponse

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    days: int = 30,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    queries = db.query(QueryHistory).filter(
        QueryHistory.user_id == current_user.id,
        QueryHistory.created_at >= since,
    ).all()

    total = len(queries)
    executed = sum(1 for q in queries if q.status == "executed")
    failed = sum(1 for q in queries if q.status == "failed")
    blocked = sum(1 for q in queries if q.status == "blocked")

    avg_time = (
        sum(q.execution_time_ms for q in queries if q.execution_time_ms) /
        max(sum(1 for q in queries if q.execution_time_ms), 1)
    )

    type_counts = {}
    for q in queries:
        if q.query_type:
            type_counts[q.query_type] = type_counts.get(q.query_type, 0) + 1

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for q in queries:
        risk_counts[q.risk_level] = risk_counts.get(q.risk_level, 0) + 1

    # Daily counts for chart
    daily = {}
    for q in queries:
        day = q.created_at.strftime("%Y-%m-%d")
        daily[day] = daily.get(day, 0) + 1

    # Top tables (simple extraction)
    table_counts = {}
    for q in queries:
        if q.generated_sql:
            import re
            tables = re.findall(r"FROM\s+(\w+)|JOIN\s+(\w+)", q.generated_sql, re.IGNORECASE)
            for t1, t2 in tables:
                name = (t1 or t2).lower()
                table_counts[name] = table_counts.get(name, 0) + 1

    top_tables = sorted(table_counts.items(), key=lambda x: -x[1])[:5]

    return {
        "summary": {
            "total_queries": total,
            "executed": executed,
            "failed": failed,
            "blocked": blocked,
            "avg_execution_time_ms": round(avg_time, 2),
            "success_rate": round(executed / max(total, 1) * 100, 1),
        },
        "query_types": [{"type": k, "count": v} for k, v in type_counts.items()],
        "risk_distribution": [{"level": k, "count": v} for k, v in risk_counts.items()],
        "daily_queries": [{"date": k, "count": v} for k, v in sorted(daily.items())],
        "top_tables": [{"table": t, "count": c} for t, c in top_tables],
    }
