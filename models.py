from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

# MongoDB models using Pydantic

# =========================
# USER
# =========================
class User(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: str
    password: str
    role: str = "client"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True  # ✅ V2 syntax
        json_encoders = {ObjectId: str}

# =========================
# RFP
# =========================
class RFP(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    approximate_budget: Optional[float] = None
    due_date: Optional[datetime] = None
    attachment_url: Optional[str] = None
    status: str = "draft"

    user_id: str  # MongoDB ObjectId as string
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # AI Analysis
    internal_rfp_score: float = 0.0
    spec_match_score: float = 0.0
    win_probability: float = 0.0

    extracted_specs: Dict[str, Any] = Field(default_factory=dict)
    financial_analysis: Dict[str, Any] = Field(default_factory=dict)

    recommendation: str = ""
    recommendation_reason: str = ""
    suggestions: List[str] = Field(default_factory=list)

    agent_status: str = "idle"  # idle | processing | completed

    # Demo/Sample Status
    demo_status: str = "none"  # none | requested | scheduled | completed | accepted | rejected

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# QUALIFICATION RULE
# =========================
class QualificationRule(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    description: Optional[str] = None

    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    min_spec_match_percent: float = 0.0
    min_days_before_deadline: Optional[int] = None

    allowed_client_types: List[str] = Field(default_factory=list)

    reject_if_testing_cost_above: Optional[float] = None
    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# PRODUCT PRICE
# =========================
class ProductPrice(BaseModel):
    sku_id: str = Field(..., alias="_id")  # Use sku_id as primary key
    sku_name: str
    base_unit_price: float
    currency: str = "USD"

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# TEST PRICE
# =========================
class TestPrice(BaseModel):
    test_code: str = Field(..., alias="_id")  # Use test_code as primary key
    test_name: str
    test_price: float
    currency: str = "USD"

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# NOTIFICATION
# =========================
class Notification(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    rfp_id: Optional[str] = None
    message: str
    type: str = "ai_result"  # ai_result, system, etc.
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# DEMO CENTER
# =========================
class DemoCenter(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    location: str  # City, State/Country
    address: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    available_slots: List[str] = Field(default_factory=list)  # e.g., ["2025-01-15 10:00", "2025-01-15 14:00"]
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# DEMO REQUEST
# =========================
class DemoRequest(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    rfp_id: Optional[str] = None
    user_id: str
    preferred_location: str  # City or center name
    preferred_date: Optional[datetime] = None
    special_requirements: Optional[str] = None
    status: str = "requested"  # requested, scheduled, completed, cancelled
    scheduled_center_id: Optional[str] = None
    scheduled_datetime: Optional[datetime] = None
    admin_notes: Optional[str] = None
    client_feedback: Optional[str] = None
    final_decision: Optional[str] = None  # accept, reject
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# =========================
# CRON JOB CONFIG
# =========================
class CronJobConfig(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    enabled: bool = False
    schedule_type: str  # "interval" or "count_based"
    interval_minutes: Optional[int] = None
    min_pending_rfps: Optional[int] = None
    last_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
