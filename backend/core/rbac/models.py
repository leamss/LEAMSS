"""RBAC Pydantic Models for the new collections"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class Department(BaseModel):
    """Org department (e.g. admin, sales, hr)"""
    id: str
    key: str  # unique slug
    name: str
    icon: str  # Lucide icon name
    color: str  # hex
    description: Optional[str] = None
    head_user_id: Optional[str] = None
    is_active: bool = True
    is_system: bool = True
    created_at: datetime


class Permission(BaseModel):
    """Master permission catalog entry. key = {resource}.{action}.{scope}"""
    id: str
    key: str
    resource: str
    action: str
    scope: str
    display_name: str
    description: str
    category: str
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    requires_2fa: bool = False
    audit_log_required: bool = False
    is_system: bool = True
    created_at: datetime


class Role(BaseModel):
    """Role definition — bundle of permissions + UI modules"""
    id: str
    key: str
    name: str
    user_type: Literal["internal", "external", "client"]
    department: Optional[str] = None  # FK to departments.key
    hierarchy_level: int = Field(ge=0, le=6)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    ui_modules: List[str] = Field(default_factory=list)
    reports_to_roles: List[str] = Field(default_factory=list)
    can_manage_roles: List[str] = Field(default_factory=list)
    is_system: bool = True
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


class Team(BaseModel):
    """Optional grouping inside a department"""
    id: str
    name: str
    department: str
    manager_id: Optional[str] = None
    member_ids: List[str] = Field(default_factory=list)
    monthly_target: Optional[float] = None
    region: Optional[str] = None
    specialization: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class UserRoleHistory(BaseModel):
    """Audit trail of role changes per user"""
    id: str
    user_id: str
    changed_from: Optional[str] = None
    changed_to: str
    changed_by: str
    reason: Optional[str] = None
    effective_date: datetime
    created_at: datetime
