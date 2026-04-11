from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.database import get_db
from app.models.accounts import Account, AccountType
from app.models.transactions import TransactionLine
from app.models.invoices import Invoice, InvoiceStatus
from app.models.contacts import Customer

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/profit-loss")
def profit_loss(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()

    def get_account_totals(acct_type):
        results = (
            db.query(Account.name, Account.account_number,
                     sqlfunc.coalesce(sqlfunc.sum(TransactionLine.credit - TransactionLine.debit), 0))
            .join(TransactionLine, TransactionLine.account_id == Account.id)
            .join(TransactionLine.transaction)
            .filter(Account.account_type == acct_type)
            .filter(TransactionLine.transaction.has(date__gte=start_date))
            .filter(TransactionLine.transaction.has(date__lte=end_date))
            .group_by(Account.id, Account.name, Account.account_number)
            .all()
        )
        return [{"account_name": r[0], "account_number": r[1], "amount": float(r[2])} for r in results]

    income = get_account_totals(AccountType.INCOME)
    cogs = get_account_totals(AccountType.COGS)
    expenses = get_account_totals(AccountType.EXPENSE)

    total_income = sum(i["amount"] for i in income)
    total_cogs = sum(abs(c["amount"]) for c in cogs)
    total_expenses = sum(abs(e["amount"]) for e in expenses)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "income": income,
        "cogs": cogs,
        "expenses": expenses,
        "total_income": total_income,
        "total_cogs": total_cogs,
        "gross_profit": total_income - total_cogs,
        "total_expenses": total_expenses,
        "net_income": total_income - total_cogs - total_expenses,
    }


@router.get("/balance-sheet")
def balance_sheet(as_of_date: date = Query(default=None), db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = date.today()

    def get_balances(acct_type):
        results = (
            db.query(Account.name, Account.account_number,
                     sqlfunc.coalesce(sqlfunc.sum(TransactionLine.debit - TransactionLine.credit), 0))
            .join(TransactionLine, TransactionLine.account_id == Account.id)
            .filter(Account.account_type == acct_type)
            .group_by(Account.id, Account.name, Account.account_number)
            .all()
        )
        return [{"account_name": r[0], "account_number": r[1], "amount": float(r[2])} for r in results]

    assets = get_balances(AccountType.ASSET)
    liabilities = get_balances(AccountType.LIABILITY)
    equity = get_balances(AccountType.EQUITY)

    total_assets = sum(a["amount"] for a in assets)
    total_liabilities = sum(abs(l["amount"]) for l in liabilities)
    total_equity = sum(abs(e["amount"]) for e in equity)

    return {
        "as_of_date": as_of_date.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
    }


@router.get("/ar-aging")
def ar_aging(as_of_date: date = Query(default=None), db: Session = Depends(get_db)):
    if not as_of_date:
        as_of_date = date.today()

    invoices = (
        db.query(Invoice)
        .filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]))
        .filter(Invoice.balance_due > 0)
        .all()
    )

    aging = {}
    for inv in invoices:
        cid = inv.customer_id
        if cid not in aging:
            cname = db.query(Customer.name).filter(Customer.id == cid).scalar() or "Unknown"
            aging[cid] = {
                "customer_name": cname, "customer_id": cid,
                "current": Decimal(0), "over_30": Decimal(0),
                "over_60": Decimal(0), "over_90": Decimal(0), "total": Decimal(0),
            }

        days = (as_of_date - inv.due_date).days if inv.due_date else 0
        bal = inv.balance_due
        if days <= 0:
            aging[cid]["current"] += bal
        elif days <= 30:
            aging[cid]["over_30"] += bal
        elif days <= 60:
            aging[cid]["over_60"] += bal
        else:
            aging[cid]["over_90"] += bal
        aging[cid]["total"] += bal

    items = list(aging.values())
    totals = {
        "customer_name": "TOTAL", "customer_id": 0,
        "current": sum(i["current"] for i in items),
        "over_30": sum(i["over_30"] for i in items),
        "over_60": sum(i["over_60"] for i in items),
        "over_90": sum(i["over_90"] for i in items),
        "total": sum(i["total"] for i in items),
    }
    # Convert Decimals to float for JSON
    for item in items:
        for k in ("current", "over_30", "over_60", "over_90", "total"):
            item[k] = float(item[k])
    for k in ("current", "over_30", "over_60", "over_90", "total"):
        totals[k] = float(totals[k])

    return {"as_of_date": as_of_date.isoformat(), "items": items, "totals": totals}
