from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.database import get_db
from app.models.estimates import Estimate, EstimateLine, EstimateStatus
from app.models.contacts import Customer
from app.schemas.estimates import EstimateCreate, EstimateUpdate, EstimateResponse

router = APIRouter(prefix="/api/estimates", tags=["estimates"])


def _next_estimate_number(db: Session) -> str:
    last = db.query(sqlfunc.max(Estimate.estimate_number)).scalar()
    if last and last.isdigit():
        return str(int(last) + 1).zfill(len(last))
    return "E-1001"


@router.get("", response_model=list[EstimateResponse])
def list_estimates(status: str = None, customer_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Estimate)
    if status:
        q = q.filter(Estimate.status == status)
    if customer_id:
        q = q.filter(Estimate.customer_id == customer_id)
    estimates = q.order_by(Estimate.date.desc()).all()
    results = []
    for est in estimates:
        resp = EstimateResponse.model_validate(est)
        if est.customer:
            resp.customer_name = est.customer.name
        results.append(resp)
    return results


@router.get("/{estimate_id}", response_model=EstimateResponse)
def get_estimate(estimate_id: int, db: Session = Depends(get_db)):
    est = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    resp = EstimateResponse.model_validate(est)
    if est.customer:
        resp.customer_name = est.customer.name
    return resp


@router.post("", response_model=EstimateResponse, status_code=201)
def create_estimate(data: EstimateCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    estimate_number = _next_estimate_number(db)
    subtotal = sum(l.quantity * l.rate for l in data.lines)
    tax_amount = subtotal * data.tax_rate
    total = subtotal + tax_amount

    estimate = Estimate(
        estimate_number=estimate_number,
        customer_id=data.customer_id,
        date=data.date,
        expiration_date=data.expiration_date,
        subtotal=subtotal,
        tax_rate=data.tax_rate,
        tax_amount=tax_amount,
        total=total,
        notes=data.notes,
    )
    db.add(estimate)
    db.flush()

    for i, line_data in enumerate(data.lines):
        line = EstimateLine(
            estimate_id=estimate.id,
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
    db.refresh(estimate)
    resp = EstimateResponse.model_validate(estimate)
    resp.customer_name = customer.name
    return resp


@router.put("/{estimate_id}", response_model=EstimateResponse)
def update_estimate(estimate_id: int, data: EstimateUpdate, db: Session = Depends(get_db)):
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    for key, val in data.model_dump(exclude_unset=True, exclude={"lines"}).items():
        setattr(estimate, key, val)

    if data.lines is not None:
        db.query(EstimateLine).filter(EstimateLine.estimate_id == estimate_id).delete()
        for i, line_data in enumerate(data.lines):
            line = EstimateLine(
                estimate_id=estimate_id,
                item_id=line_data.item_id,
                description=line_data.description,
                quantity=line_data.quantity,
                rate=line_data.rate,
                amount=line_data.quantity * line_data.rate,
                class_name=line_data.class_name,
                line_order=line_data.line_order or i,
            )
            db.add(line)

        tax_rate = data.tax_rate if data.tax_rate is not None else estimate.tax_rate
        subtotal = sum(l.quantity * l.rate for l in data.lines)
        estimate.subtotal = subtotal
        estimate.tax_amount = subtotal * tax_rate
        estimate.total = subtotal + estimate.tax_amount

    db.commit()
    db.refresh(estimate)
    resp = EstimateResponse.model_validate(estimate)
    if estimate.customer:
        resp.customer_name = estimate.customer.name
    return resp


@router.post("/{estimate_id}/convert", response_model=dict)
def convert_to_invoice(estimate_id: int, db: Session = Depends(get_db)):
    """Convert estimate to invoice — placeholder for Phase 3"""
    raise HTTPException(status_code=501, detail="Convert to invoice not yet implemented")
