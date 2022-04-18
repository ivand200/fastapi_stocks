# TODO: implement Celery(priority--)
# TODO: implement RabbitMQ
# TODO: implement Docker
# TODO: implement Redis(priority-)
# TODO: implement logging
# TODO: implement Admin model


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
from fastapi import (
    FastAPI, Depends, HTTPException, 
    Security, Header, Response
)

from worker import tasks
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.security import (
    OAuth2PasswordBearer, 
    OAuth2PasswordRequestForm, 
    HTTPAuthorizationCredentials, 
    HTTPBearer
)
from passlib.context import CryptContext

from database import models, schemas
from database.db import SessionLocal, engine
from .defs import Momentum, DivP
from database.db import get_db

import csv
import logging
import sys
import redis

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler_format = logging.Formatter("%(asctime)s-%(message)s")
handler.setFormatter(handler_format)
logger.addHandler(handler)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# # Dependency
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = config("secret")
JWT_ALGORITH = config("algorithm")
r = redis.Redis(host=config("redis_host"), port=config("redis_port"), password=config("redis_password"))


def token_response(token: str):
    return {"access_token": token}


def signJWT(user_id: str):
    payload = { "user_id": user_id, "expires": time.time() + 600}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITH)
    return token_response(token)


def decodeJWT(token: str):
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITH])
        return decoded_token if decoded_token["expires"] >= time.time() else False
    except:
        return False


def check_user(user: schemas.UserInDB, db: Session = Depends(get_db)):
    """
    Check user in DB
    username and email
    """
    try:
        user_db = (
            db.query(models.User).
            filter(
                models.User.email == user.email, models.User.username == user.username
            )
            .first()
        )
        varify_password = pwd_context.verify(user.password, user_db.password)
        # user_db = db.query(models.User).filter(models.User.email == user.email, models.User.username == user.username).first()
        if user_db and varify_password:
            return True
        return False
    except:
        return False


@app.post("/user/signup", status_code=201)
async def create_user(user: schemas.UserInDB, db: Session = Depends(get_db)):
    """
    Signup new user
    return token
    """
    logger.info(f"User signup: {user.username}, {user.email}")
    username_check = (
        db.query(models.User)
        .filter(models.User.username == user.username)
        .first()
    )
    email_check = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )
    if username_check or email_check:
        raise HTTPException(
            status_code=400, detail="username or mail already exist"
        )
    hashed_password = pwd_context.hash(user.password)
    user_db = models.User(
        username=user.username, email=user.email, password=hashed_password
    )
    if user.role:
        user_db.role = user.role
    if user.id:
        user_db.id = user.id
    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return signJWT(user.email)


@app.post("/user/login", status_code=200)
async def user_login(user: schemas.UserInDB, db: Session = Depends(get_db)):
    """
    User login
    return token
    """
    logger.info(f"User login: {user.username}, {user.email}")
    if check_user(user, db):
        return signJWT(user.email)
    return HTTPException(status_code=403, detail="Unauthorized")


@app.delete("/user/{user_id}", status_code=200)
def user_delete(
    user_id: int,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
):
    """
    Delete user by id
    """
    token = decodeJWT(Authorization)
    user_db = db.query(models.User).filter(models.User.email == token["user_id"]).first()
    if not user_db.role == "admin":
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        logger.info(f"User to delete: {user_id}, by {user_db.email}")
        user_db = db.query(models.User).filter(models.User.id == user_id).delete()
        db.commit()
        return f"User with id: {user_id} was deleted."


# @app.get("/{index}", response_model = schemas.IndexDataBase)
# async def root(index: str, db: Session = Depends(get_db)):
#     query = (
#         db.query(models.Stock)
#         .join(models.Index)
#         .filter(models.Index.ticker == index)
#         .all()
#     )
#     result = schemas.IndexDataBase(ticker=index)
#     result.stocks = query
#     return result


@app.get("/stocks/{ticker}", response_model=schemas.StockBase, status_code=200)
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
            db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
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


@app.get("/index/best/{index}", response_model=schemas.IndexDataBase, status_code=200)
def best_stocks(
    index: str,
    response_model = schemas.IndexDataBase,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
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
            .order_by(models.Stock.momentum_avg.desc()).all()
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


@app.put("/index/update/{index}", status_code=200)
async def update_index(
    index: str, 
    db: Session = Depends(get_db), 
    Authorization: Optional[str] = Header(None)
):
    """
    Update stocks by index
    momentum_avg
    div_p
    """
    if not decodeJWT(Authorization):
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        index_db = db.query(models.Index).filter(models.Index.ticker == index).first()
        stocks_db = db.query(models.Stock).filter(models.Stock.index_id == index_db.id).all()
        for stock in stocks_db:
            momentum_avg = Momentum.get_momentum_avg(stock.ticker)
            div_p = DivP.get_div_p(stock.ticker)
            stock.momentum_avg = momentum_avg
            stock.div_p = div_p
            logger.info(f"Update stock: {stock.ticker}")
            redis_data = {"ticker": stock.ticker,"Momentum_avg": stock.momentum_avg, "Div_p": stock.div_p}
            r.set(stock.ticker, json.dumps(redis_data))
            db.commit()
            db.refresh(stock)
        return JSONResponse({"status": "ok"})


@app.delete("/index/update/{index}", status_code=200)
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


@app.post("/index/update/{index}", status_code=201)
async def populate_index(
    index: str,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
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


@app.put("/etf/update", status_code=204)
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
        r.set(item.ticker, item.momentum_12_1)
        logger.info(f"ETF update {item.ticker}")
    return "ETFs was updated"


@app.post("/etf/update", status_code=201)
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
            logger.info(f"Populate ETF: {etf.ticker}")
        db.commit()
    return JSONResponse("ETF was updated")


@app.delete("/etf/{etf}", status_code=200)
def delete_etf(
    etf: str,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None)
):
    token = decodeJWT(Authorization)
    user_db = db.query(models.User).filter(models.User.email == token["user_id"]).first()
    if not user_db.role == "admin":
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        etf_upper = etf.upper()
        etf_db = db.query(models.ETF).filter(models.ETF.ticker == etf_upper).delete()
        db.commit()
        logger.info(f"ETF was deleted: {etf_upper}")
        return f"{etf_upper} was deleted"

      
@app.get("/redis/")
def test_redis():
    result = r.get("MSFT")
    return json.loads(result)


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
