from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.database import get_db
from app.models.invoices import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.models.contacts import Customer
from app.models.banking import BankAccount

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    total_receivables = db.query(func.coalesce(func.sum(Invoice.balance_due), 0)).filter(
        Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL])
    ).scalar()

    overdue_count = db.query(func.count(Invoice.id)).filter(
        Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]),
        Invoice.due_date < func.current_date()
    ).scalar()

    customer_count = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar()

    recent_invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(5).all()
    recent_payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(5).all()

    bank_balances = db.query(BankAccount).filter(BankAccount.is_active == True).all()

    return {
        "total_receivables": float(total_receivables),
        "overdue_count": overdue_count,
        "customer_count": customer_count,
        "recent_invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_id": inv.customer_id,
                "total": float(inv.total),
                "balance_due": float(inv.balance_due),
                "status": inv.status.value,
                "date": inv.date.isoformat(),
            }
            for inv in recent_invoices
        ],
        "recent_payments": [
            {
                "id": p.id,
                "customer_id": p.customer_id,
                "amount": float(p.amount),
                "date": p.date.isoformat(),
                "method": p.method,
            }
            for p in recent_payments
        ],
        "bank_balances": [
            {"id": ba.id, "name": ba.name, "balance": float(ba.balance)}
            for ba in bank_balances
        ],
    }
