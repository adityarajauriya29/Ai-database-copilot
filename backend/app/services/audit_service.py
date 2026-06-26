import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.query import AuditLog


def _compute_hash(entry: Dict[str, Any], prev_hash: Optional[str]) -> str:
    payload = json.dumps({
        "user_id": entry.get("user_id"),
        "action": entry.get("action"),
        "resource": entry.get("resource"),
        "details": entry.get("details"),
        "created_at": entry.get("created_at"),
        "prev_hash": prev_hash,
    }, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def write_audit_log(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    # Get last hash for chain
    last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = last.entry_hash if last else None

    created_at = datetime.utcnow()
    entry_data = {
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "details": details,
        "created_at": str(created_at),
    }
    entry_hash = _compute_hash(entry_data, prev_hash)

    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id else None,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        created_at=created_at,
    )
    db.add(log)
    db.commit()
    return log


def verify_audit_chain(db: Session) -> bool:
    """Verify the entire audit log chain hasn't been tampered with."""
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    prev_hash = None
    for log in logs:
        if log.prev_hash != prev_hash:
            return False
        entry_data = {
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "details": log.details,
            "created_at": str(log.created_at),
        }
        expected = _compute_hash(entry_data, prev_hash)
        if log.entry_hash != expected:
            return False
        prev_hash = log.entry_hash
    return True
