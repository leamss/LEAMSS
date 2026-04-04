"""Service Comparison Calculator & Testimonials & Cross-Sell & Leaderboard Router"""
from fastapi import APIRouter, HTTPException, Depends, Query
from core.database import db
from core.auth import get_current_user
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/marketing-tools", tags=["marketing-tools"])
testimonials_col = db["testimonials"]
cross_sell_col = db["cross_sell_recommendations"]
products_col = db["products"]
sales_col = db["sales"]
users_col = db["users"]


# ===================== SERVICE CALCULATOR =====================

@router.post("/calculator/assess")
async def assess_eligibility(data: dict):
    """Public endpoint — assess immigration eligibility based on profile"""
    age = data.get("age", 30)
    education = data.get("education", "bachelors")
    work_experience = data.get("work_experience_years", 0)
    language_score = data.get("language_score", 6.0)
    country_interest = data.get("country_of_interest", "")
    
    # Fetch active products
    products = await products_col.find({"status": "active"}, {"_id": 0}).to_list(50)
    
    recommendations = []
    for product in products:
        score = 0
        reasons = []
        pname = product["name"].lower()
        
        # Age scoring
        if age <= 35:
            score += 25
            reasons.append("Age is within ideal range (under 35)")
        elif age <= 45:
            score += 15
            reasons.append("Age is acceptable")
        else:
            score += 5
            reasons.append("Age may affect eligibility")
        
        # Education scoring
        edu_scores = {"phd": 30, "masters": 25, "bachelors": 20, "diploma": 15, "high_school": 5}
        score += edu_scores.get(education, 10)
        reasons.append(f"Education: {education.replace('_', ' ').title()}")
        
        # Work experience
        if work_experience >= 5:
            score += 25
            reasons.append(f"{work_experience}+ years work experience (excellent)")
        elif work_experience >= 3:
            score += 20
            reasons.append(f"{work_experience} years work experience (good)")
        elif work_experience >= 1:
            score += 10
            reasons.append(f"{work_experience} year(s) work experience")
        
        # Language score (IELTS-like 0-9 scale)
        if language_score >= 7.5:
            score += 20
            reasons.append(f"Language score {language_score} (excellent)")
        elif language_score >= 6.5:
            score += 15
            reasons.append(f"Language score {language_score} (good)")
        elif language_score >= 6.0:
            score += 10
            reasons.append(f"Language score {language_score} (acceptable)")
        
        # Country match bonus
        if country_interest and country_interest.lower() in pname:
            score += 10
            reasons.append(f"Matches your country interest: {country_interest}")
        
        # Determine eligibility category
        if score >= 70:
            eligibility = "high"
            label = "Highly Eligible"
        elif score >= 50:
            eligibility = "medium"
            label = "Likely Eligible"
        elif score >= 30:
            eligibility = "low"
            label = "May Be Eligible"
        else:
            eligibility = "unlikely"
            label = "Unlikely Eligible"
        
        recommendations.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "description": product.get("description", ""),
            "base_fee": product.get("base_fee", 0),
            "score": min(score, 100),
            "eligibility": eligibility,
            "eligibility_label": label,
            "reasons": reasons,
            "estimated_timeline": product.get("processing_time", "3-6 months")
        })
    
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "profile_summary": {
            "age": age,
            "education": education,
            "work_experience": work_experience,
            "language_score": language_score,
            "country_of_interest": country_interest
        },
        "recommendations": recommendations,
        "top_recommendation": recommendations[0] if recommendations else None
    }


# ===================== TESTIMONIALS =====================

@router.get("/testimonials")
async def get_testimonials(status: str = Query("published")):
    """Public endpoint — get published testimonials"""
    query = {}
    if status != "all":
        query["status"] = status
    testimonials = await testimonials_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    for t in testimonials:
        for f in ["created_at", "updated_at"]:
            if isinstance(t.get(f), datetime):
                t[f] = t[f].isoformat()
    return testimonials


@router.post("/testimonials")
async def create_testimonial(data: dict, current_user: dict = Depends(get_current_user)):
    """Create a testimonial (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    testimonial = {
        "id": str(uuid.uuid4()),
        "client_name": data.get("client_name", ""),
        "client_country": data.get("client_country", ""),
        "service_used": data.get("service_used", ""),
        "rating": data.get("rating", 5),
        "text": data.get("text", ""),
        "image_url": data.get("image_url", ""),
        "video_url": data.get("video_url", ""),
        "status": data.get("status", "published"),
        "featured": data.get("featured", False),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await testimonials_col.insert_one(testimonial)
    return {"message": "Testimonial created", "id": testimonial["id"]}


@router.put("/testimonials/{testimonial_id}")
async def update_testimonial(testimonial_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    data.pop("id", None)
    data.pop("_id", None)
    data["updated_at"] = datetime.now(timezone.utc)
    await testimonials_col.update_one({"id": testimonial_id}, {"$set": data})
    return {"message": "Testimonial updated"}


@router.delete("/testimonials/{testimonial_id}")
async def delete_testimonial(testimonial_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await testimonials_col.delete_one({"id": testimonial_id})
    return {"message": "Testimonial deleted"}


# ===================== CROSS-SELL RECOMMENDATIONS =====================

@router.get("/cross-sell/{client_id}")
async def get_cross_sell(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get cross-sell recommendations for a client based on their current services"""
    client_sales = await sales_col.find(
        {"client_id": client_id, "status": "approved"}, {"_id": 0}
    ).to_list(20)
    
    purchased_product_ids = {s.get("product_id") for s in client_sales}
    all_products = await products_col.find({"status": "active"}, {"_id": 0}).to_list(50)
    
    recommendations = []
    for product in all_products:
        if product["id"] in purchased_product_ids:
            continue
        
        # Score relevance based on what they already bought
        relevance = "medium"
        reason = "Expand your immigration portfolio"
        
        for sale in client_sales:
            sold_name = sale.get("product_name", "").lower()
            prod_name = product["name"].lower()
            
            if "pr" in sold_name and ("spouse" in prod_name or "dependent" in prod_name or "family" in prod_name):
                relevance = "high"
                reason = "Your PR is approved — bring your family!"
            elif "pr" in sold_name and "citizenship" in prod_name:
                relevance = "high"
                reason = "Next step after PR: Citizenship!"
            elif "student" in sold_name and ("work" in prod_name or "pr" in prod_name):
                relevance = "high"
                reason = "After studies, stay and work!"
            elif "work" in sold_name and "pr" in prod_name:
                relevance = "high"
                reason = "Convert your work permit to PR!"
        
        recommendations.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "description": product.get("description", ""),
            "base_fee": product.get("base_fee", 0),
            "relevance": relevance,
            "reason": reason
        })
    
    recommendations.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["relevance"]])
    return recommendations


# ===================== PARTNER LEADERBOARD =====================

@router.get("/leaderboard")
async def get_leaderboard(period: str = Query("all_time"), current_user: dict = Depends(get_current_user)):
    """Get partner performance leaderboard"""
    if current_user["role"] not in ["admin", "partner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    partners = await users_col.find({"role": "partner", "status": "active"}, {"_id": 0}).to_list(100)
    
    leaderboard = []
    for partner in partners:
        sales = await sales_col.find(
            {"partner_id": partner["id"], "status": {"$in": ["approved", "completed"]}}, {"_id": 0}
        ).to_list(500)
        
        total_sales = len(sales)
        total_revenue = sum(s.get("amount_inr", s.get("amount", 0)) for s in sales)
        total_commission = sum(s.get("commission_amount", 0) for s in sales)
        pending = await sales_col.count_documents({"partner_id": partner["id"], "status": "pending"})
        
        conversion_rate = round(total_sales / (total_sales + pending) * 100 if (total_sales + pending) > 0 else 0, 1)
        
        leaderboard.append({
            "partner_id": partner["id"],
            "partner_name": partner.get("name", "Unknown"),
            "email": partner.get("email", ""),
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_commission": total_commission,
            "pending_sales": pending,
            "conversion_rate": conversion_rate,
            "tier": "gold" if total_sales >= 20 else "silver" if total_sales >= 10 else "bronze"
        })
    
    leaderboard.sort(key=lambda x: x["total_revenue"], reverse=True)
    
    for idx, entry in enumerate(leaderboard):
        entry["rank"] = idx + 1
    
    return leaderboard
