"""
Settings Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.models import SystemSetting, UserRole
from core.auth import get_current_user, require_role
from core.schemas import SystemSettings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=dict)
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system settings"""
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    
    # Convert to dict
    settings_dict = {}
    for s in settings:
        if s.setting_type == "boolean":
            settings_dict[s.setting_key] = s.setting_value.lower() == "true"
        elif s.setting_type == "number":
            settings_dict[s.setting_key] = float(s.setting_value) if s.setting_value else 0
        else:
            settings_dict[s.setting_key] = s.setting_value
    
    # Default values if not set
    if "allow_case_manager_workflow_customization" not in settings_dict:
        settings_dict["allow_case_manager_workflow_customization"] = False
    
    return settings_dict


@router.put("", response_model=dict)
async def update_settings(
    settings: SystemSettings,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Update system settings (Admin only)"""
    # Update workflow customization setting
    result = await db.execute(
        select(SystemSetting)
        .where(SystemSetting.setting_key == "allow_case_manager_workflow_customization")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.setting_value = str(settings.allow_case_manager_workflow_customization).lower()
        setting.updated_by = current_user["id"]
    else:
        setting = SystemSetting(
            setting_key="allow_case_manager_workflow_customization",
            setting_value=str(settings.allow_case_manager_workflow_customization).lower(),
            setting_type="boolean",
            description="Allow case managers to customize workflow steps",
            updated_by=current_user["id"]
        )
        db.add(setting)
    
    await db.commit()
    
    return {
        "message": "Settings updated successfully",
        "allow_case_manager_workflow_customization": settings.allow_case_manager_workflow_customization
    }
