from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    natural_language = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    risk_level = Column(String, default="low")
    risk_score = Column(Float, default=0.0)
    execution_time_ms = Column(Float, nullable=True)
    rows_affected = Column(Integer, nullable=True)
    rows_returned = Column(Integer, nullable=True)
    query_type = Column(String, nullable=True)  # SELECT, INSERT, UPDATE, DELETE
    status = Column(String, default="pending")  # pending, executed, failed, blocked
    error_message = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    optimization_score = Column(Float, nullable=True)
    alternatives = Column(JSON, nullable=True)
    share_token = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    session_id = Column(String, nullable=True)  # for conversation context

    user = relationship("User", back_populates="queries")
    connection = relationship("DatabaseConnection", back_populates="queries")


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    db_type = Column(String, nullable=False)  # postgresql, mysql, sqlite
    host = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    database = Column(String, nullable=True)
    username = Column(String, nullable=True)
    encrypted_password = Column(String, nullable=True)
    connection_string = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_readonly = Column(Boolean, default=True)
    schema_cache = Column(JSON, nullable=True)
    schema_cached_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="connections")
    queries = relationship("QueryHistory", back_populates="connection")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    prev_hash = Column(String, nullable=True)  # chain hash for tamper-evidence
    entry_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
