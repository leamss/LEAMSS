"""Payment Router — Stripe Checkout for Client Payments"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from core.database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

sales_col = db["sales"]
payment_transactions_col = db["payment_transactions"]
notifications_col = db["notifications"]

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")


class PaymentRequest(BaseModel):
    sale_id: str
    origin_url: str


@router.get("/my-proposals")
async def get_my_proposals(current_user: dict = Depends(get_current_user)):
    """Get all sales/proposals for the current client with payment info"""
    # Find sales where client_email matches
    client_email = current_user["email"]
    sales = await sales_col.find(
        {"client_email": client_email},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    # Enrich with product and payment info
    products_col = db["products"]
    users_col = db["users"]
    for sale in sales:
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1, "category": 1})
        if product:
            sale["product_name"] = product.get("name", "Unknown")
            sale["product_category"] = product.get("category", "")
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "name": 1})
        if partner:
            sale["partner_name"] = partner.get("name", "Unknown")

        # Get payment transactions for this sale
        transactions = await payment_transactions_col.find(
            {"sale_id": sale["id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        sale["payment_transactions"] = transactions

        # Calculate pending_amount if not present
        if sale.get("pending_amount") is None:
            fee = sale.get("fee_amount", 0) or 0
            received = sale.get("amount_received", 0) or 0
            sale["pending_amount"] = round(fee - received, 2)

        # Serialize datetime
        for field in ["created_at", "approved_at", "collection_deadline"]:
            if field in sale and sale[field] and hasattr(sale[field], 'isoformat'):
                sale[field] = sale[field].isoformat()

    return sales


@router.post("/create-checkout")
async def create_checkout(request: PaymentRequest, http_request: Request, current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for a sale's pending amount"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    sale = await sales_col.find_one({"id": request.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Sale must be approved before payment")

    # Calculate pending amount from server-side data (NEVER trust frontend amount)
    pending = round(sale.get("pending_amount", 0), 2)
    if pending <= 0:
        raise HTTPException(status_code=400, detail="No pending amount to pay")

    # Build dynamic URLs from origin
    origin = request.origin_url.rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/payment-cancel?sale_id={request.sale_id}"

    # Create Stripe checkout session
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    host_url = str(http_request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    # Amount in float for Stripe (INR)
    amount_float = float(pending)

    checkout_request = CheckoutSessionRequest(
        amount=amount_float,
        currency="inr",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "sale_id": request.sale_id,
            "client_email": sale.get("client_email", ""),
            "client_name": sale.get("client_name", ""),
            "product_id": sale.get("product_id", ""),
            "user_id": current_user["id"]
        }
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    # Create payment transaction record BEFORE redirect
    transaction = {
        "id": str(uuid.uuid4()),
        "sale_id": request.sale_id,
        "session_id": session.session_id,
        "user_id": current_user["id"],
        "client_email": sale.get("client_email", ""),
        "amount": amount_float,
        "currency": "inr",
        "status": "initiated",
        "payment_status": "pending",
        "metadata": {
            "client_name": sale.get("client_name", ""),
            "product_id": sale.get("product_id", "")
        },
        "created_at": datetime.now(timezone.utc)
    }
    await payment_transactions_col.insert_one(transaction)

    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def get_payment_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Poll payment status for a checkout session"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    transaction = await payment_transactions_col.find_one({"session_id": session_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If already processed, return cached status
    if transaction.get("payment_status") in ["paid", "failed"]:
        return {
            "status": transaction.get("status"),
            "payment_status": transaction.get("payment_status"),
            "amount": transaction.get("amount"),
            "sale_id": transaction.get("sale_id")
        }

    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")

    checkout_status = await stripe_checkout.get_checkout_status(session_id)

    # Update transaction
    new_status = checkout_status.status
    new_payment_status = checkout_status.payment_status
    update_data = {
        "status": new_status,
        "payment_status": new_payment_status,
        "updated_at": datetime.now(timezone.utc)
    }
    await payment_transactions_col.update_one({"session_id": session_id}, {"$set": update_data})

    # If payment successful, update the sale
    if new_payment_status == "paid":
        await _process_successful_payment(transaction["sale_id"], transaction["amount"], session_id)

    return {
        "status": new_status,
        "payment_status": new_payment_status,
        "amount": transaction.get("amount"),
        "sale_id": transaction.get("sale_id")
    }


async def _process_successful_payment(sale_id: str, amount: float, session_id: str):
    """Update sale after successful payment — idempotent (won't double-count)"""
    # Check if this session was already processed
    existing = await payment_transactions_col.find_one(
        {"session_id": session_id, "processed": True}, {"_id": 0}
    )
    if existing:
        return  # Already processed

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        return

    new_received = round((sale.get("amount_received", 0) or 0) + amount, 2)
    new_pending = round(sale.get("fee_amount", 0) - new_received, 2)
    if new_pending < 0:
        new_pending = 0

    pay_status = "paid" if new_pending <= 0 else "partial"
    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2)

    # Add to payment history
    payment_entry = {
        "amount": amount,
        "method": "stripe_online",
        "reference": session_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "recorded_by": "system_stripe"
    }

    await sales_col.update_one({"id": sale_id}, {
        "$set": {
            "amount_received": new_received,
            "pending_amount": new_pending,
            "payment_status": pay_status,
            "commission_amount": new_commission
        },
        "$push": {"payment_history": payment_entry}
    })

    # Mark as processed to prevent double-counting
    await payment_transactions_col.update_one({"session_id": session_id}, {"$set": {"processed": True}})

    # Notify admin
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": "admin",
        "title": "Online Payment Received",
        "message": f"₹{amount:,.0f} received for sale of {sale.get('client_name', 'Unknown')} via Stripe",
        "type": "payment_received",
        "related_id": sale_id,
        "read": False,
        "created_at": datetime.now(timezone.utc)
    })


@router.get("/history/{sale_id}")
async def get_payment_history(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Get payment transaction history for a sale"""
    transactions = await payment_transactions_col.find(
        {"sale_id": sale_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    for t in transactions:
        if "created_at" in t and hasattr(t["created_at"], "isoformat"):
            t["created_at"] = t["created_at"].isoformat()
        if "updated_at" in t and hasattr(t["updated_at"], "isoformat"):
            t["updated_at"] = t["updated_at"].isoformat()

    return transactions


RECEIPTS_DIR = "/app/uploads/receipts"
os.makedirs(RECEIPTS_DIR, exist_ok=True)


def _generate_receipt_pdf(sale: dict, transaction: dict, filename: str):
    """Generate a professional branded payment receipt PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=25, bottomMargin=25, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()

    brand_color = colors.HexColor('#2a777a')
    accent_color = colors.HexColor('#f7620b')
    light_bg = colors.HexColor('#f0f9f9')

    company_style = ParagraphStyle('Company', parent=styles['Heading1'], fontSize=22, textColor=brand_color, alignment=TA_CENTER, spaceAfter=2)
    tagline_style = ParagraphStyle('Tagline', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=6)
    receipt_title = ParagraphStyle('ReceiptTitle', parent=styles['Heading2'], fontSize=16, textColor=accent_color, alignment=TA_CENTER, spaceAfter=4)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#666666'))
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#222222'), fontName='Helvetica-Bold')
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

    elements = []

    # Logo Header
    logo_path = "/app/backend/uploads/leamss-logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=180, height=80)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("LEAMSS Immigration Services", company_style))

    elements.append(Paragraph("Ladhani Education & Migration Services Pvt. Ltd", tagline_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=brand_color, spaceAfter=12))
    elements.append(Paragraph("PAYMENT RECEIPT", receipt_title))
    elements.append(Spacer(1, 8))

    # Receipt meta
    receipt_no = f"REC-{transaction.get('id', 'N/A')[:8].upper()}"
    txn_date = transaction.get('created_at', '')
    if hasattr(txn_date, 'strftime'):
        txn_date_str = txn_date.strftime('%d %b %Y, %I:%M %p')
    elif isinstance(txn_date, str):
        try:
            txn_date_str = datetime.fromisoformat(txn_date.replace('Z', '+00:00')).strftime('%d %b %Y, %I:%M %p')
        except (ValueError, TypeError):
            txn_date_str = str(txn_date)
    else:
        txn_date_str = datetime.now().strftime('%d %b %Y, %I:%M %p')

    meta_data = [
        [Paragraph('Receipt No:', label_style), Paragraph(receipt_no, value_style),
         Paragraph('Date:', label_style), Paragraph(txn_date_str, value_style)],
        [Paragraph('Payment Method:', label_style), Paragraph('Online (Stripe)', value_style),
         Paragraph('Transaction ID:', label_style), Paragraph(transaction.get('session_id', 'N/A')[:20] + '...', value_style)],
    ]
    meta_table = Table(meta_data, colWidths=[90, 170, 90, 170])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Client Info
    elements.append(Paragraph("Client Information", ParagraphStyle('SectionHead', parent=styles['Heading3'], fontSize=12, textColor=brand_color, spaceAfter=6)))
    client_data = [
        [Paragraph('Name:', label_style), Paragraph(sale.get('client_name', 'N/A'), value_style)],
        [Paragraph('Email:', label_style), Paragraph(sale.get('client_email', 'N/A'), value_style)],
        [Paragraph('Mobile:', label_style), Paragraph(sale.get('client_mobile', 'N/A'), value_style)],
        [Paragraph('Service:', label_style), Paragraph(sale.get('product_name', 'N/A'), value_style)],
    ]
    client_table = Table(client_data, colWidths=[80, 440])
    client_table.setStyle(TableStyle([
        ('PADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#e0e0e0')),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 15))

    # Fee Breakdown
    elements.append(Paragraph("Fee Breakdown", ParagraphStyle('SectionHead', parent=styles['Heading3'], fontSize=12, textColor=brand_color, spaceAfter=6)))

    fee_rows = []
    has_discount = (sale.get('total_discount_amount', 0) or 0) > 0
    original_fee = sale.get('fee_before_discount', sale.get('fee_amount', 0)) or sale.get('fee_amount', 0)

    if has_discount:
        fee_rows.append(['Original Service Fee', f"INR {original_fee:,.2f}"])
        if (sale.get('promo_discount_amount', 0) or 0) > 0:
            fee_rows.append([f"Promo Code ({sale.get('promo_code', '')})", f"- INR {sale['promo_discount_amount']:,.2f}"])
        if (sale.get('additional_discount_percentage', 0) or 0) > 0:
            fee_rows.append([f"Special Discount ({sale['additional_discount_percentage']}%)", f"- INR {sale.get('additional_discount_amount', 0):,.2f}"])
        fee_rows.append(['', ''])  # separator
    fee_rows.append(['Net Service Fee', f"INR {sale.get('fee_amount', 0):,.2f}"])

    fee_table = Table(fee_rows, colWidths=[320, 200])
    fee_style = [
        ('PADDING', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, -1), (-1, -1), 1, brand_color),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), brand_color),
    ]
    if has_discount:
        for i, row in enumerate(fee_rows):
            if row[0].startswith('Promo') or row[0].startswith('Special'):
                fee_style.append(('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#16a34a')))
    fee_table.setStyle(TableStyle(fee_style))
    elements.append(fee_table)
    elements.append(Spacer(1, 15))

    # Payment Summary
    elements.append(Paragraph("Payment Summary", ParagraphStyle('SectionHead', parent=styles['Heading3'], fontSize=12, textColor=brand_color, spaceAfter=6)))

    txn_amount = transaction.get('amount', 0)
    total_received = sale.get('amount_received', 0) or 0
    total_fee = sale.get('fee_amount', 0) or 0
    pending = max(0, round(total_fee - total_received, 2))

    payment_rows = [
        ['This Payment', f"INR {txn_amount:,.2f}"],
        ['Total Amount Paid', f"INR {total_received:,.2f}"],
        ['Remaining Balance', f"INR {pending:,.2f}"],
    ]
    pay_table = Table(payment_rows, colWidths=[320, 200])
    pay_style = [
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fff3e0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), accent_color),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#e0e0e0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]
    if pending <= 0:
        pay_style.append(('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#16a34a')))
    else:
        pay_style.append(('TEXTCOLOR', (0, -1), (-1, -1), accent_color))
    pay_table.setStyle(TableStyle(pay_style))
    elements.append(pay_table)

    if pending <= 0:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("FULLY PAID", ParagraphStyle('Paid', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#16a34a'), alignment=TA_CENTER)))

    elements.append(Spacer(1, 25))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8))

    # Footer
    elements.append(Paragraph("This is a system-generated receipt. No signature required.", small_style))
    elements.append(Paragraph("Ladhani Education & Migration Services Pvt. Ltd | support@leamss.com", small_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y at %I:%M %p')}", small_style))

    doc.build(elements)
    return filename


@router.get("/receipt/{transaction_id}")
async def download_receipt(transaction_id: str, current_user: dict = Depends(get_current_user)):
    """Download a PDF receipt for a specific payment transaction"""
    from fastapi.responses import FileResponse

    transaction = await payment_transactions_col.find_one({"id": transaction_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.get("payment_status") != "paid":
        raise HTTPException(status_code=400, detail="Receipt available only for completed payments")

    sale = await sales_col.find_one({"id": transaction["sale_id"]}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # Enrich sale with product name
    products_col = db["products"]
    product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
    if product:
        sale["product_name"] = product.get("name", "N/A")

    filename = os.path.join(RECEIPTS_DIR, f"receipt_{transaction_id[:8]}.pdf")
    _generate_receipt_pdf(sale, transaction, filename)

    receipt_name = f"LEAMSS_Receipt_{transaction_id[:8].upper()}.pdf"
    return FileResponse(filename, media_type="application/pdf", filename=receipt_name)


@router.get("/receipt-by-sale/{sale_id}")
async def download_sale_receipt(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Download a combined receipt for all paid transactions of a sale"""
    from fastapi.responses import FileResponse

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # Get the latest paid transaction
    transaction = await payment_transactions_col.find_one(
        {"sale_id": sale_id, "payment_status": "paid"},
        {"_id": 0}
    )

    if not transaction:
        # Create a virtual transaction for manual payments
        transaction = {
            "id": f"MANUAL-{sale_id[:8]}",
            "session_id": "Manual Payment",
            "amount": sale.get("amount_received", 0),
            "created_at": sale.get("approved_at", sale.get("created_at", datetime.now(timezone.utc))),
            "payment_status": "paid"
        }

    products_col = db["products"]
    product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
    if product:
        sale["product_name"] = product.get("name", "N/A")

    filename = os.path.join(RECEIPTS_DIR, f"receipt_sale_{sale_id[:8]}.pdf")
    _generate_receipt_pdf(sale, transaction, filename)

    receipt_name = f"LEAMSS_Receipt_{sale_id[:8].upper()}.pdf"
    return FileResponse(filename, media_type="application/pdf", filename=receipt_name)
