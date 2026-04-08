"""PDF Report Generation Router"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from core.database import sales_col, users_col, cases_col, products_col, db
information_sheets_col = db["information_sheets"]
from core.auth import get_current_user
from datetime import datetime, timezone, timedelta
import os
import uuid

router = APIRouter(prefix="/reports/export", tags=["Reports Export"])

REPORTS_DIR = "/app/uploads/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


def _generate_sales_pdf(sales_data, title, filename):
    """Generate a sales report PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#2a777a'))
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=10, textColor=colors.grey)
    elements = []

    # Logo Header
    logo_path = "/app/backend/uploads/leamss-logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=160, height=70)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("LEAMSS Immigration Services", title_style))

    elements.append(Paragraph(title, styles['Heading2']))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %b %Y, %I:%M %p')}", subtitle_style))
    elements.append(Spacer(1, 15))

    # Summary
    total_fee = sum(s.get('fee_amount', 0) for s in sales_data)
    total_received = sum(s.get('amount_received', 0) for s in sales_data)
    total_commission = sum(s.get('commission_amount', 0) for s in sales_data)
    total_pending = total_fee - total_received

    summary_data = [
        ['Total Sales', str(len(sales_data))],
        ['Total Fee', f'INR {total_fee:,.0f}'],
        ['Amount Received', f'INR {total_received:,.0f}'],
        ['Pending Amount', f'INR {total_pending:,.0f}'],
        ['Total Commission', f'INR {total_commission:,.0f}'],
    ]
    summary_table = Table(summary_data, colWidths=[150, 200])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f9f9')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Sales table
    if sales_data:
        elements.append(Paragraph("Sales Details", styles['Heading3']))
        elements.append(Spacer(1, 8))
        header = ['Client', 'Product', 'Fee (INR)', 'Received', 'Commission', 'Status']
        rows = [header]
        for s in sales_data[:100]:
            rows.append([
                s.get('client_name', '')[:20],
                s.get('product_name', '')[:20],
                f"{s.get('fee_amount', 0):,.0f}",
                f"{s.get('amount_received', 0):,.0f}",
                f"{s.get('commission_amount', 0):,.0f}",
                s.get('status', '').title()
            ])
        table = Table(rows, colWidths=[90, 90, 80, 80, 80, 60])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a777a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ]))
        elements.append(table)

    doc.build(elements)
    return filename


def _generate_commission_pdf(data, title, filename):
    """Generate a commission report PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#2a777a'))
    elements = []

    # Logo Header
    logo_path = "/app/backend/uploads/leamss-logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=160, height=70)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("LEAMSS Immigration Services", title_style))

    elements.append(Paragraph(title, styles['Heading2']))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 15))

    if data:
        header = ['Partner', 'Total Sales', 'Revenue (INR)', 'Commission (INR)']
        rows = [header]
        total_comm = 0
        for p in data:
            rows.append([
                p.get('partner_name', ''),
                str(p.get('total_sales', 0)),
                f"{p.get('total_fee', 0):,.0f}",
                f"{p.get('total_commission', 0):,.0f}",
            ])
            total_comm += p.get('total_commission', 0)
        rows.append(['TOTAL', '', '', f"{total_comm:,.0f}"])
        table = Table(rows, colWidths=[150, 80, 120, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a777a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f9f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ]))
        elements.append(table)

    doc.build(elements)
    return filename


@router.get("/sales-report")
async def export_sales_report(
    status: str = Query(None),
    period: str = Query("all"),
    current_user: dict = Depends(get_current_user)
):
    """Export sales report as PDF"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin only")

    query = {}
    if status:
        query["status"] = status

    sales = await sales_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)

    # Enrich with product names
    product_ids = list({s.get("product_id") for s in sales if s.get("product_id")})
    products = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500) if product_ids else []
    products_map = {p["id"]: p.get("name", "") for p in products}
    for s in sales:
        s["product_name"] = products_map.get(s.get("product_id"), "Unknown")

    filename = os.path.join(REPORTS_DIR, f"sales_report_{uuid.uuid4().hex[:8]}.pdf")
    title = f"Sales Report — {status.title() if status else 'All Sales'}"
    _generate_sales_pdf(sales, title, filename)

    return FileResponse(filename, media_type="application/pdf",
                        filename=f"LEAMSS_Sales_Report_{datetime.now().strftime('%Y%m%d')}.pdf")


@router.get("/commission-report")
async def export_commission_report(current_user: dict = Depends(get_current_user)):
    """Export partner commission report as PDF"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin only")

    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {
            "_id": "$partner_id",
            "total_sales": {"$sum": 1},
            "total_fee": {"$sum": "$fee_amount"},
            "total_commission": {"$sum": "$commission_amount"}
        }}
    ]
    results = []
    async for item in sales_col.aggregate(pipeline):
        partner = await users_col.find_one({"id": item["_id"]}, {"_id": 0, "password": 0})
        results.append({
            "partner_name": partner["name"] if partner else "Unknown",
            "total_sales": item["total_sales"],
            "total_fee": item["total_fee"],
            "total_commission": item["total_commission"]
        })

    filename = os.path.join(REPORTS_DIR, f"commission_report_{uuid.uuid4().hex[:8]}.pdf")
    _generate_commission_pdf(results, "Partner Commission Report", filename)

    return FileResponse(filename, media_type="application/pdf",
                        filename=f"LEAMSS_Commission_Report_{datetime.now().strftime('%Y%m%d')}.pdf")


@router.get("/partner-sales")
async def export_partner_sales(partner_id: str = Query(None), current_user: dict = Depends(get_current_user)):
    """Export sales report for a specific partner"""
    pid = partner_id or current_user["id"]
    if current_user["role"] not in ["admin", "partner"]:
        raise HTTPException(status_code=403, detail="Admin or Partner only")
    if current_user["role"] == "partner":
        pid = current_user["id"]

    sales = await sales_col.find({"partner_id": pid}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    partner = await users_col.find_one({"id": pid}, {"_id": 0, "password": 0})
    pname = partner["name"] if partner else "Unknown"

    product_ids = list({s.get("product_id") for s in sales if s.get("product_id")})
    products = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500) if product_ids else []
    products_map = {p["id"]: p.get("name", "") for p in products}
    for s in sales:
        s["product_name"] = products_map.get(s.get("product_id"), "Unknown")

    filename = os.path.join(REPORTS_DIR, f"partner_sales_{uuid.uuid4().hex[:8]}.pdf")
    _generate_sales_pdf(sales, f"Sales Report — {pname}", filename)

    return FileResponse(filename, media_type="application/pdf",
                        filename=f"LEAMSS_{pname}_Sales_{datetime.now().strftime('%Y%m%d')}.pdf")



@router.get("/sale-receipt/{sale_id}")
async def admin_download_sale_receipt(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Admin download receipt PDF for any sale"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin only")

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
    if product:
        sale["product_name"] = product.get("name", "N/A")

    # Build receipt using payments router's generator
    from routers.payments import _generate_receipt_pdf, RECEIPTS_DIR, payment_transactions_col

    txn = await payment_transactions_col.find_one(
        {"sale_id": sale_id, "payment_status": "paid"}, {"_id": 0}
    )
    if not txn:
        txn = {
            "id": f"ADMIN-{sale_id[:8]}",
            "session_id": sale.get("payment_reference", "Manual"),
            "amount": sale.get("amount_received", 0),
            "created_at": sale.get("approved_at", sale.get("created_at", datetime.now(timezone.utc))),
            "payment_status": "paid"
        }

    filename = os.path.join(RECEIPTS_DIR, f"admin_receipt_{sale_id[:8]}.pdf")
    _generate_receipt_pdf(sale, txn, filename)

    return FileResponse(filename, media_type="application/pdf",
                        filename=f"LEAMSS_Receipt_{sale['client_name'].replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf")


@router.get("/info-sheet/{case_id}")
async def export_info_sheet_pdf(case_id: str, current_user: dict = Depends(get_current_user)):
    """Export information sheet as a branded PDF"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    sheet = await information_sheets_col.find_one({"case_id": case_id}, {"_id": 0})
    if not sheet:
        raise HTTPException(status_code=404, detail="No information sheet found for this case")

    # Get client name
    client = await users_col.find_one({"id": case.get("client_id")}, {"_id": 0, "name": 1})
    client_name = client.get("name", "Client") if client else "Client"

    filename = os.path.join(REPORTS_DIR, f"info_sheet_{case_id[:8]}.pdf")
    _generate_info_sheet_pdf(sheet, client_name, case.get("case_id", ""), filename)

    return FileResponse(filename, media_type="application/pdf",
                        filename=f"LEAMSS_InfoSheet_{client_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf")


def _generate_info_sheet_pdf(data, client_name, case_number, filename):
    """Generate a branded info sheet PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=25, bottomMargin=25, leftMargin=35, rightMargin=35)
    styles = getSampleStyleSheet()

    brand_color = colors.HexColor('#2a777a')
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13, textColor=brand_color, spaceAfter=6, spaceBefore=12)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

    elements = []

    # Logo Header
    logo_path = "/app/backend/uploads/leamss-logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=160, height=70)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 4))

    elements.append(Paragraph("Required Information Sheet", ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=brand_color, alignment=TA_CENTER)))
    elements.append(Paragraph(f"Client: {client_name} | Case: {case_number}", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=colors.grey, alignment=TA_CENTER)))
    elements.append(HRFlowable(width="100%", thickness=2, color=brand_color, spaceAfter=10))

    # PERSONAL DETAILS
    personal_fields = [
        ("Given Name(s)", "given_names"), ("Family Name", "family_name"), ("Other Names", "other_names"),
        ("Gender", "gender"), ("Date of Birth", "date_of_birth"), ("Country of Birth", "country_of_birth"),
        ("City/Town of Birth", "city_of_birth"), ("Address", "address"), ("Email", "email"),
        ("Contact Number", "contact_number"), ("Alternative Number", "alternative_number"),
        ("Aadhaar Number", "aadhaar_number"), ("Nationality", "nationality"),
        ("Passport No.", "passport_number"), ("Passport Issue Date", "passport_issue_date"),
        ("Passport Expiry Date", "passport_expiry_date"), ("Passport Place of Issue", "passport_place_of_issue"),
        ("Marital Status", "marital_status"), ("Spouse Name", "spouse_name"),
        ("Father's Name", "father_name"), ("Mother's Name", "mother_name"),
    ]
    elements.append(Paragraph("1. PERSONAL DETAILS", section_style))
    _add_field_table(elements, data, personal_fields, styles)

    # FAMILY CHART
    family_fields = [
        ("Father's DOB", "father_dob"), ("Father's Place of Birth", "father_place_of_birth"),
        ("Mother's DOB", "mother_dob"), ("Mother's Place of Birth", "mother_place_of_birth"),
        ("Siblings Details", "siblings_details"), ("Date of Marriage", "date_of_marriage"),
        ("Spouse DOB", "spouse_dob"), ("Spouse Place of Birth", "spouse_place_of_birth"),
        ("Spouse Passport No.", "spouse_passport_number"), ("Spouse Passport Issue", "spouse_passport_issue_date"),
        ("Spouse Passport Expiry", "spouse_passport_expiry_date"), ("Spouse Passport Place", "spouse_passport_place"),
    ]
    elements.append(Paragraph("2. FAMILY CHART", section_style))
    _add_field_table(elements, data, family_fields, styles)

    # REPEATABLE SECTIONS
    repeatable_sections = [
        ("3. DEPENDENT CHILDREN", "child", [("Name", "name"), ("DOB", "dob"), ("Gender", "gender"), ("Place of Birth", "place_of_birth"), ("Passport No.", "passport_number"), ("Migrating?", "migrating")]),
        ("4. MIGRATING DEPENDENTS", "dependent", [("Full Name", "full_name"), ("Relation", "relation"), ("Gender", "gender"), ("Migrating?", "migrating_with_you"), ("Residing Country", "residing_country")]),
        ("5. QUALIFICATIONS", "qualification", [("Qualification", "name"), ("Field of Study", "field_of_study"), ("Institute", "institute_name"), ("Course Length", "course_length"), ("Start Date", "start_date"), ("End Date", "end_date"), ("Study Mode", "study_mode")]),
        ("6. EMPLOYMENT HISTORY", "employment", [("Company", "business_name"), ("Job Title", "job_title"), ("Address", "address"), ("Start Date", "start_date"), ("End Date", "end_date"), ("Hours/Week", "working_hours")]),
    ]

    for title, prefix, fields in repeatable_sections:
        elements.append(Paragraph(title, section_style))
        entry_found = False
        for i in range(1, 21):
            entry_prefix = f"{prefix}_{i}"
            has_data = any(data.get(f"{entry_prefix}_{f[1]}") for f in fields)
            if not has_data:
                continue
            entry_found = True
            elements.append(Paragraph(f"  Entry #{i}", ParagraphStyle('Entry', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#555555'), fontName='Helvetica-Bold', spaceBefore=4)))
            entry_fields = [(label, f"{entry_prefix}_{key}") for label, key in fields]
            _add_field_table(elements, data, entry_fields, styles)
        if not entry_found:
            elements.append(Paragraph("  No entries", ParagraphStyle('Empty', parent=styles['Normal'], fontSize=9, textColor=colors.grey, fontName='Helvetica-Oblique')))

    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceAfter=6))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y %H:%M')} | Ladhani Education & Migration Services Pvt. Ltd", small_style))

    doc.build(elements)


def _add_field_table(elements, data, fields, styles):
    """Add a 2-column label-value table for fields"""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Spacer

    table_data = []
    row = []
    for i, (label, key) in enumerate(fields):
        val = data.get(key, "")
        if val and str(val).strip() and str(val) != "null" and str(val) != "None":
            val = str(val).strip()
        else:
            val = "-"
        row.append(f"{label}: {val}")
        if len(row) == 3 or i == len(fields) - 1:
            while len(row) < 3:
                row.append("")
            table_data.append(row)
            row = []

    if table_data:
        col_w = 175
        t = Table(table_data, colWidths=[col_w, col_w, col_w])
        t.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))
