"""
Commission calculation service for LEAMSS Portal
"""
from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any


def get_applicable_commission(product: dict, sale_date: str = None) -> Tuple[float, str, List[Dict[str, Any]]]:
    """
    Get the applicable commission rate and type based on the sale date.
    Returns (commission_rate, commission_type, commission_tiers)
    
    If sale_date is provided and commission history exists, find the rate that was effective at that date.
    """
    if not sale_date:
        sale_date = datetime.now(timezone.utc).isoformat()
    
    # Default to current values
    commission_rate = product.get("commission_rate", 0)
    commission_type = product.get("commission_type", "fixed")
    commission_tiers = product.get("commission_tiers", [])
    
    # Check if there's commission history
    commission_history = product.get("commission_history", [])
    if not commission_history:
        return commission_rate, commission_type, commission_tiers
    
    # Parse sale date
    try:
        if isinstance(sale_date, str):
            if 'T' in sale_date:
                sale_datetime = datetime.fromisoformat(sale_date.replace('Z', '+00:00'))
            else:
                sale_datetime = datetime.strptime(sale_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            sale_datetime = sale_date
    except (ValueError, TypeError, AttributeError):
        return commission_rate, commission_type, commission_tiers
    
    # Find the applicable commission based on effective_from dates
    sorted_history = sorted(
        commission_history, 
        key=lambda x: x.get("effective_from", "1970-01-01"), 
        reverse=True
    )
    
    for entry in sorted_history:
        effective_from = entry.get("effective_from", "")
        try:
            if 'T' in effective_from:
                effective_datetime = datetime.fromisoformat(effective_from.replace('Z', '+00:00'))
            else:
                effective_datetime = datetime.strptime(effective_from, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            if sale_datetime >= effective_datetime:
                return (
                    entry.get("new_rate", commission_rate),
                    entry.get("new_type", commission_type),
                    entry.get("new_tiers", commission_tiers)
                )
        except (ValueError, TypeError, AttributeError):
            continue
    
    # Check for previous rate before all history
    if sorted_history:
        oldest_entry = sorted_history[-1]
        oldest_effective = oldest_entry.get("effective_from", "")
        try:
            if 'T' in oldest_effective:
                oldest_datetime = datetime.fromisoformat(oldest_effective.replace('Z', '+00:00'))
            else:
                oldest_datetime = datetime.strptime(oldest_effective, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            if sale_datetime < oldest_datetime:
                return (
                    oldest_entry.get("previous_rate", commission_rate),
                    oldest_entry.get("previous_type", commission_type),
                    oldest_entry.get("previous_tiers", commission_tiers)
                )
        except (ValueError, TypeError, AttributeError):
            pass
    
    return commission_rate, commission_type, commission_tiers
