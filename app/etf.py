import sys
import csv
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, Header, Response
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from decouple import config

from database import models, schemas
from database.db import get_db
from .defs import Momentum
from .auth import decodeJWT


etf_logger = logging.getLogger()
etf_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler_format = logging.Formatter("%(asctime)s-%(message)s")
handler.setFormatter(handler_format)
etf_logger.addHandler(handler)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = config("secret")
JWT_ALGORITH = config("algorithm")

router_etf = APIRouter()

@router_etf.get("/{ticker}", tags=["etf"])
async def etf_get(ticker: str, db: Session = Depends(get_db)):
    """
    Get information about ETF by ticker
    """
    etf_logger.info(f"etf ticker {ticker}")
    ticker_upper = ticker.upper()
    etf = db.query(models.ETF).filter(models.ETF.ticker == ticker_upper).first()
    etf_serializer = schemas.ETFBase(ticker=etf.ticker, momentum_12_1=etf.momentum_12_1)
    return etf_serializer


@router_etf.put("/update", tags=["etf"], status_code=204)
async def eft_update(db: Session = Depends(get_db)):
    """
    Update ETF
    momentum_12_1
    """
    etfs = db.query(models.ETF).all()
    for item in etfs:
        momentum = Momentum.get_momentum_12_1(item.ticker)
        item.momentum_12_1 = momentum
        db.commit()
        db.refresh(item)
        # r.set(item.ticker, item.momentum_12_1)
        etf_logger.info(f"ETF update {item.ticker}")
    return "ETFs was updated"


@router_etf.post("/create", tags=["etf"], status_code=201)
async def etf_create(db: Session = Depends(get_db)):
    """
    Create ETF
    Populate
    """
    with open(f"data/etf.csv", newline="") as f:
        file = csv.reader(f)
        next(file)
        for row in file:
            ticker = row[0]
            momentum = Momentum.get_momentum_12_1(row[0])
            etf = models.ETF(ticker=ticker, momentum_12_1=momentum)
            db.add(etf)
            etf_logger.info(f"Populate ETF: {etf.ticker}")
        db.commit()
    return JSONResponse("ETF was updated")


@router_etf.delete("/{etf}", tags=["etf"], status_code=200)
def delete_etf(
    etf: str,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
):
    """
    Delete ETF by ticker
    """
    token = decodeJWT(Authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Acces denied")
    user_db = db.query(models.User).filter(models.User.email == token["user_id"]).first()
    if not user_db.role == "admin":
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        etf_upper = etf.upper()
        etf_db = db.query(models.ETF).filter(models.ETF.ticker == etf_upper).delete()
        db.commit()
        etf_logger.info(f"ETF was deleted: {etf_upper}")
        return f"{etf_upper} was deleted"