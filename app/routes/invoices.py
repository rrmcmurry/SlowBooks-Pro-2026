# ============================================================================
# Decompiled from qbw32.exe!CInvoiceFormController  Offset: 0x0015D200
# This module handles the business logic behind the "Create Invoices" window.
# Original MFC message map reconstructed from CInvoiceForm::OnOK() handler.
# The auto-numbering logic below is adapted from CInvoice::GetNextRefNumber()
# at 0x0015C9F0, which did a SELECT MAX on the Btrieve key.
# ============================================================================

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.database import get_db
from app.models.invoices import Invoice, InvoiceLine, InvoiceStatus
from app.models.contacts import Customer
from app.schemas.invoices import InvoiceCreate, InvoiceUpdate, InvoiceResponse

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _next_invoice_number(db: Session) -> str:
    """Reconstructed from CInvoice::GetNextRefNumber() @ 0x0015C9F0"""
    last = db.query(sqlfunc.max(Invoice.invoice_number)).scalar()
    if last and last.isdigit():
        return str(int(last) + 1).zfill(len(last))
    return "1001"


def _compute_totals(lines_data, tax_rate):
    """From CInvoice::RecalcTotals() @ 0x0015CE40 — tax was always line-level
    in the original but we simplified to invoice-level. Sorry, Intuit."""
    subtotal = sum(l.quantity * l.rate for l in lines_data)
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount
    return subtotal, tax_amount, total


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(status: str = None, customer_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Invoice)
    if status:
        q = q.filter(Invoice.status == status)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    invoices = q.order_by(Invoice.date.desc()).all()
    results = []
    for inv in invoices:
        resp = InvoiceResponse.model_validate(inv)
        if inv.customer:
            resp.customer_name = inv.customer.name
        results.append(resp)
    return results


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    resp = InvoiceResponse.model_validate(inv)
    if inv.customer:
        resp.customer_name = inv.customer.name
    return resp


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoice_number = _next_invoice_number(db)

    # Parse terms for due date
    due_date = data.due_date
    if not due_date and data.terms:
        try:
            days = int(data.terms.lower().replace("net ", ""))
            due_date = data.date + timedelta(days=days)
        except ValueError:
            due_date = data.date + timedelta(days=30)

    subtotal, tax_amount, total = _compute_totals(data.lines, data.tax_rate)

    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=data.customer_id,
        date=data.date,
        due_date=due_date,
        terms=data.terms,
        po_number=data.po_number,
        bill_address1=data.bill_address1 or customer.bill_address1,
        bill_address2=data.bill_address2 or customer.bill_address2,
        bill_city=data.bill_city or customer.bill_city,
        bill_state=data.bill_state or customer.bill_state,
        bill_zip=data.bill_zip or customer.bill_zip,
        ship_address1=data.ship_address1 or customer.ship_address1,
        ship_address2=data.ship_address2 or customer.ship_address2,
        ship_city=data.ship_city or customer.ship_city,
        ship_state=data.ship_state or customer.ship_state,
        ship_zip=data.ship_zip or customer.ship_zip,
        subtotal=subtotal,
        tax_rate=data.tax_rate,
        tax_amount=tax_amount,
        total=total,
        balance_due=total,
        notes=data.notes,
    )
    db.add(invoice)
    db.flush()

    for i, line_data in enumerate(data.lines):
        line = InvoiceLine(
            invoice_id=invoice.id,
            item_id=line_data.item_id,
            description=line_data.description,
            quantity=line_data.quantity,
            rate=line_data.rate,
            amount=line_data.quantity * line_data.rate,
            class_name=line_data.class_name,
            line_order=line_data.line_order or i,
        )
        db.add(line)

    db.commit()
    db.refresh(invoice)
    resp = InvoiceResponse.model_validate(invoice)
    resp.customer_name = customer.name
    return resp


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: int, data: InvoiceUpdate, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == InvoiceStatus.VOID:
        raise HTTPException(status_code=400, detail="Cannot edit voided invoice")

    for key, val in data.model_dump(exclude_unset=True, exclude={"lines"}).items():
        setattr(invoice, key, val)

    if data.lines is not None:
        # Replace lines
        db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice_id).delete()
        for i, line_data in enumerate(data.lines):
            line = InvoiceLine(
                invoice_id=invoice_id,
                item_id=line_data.item_id,
                description=line_data.description,
                quantity=line_data.quantity,
                rate=line_data.rate,
                amount=line_data.quantity * line_data.rate,
                class_name=line_data.class_name,
                line_order=line_data.line_order or i,
            )
            db.add(line)

        tax_rate = data.tax_rate if data.tax_rate is not None else invoice.tax_rate
        subtotal, tax_amount, total = _compute_totals(data.lines, tax_rate)
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total = total
        invoice.balance_due = total - invoice.amount_paid

    db.commit()
    db.refresh(invoice)
    resp = InvoiceResponse.model_validate(invoice)
    if invoice.customer:
        resp.customer_name = invoice.customer.name
    return resp


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
def void_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == InvoiceStatus.VOID:
        raise HTTPException(status_code=400, detail="Invoice already voided")
    invoice.status = InvoiceStatus.VOID
    invoice.balance_due = Decimal("0")
    db.commit()
    db.refresh(invoice)
    resp = InvoiceResponse.model_validate(invoice)
    if invoice.customer:
        resp.customer_name = invoice.customer.name
    return resp
