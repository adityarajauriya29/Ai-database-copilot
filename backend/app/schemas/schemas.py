from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# Auth schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @validator("username")
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not v.isalnum() and "_" not in v:
            raise ValueError("Username must be alphanumeric")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    preferred_mode: str
    created_at: datetime

    class Config:
        from_attributes = True


# Connection schemas
class ConnectionCreate(BaseModel):
    name: str
    db_type: str  # postgresql, mysql, sqlite
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None
    is_readonly: bool = True


class ConnectionResponse(BaseModel):
    id: int
    name: str
    db_type: str
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    username: Optional[str]
    is_active: bool
    is_readonly: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Query schemas
class QueryRequest(BaseModel):
    natural_language: str
    connection_id: int
    session_id: Optional[str] = None
    mode: str = "simple"  # simple, learning, developer
    language: str = "en"

    @validator("natural_language")
    def validate_query(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Query too short")
        if len(v) > 2000:
            raise ValueError("Query too long (max 2000 chars)")
        return v.strip()


class AlternativeQuery(BaseModel):
    sql: str
    explanation: str
    rank: int
    reason: str


class QueryResponse(BaseModel):
    id: Optional[int]
    natural_language: str
    generated_sql: str
    explanation: str
    confidence_score: float
    optimization_score: float
    risk_level: str
    risk_score: float
    risk_reasons: List[str]
    query_type: str
    estimated_rows: Optional[int]
    estimated_time_ms: Optional[float]
    alternatives: List[AlternativeQuery]
    optimization_tips: List[str]
    learning_tips: Optional[List[str]]
    clauses_explained: Optional[Dict[str, str]]
    warnings: List[str]
    share_token: Optional[str]


class ExecuteRequest(BaseModel):
    query_id: int
    confirm: bool = False


class ExecuteResponse(BaseModel):
    success: bool
    rows: Optional[List[Dict[str, Any]]] = []
    columns: Optional[List[str]] = []
    rows_affected: Optional[int] = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None


# History schemas
class QueryHistoryResponse(BaseModel):
    id: int
    natural_language: str
    generated_sql: Optional[str]
    confidence_score: Optional[float]
    risk_level: str
    status: str
    query_type: Optional[str]
    rows_returned: Optional[int]
    execution_time_ms: Optional[float]
    is_favorite: bool
    share_token: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
