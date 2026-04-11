from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.banking import BankAccount, BankTransaction, Reconciliation
from app.schemas.banking import (
    BankAccountCreate, BankAccountUpdate, BankAccountResponse,
    BankTransactionCreate, BankTransactionResponse,
    ReconciliationCreate, ReconciliationResponse,
)

router = APIRouter(prefix="/api/banking", tags=["banking"])


# Bank Accounts
@router.get("/accounts", response_model=list[BankAccountResponse])
def list_bank_accounts(db: Session = Depends(get_db)):
    return db.query(BankAccount).filter(BankAccount.is_active == True).order_by(BankAccount.name).all()


@router.get("/accounts/{account_id}", response_model=BankAccountResponse)
def get_bank_account(account_id: int, db: Session = Depends(get_db)):
    ba = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return ba


@router.post("/accounts", response_model=BankAccountResponse, status_code=201)
def create_bank_account(data: BankAccountCreate, db: Session = Depends(get_db)):
    ba = BankAccount(**data.model_dump())
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return ba


@router.put("/accounts/{account_id}", response_model=BankAccountResponse)
def update_bank_account(account_id: int, data: BankAccountUpdate, db: Session = Depends(get_db)):
    ba = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(ba, key, val)
    db.commit()
    db.refresh(ba)
    return ba


# Bank Transactions
@router.get("/transactions", response_model=list[BankTransactionResponse])
def list_bank_transactions(bank_account_id: int = None, db: Session = Depends(get_db)):
    q = db.query(BankTransaction)
    if bank_account_id:
        q = q.filter(BankTransaction.bank_account_id == bank_account_id)
    return q.order_by(BankTransaction.date.desc()).all()


@router.post("/transactions", response_model=BankTransactionResponse, status_code=201)
def create_bank_transaction(data: BankTransactionCreate, db: Session = Depends(get_db)):
    ba = db.query(BankAccount).filter(BankAccount.id == data.bank_account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")

    txn = BankTransaction(**data.model_dump())
    ba.balance += data.amount
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


# Reconciliations — stub for Phase 4
@router.get("/reconciliations", response_model=list[ReconciliationResponse])
def list_reconciliations(bank_account_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Reconciliation)
    if bank_account_id:
        q = q.filter(Reconciliation.bank_account_id == bank_account_id)
    return q.order_by(Reconciliation.statement_date.desc()).all()


@router.post("/reconciliations", response_model=ReconciliationResponse, status_code=201)
def create_reconciliation(data: ReconciliationCreate, db: Session = Depends(get_db)):
    recon = Reconciliation(**data.model_dump())
    db.add(recon)
    db.commit()
    db.refresh(recon)
    return recon
