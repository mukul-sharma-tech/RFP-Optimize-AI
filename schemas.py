from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# class UserCreate(BaseModel):
#     email: EmailStr
#     password: str
#     role: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        populate_by_name = True

class RFPCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    approximate_budget: Optional[float] = None
    due_date: Optional[datetime] = None
    attachment_url: Optional[str] = None

class RFPUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    approximate_budget: Optional[float] = None
    due_date: Optional[datetime] = None
    attachment_url: Optional[str] = None
    status: Optional[str] = None

class RFPResponse(BaseModel):
    id: str = Field(..., alias="_id")
    title: str
    description: Optional[str]
    project_type: Optional[str]
    approximate_budget: Optional[float]
    due_date: Optional[datetime]
    attachment_url: Optional[str]
    status: str
    user_id: str
    created_at: datetime

    # AI Fields
    internal_rfp_score: float
    spec_match_score: float
    win_probability: float
    extracted_specs: Optional[Dict[str, Any]]
    financial_analysis: Optional[Dict[str, Any]]
    recommendation: str = ""
    recommendation_reason: str = ""
    suggestions: List[str] = []
    agent_status: str
    demo_status: str

    class Config:
        populate_by_name = True

class RFPList(BaseModel):
    rfps: List[RFPResponse]

class QualificationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    min_spec_match_percent: Optional[float] = 0.0
    min_days_before_deadline: Optional[int] = None
    allowed_client_types: Optional[List[str]] = []
    reject_if_testing_cost_above: Optional[float] = None

class QualificationRuleResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str]
    min_budget: Optional[float]
    max_budget: Optional[float]
    min_spec_match_percent: float
    min_days_before_deadline: Optional[int]
    allowed_client_types: List[str]
    reject_if_testing_cost_above: Optional[float]
    is_active: bool
    created_at: datetime

    class Config:
        populate_by_name = True

class ProductPriceResponse(BaseModel):
    sku_id: str = Field(..., alias="_id")
    sku_name: str
    base_unit_price: float
    currency: str

    class Config:
        populate_by_name = True

class TestPriceResponse(BaseModel):
    test_code: str = Field(..., alias="_id")
    test_name: str
    test_price: float
    currency: str

    class Config:
        populate_by_name = True

# New schemas for additional features
class NotificationResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    rfp_id: Optional[str] = None
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        populate_by_name = True

class CronJobConfigCreate(BaseModel):
    name: str
    enabled: bool = False
    schedule_type: str  # "interval" or "count_based"
    interval_minutes: Optional[int] = None
    min_pending_rfps: Optional[int] = None

class CronJobConfigResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    enabled: bool
    schedule_type: str
    interval_minutes: Optional[int]
    min_pending_rfps: Optional[int]
    last_run: Optional[datetime]
    created_at: datetime

    class Config:
        populate_by_name = True

# Demo/Sample Schemas
class DemoCenterResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    location: str
    address: str
    contact_phone: Optional[str]
    contact_email: Optional[str]
    available_slots: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        populate_by_name = True

class DemoRequestCreate(BaseModel):
    preferred_location: str
    preferred_date: Optional[datetime] = None
    special_requirements: Optional[str] = None

class DemoRequestResponse(BaseModel):
    id: str = Field(..., alias="_id")
    rfp_id: Optional[str] = None
    user_id: str
    preferred_location: str
    preferred_date: Optional[datetime]
    special_requirements: Optional[str]
    status: str
    scheduled_center_id: Optional[str]
    scheduled_datetime: Optional[datetime]
    admin_notes: Optional[str]
    client_feedback: Optional[str]
    final_decision: Optional[str]
    created_at: datetime

    class Config:
        populate_by_name = True

class DemoScheduleCreate(BaseModel):
    center_id: str
    scheduled_datetime: datetime
    admin_notes: Optional[str] = None

class DemoDecisionCreate(BaseModel):
    final_decision: str
    feedback: Optional[str] = None