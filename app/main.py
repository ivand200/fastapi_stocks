import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from base64 import decode
from statistics import mode
from tabnanny import check
from typing import List
from webbrowser import get
import json

import time
from typing import Dict, Optional

import jwt
from decouple import config

from starlette import status

from worker import tasks
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.security import (
    OAuth2PasswordBearer, 
    OAuth2PasswordRequestForm, 
    HTTPAuthorizationCredentials, 
    HTTPBearer,
)
from passlib.context import CryptContext

from database import models, schemas
from .defs import Momentum, DivP
from database.db import get_db, engine

# from app.routers import app
from fastapi import APIRouter, Depends, HTTPException, Security, Header, Response
from app.auth import decodeJWT

import csv
import logging
import sys
import redis

router_stocks = APIRouter()


logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler_format = logging.Formatter("%(asctime)s-%(message)s")
handler.setFormatter(handler_format)
logger.addHandler(handler)

models.Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = config("secret")
JWT_ALGORITH = config("algorithm")
r = redis.Redis(
    host=config("redis_host"),
    port=config("redis_port"),
    password=config("redis_password")
)

scheduler = BackgroundScheduler()


@router_stocks.get("/dj30/{ticker}", response_model=schemas.StockBase, status_code=200)
def get_stock(
    ticker: str,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
):
    """
    Get information by ticker
    """
    if not decodeJWT(Authorization):
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        db_stock = (
            db.query(models.Stock)
            .join(models.Index)
            .filter(models.Index.id == 1, models.Stock.ticker == ticker)
            .first()
        )
        if db_stock is None:
            raise HTTPException(status_code=404, detail="Stock not found")
        stock = schemas.StockBase(
            name=db_stock.name,
            ticker=db_stock.ticker,
            momentum_avg=db_stock.momentum_avg,
            div_p=db_stock.div_p,
        )
        logger.info(f"Stock by ticker: {stock.name}, {stock.ticker}")
        return stock


@router_stocks.get("/index/{index}", response_model=schemas.IndexDataBase, status_code=200)
def best_stocks(
    index: str,
    response_model = schemas.IndexDataBase,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None),
):
    """
    Get information about best stocks from index
    sorted by momentum_avg
    """
    if not decodeJWT(Authorization):
        raise HTTPException(status_code=401, detail="Acces denied")
    else:  
        index_db = db.query(models.Index).filter(models.Index.ticker == index).first()
        logger.info(f"best stocks from {index_db.ticker}")
        stocks_db = (
            db.query(models.Stock)
            .join(models.Index)
            .filter(models.Index.ticker == index)
            .order_by(models.Stock.momentum_avg.desc())
            .all()
            )
        result = schemas.IndexDataBase(ticker=index_db.ticker, stocks=stocks_db)
        return result

    # index = db.query(models.Index).filter(models.Index.ticker == index).first()
    # best_stocks = (
    #     db.query(models.Stock)
    #     .join(models.Index)
    #     .filter(models.Index.id == index.id)
    #     .order_by(models.Stock.momentum_avg.desc())
    # )
    # stock_serializer = [schemas.StockBase(**i.__dict__) for i in best_stocks.all()]
    # return stock_serializer


@router_stocks.put("/index/dj30", status_code=200)
async def update_index(
    stock: schemas.StockBase, 
    db: Session = Depends(get_db), 
    Authorization: Optional[str] = Header(None),
):
    """
    Stocks updates
    momentum_avg
    div_p
    """
    if not decodeJWT(Authorization):
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        stock_db = (
            db.query(models.Stock)
            .join(models.Index)
            .filter(models.Index.id == 1, models.Stock.ticker == stock.ticker)
            .first()
        )
        stock_db.momentum_avg = stock.momentum_avg
        stock_db.div_p = stock.div_p
        logger.info(f"Update stock: {stock.ticker}")
        db.commit()
        db.refresh(stock_db)
        return JSONResponse(f"{stock} was updated")


      # index_db = (
      #     db.query(models.Index).filter(models.Index.ticker == index).first()
      # )
      # stocks_db = (
      #     db.query(models.Stock).filter(models.Stock.index_id == index_db.id).all()
      # )
      # for stock in stocks_db:
      #     momentum_avg = Momentum.get_momentum_avg(stock.ticker)
      #     div_p = DivP.get_div_p(stock.ticker)
      #     stock.momentum_avg = momentum_avg
      #     stock.div_p = div_p
      #     logger.info(f"Update stock: {stock.ticker}")
#
      #     redis_data = {
      #         "ticker": stock.ticker,
      #         "Momentum_avg": stock.momentum_avg,
      #         "Div_p": stock.div_p
      #     }
      #     r.set(stock.ticker, json.dumps(redis_data))
      #     db.commit()
      #     db.refresh(stock)
      # return JSONResponse({"status": "ok"})

      
@router_stocks.delete("/index/{index}", status_code=200)
def delete_index(
    index: str,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
):
    """
    Delete all stocks by index
    """
    token = decodeJWT(Authorization)
    user_db = db.query(models.User).filter(models.User.email == token["user_id"]).first()
    if not user_db.role == "admin":
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        index_id = db.query(models.Index).filter(models.Index.ticker == index).first()
        logger.info(f"Index to delete: {index_id.ticker}")
        index = db.query(models.Stock).filter(models.Stock.index_id == index_id.id).delete()
        db.commit()
        return JSONResponse(f"all stocks from index {index} was deleted")

    # if not decodeJWT(Authorization):
    #     raise HTTPException(status_code=401, detail="Acces denied")
    # else:
    #     index_id = db.query(models.Index).filter(models.Index.ticker == index).first()
    #     index = db.query(models.Stock).filter(models.Stock.index_id == index_id.id).delete()
    #     db.commit()
    #     return JSONResponse(f"all stocks from index {index} was deleted")


@router_stocks.post("/index/{index}", status_code=201)
async def populate_index(
    index: str,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None),
):
    """
    Populate stocks by
    index,
    ticker,
    name
    """
    index_db = db.query(models.Index).filter(models.Index.ticker == index).first()
    with open(f"data/{index}.csv", newline="") as f:
        file = csv.reader(f)
        next(file)
        for row in file:
            ticker = row[0]
            name = row[1]
            stock = models.Stock(ticker=ticker, name=name, index_id=index_db.id)
            db.add(stock)
            logger.info(f"Pupolate stock: {index_db.ticker}, {stock.ticker}")
        db.commit()
    return JSONResponse(f"{index} was populated")


# 
# @app.get("/redis/")
# def test_redis():
#     result = r.get("MSFT")
#     return json.loads(result)
# 
# 
# @app.post("/repeat")
# def test_repeat():
#     sec = datetime.datetime.now()
#     logger.info(f"test celery: {sec}")
#     return {"seconds": f"{sec.second}"}

# if __name__ == "__main__":
#     uvicorn.run(app="app.main:app", host="0.0.0.0", port=80)

# @app.get("/redis/")
# def test_redis():
#     result = r.get("MSFT")
#     return json.loads(result)
# 
# 
# @app.get("/celery")
# def test_celery():
#     result = tasks.dj30_update()
#     return {"status": "ok"}
# 
# 
# @app.post("/celery/2")
# def test_celery_2():
#     with open("log.txt", "w") as f:
#         f.write("test log: ")
#         print("Check")
