from app import routers
from fastapi.testclient import TestClient
from database import models
from passlib.context import CryptContext
from database.db import SessionLocal, engine
from sqlalchemy.orm import Session
from fastapi import Depends
import pytest

import json


client = TestClient(routers.app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_admin_token():
    payload = {
        "username": "test_admin",
        "email": "admin@domain.com",
        "password": "testPass"
    }
    response = client.post("/auth/user/login", data=json.dumps(payload))
    response_body = response.json()
    TOKEN = response_body["access_token"]
    return TOKEN


def get_token():
    payload = {
        "username": "test_user1",
        "email": "test@mail.com1",
        "password": "testPass"
    }
    response = client.post("/auth/user/login", data=json.dumps(payload))
    response_body = response.json()
    TOKEN = response_body["access_token"]
    
    return TOKEN


def test_auth_app():
    payload = {
        "username": "test_user1",
        "email": "test@mail.com1",
        "password": "testPass"
    }

    user_test = {
        "id": 666,
        "username": "user_pytest",
        "email": "pytest@mail.com",
        "password": "pytestPass"
    }

    unregistered_user = {
        "username": "blabla_pytest",
        "email": "nouser@mail.com",
        "password": "pytestPass"
    }

    response = client.post("/auth/user/login", data=json.dumps(payload))
    response_body = response.json()
    TOKEN = get_admin_token()


    response_create_user = client.post("/auth/user/signup", data=json.dumps(user_test))
    response_login_user = client.post("/auth/user/login", data=json.dumps(user_test))
    response_login_unregistered_user = client.post("/auth/user/login", data=json.dumps(unregistered_user))
    response_delete_fake_admin = client.delete(f"/auth/user/{user_test['id']}", headers={"Authorization": "Asvf$5geGe5V"})
    response_delete_user = client.delete(f"/auth/user/{user_test['id']}", headers={"Authorization": TOKEN})

    assert response.status_code == 200
    assert response_create_user.status_code == 201
    assert response_login_user.status_code == 200
    assert response_login_unregistered_user.status_code == 403
    assert response_delete_fake_admin.status_code == 401
    assert response_delete_user.status_code == 200


def test_get_token():
    TOKEN = get_token()
    
    response_ticker_token = client.get("/stocks/dj30/AAPL", headers={"Authorization": TOKEN})
    response_ticker_bad_token = client.get("/stocks/dj30/AAPL", headers={"Authorization": "123fttt"})

    response_index_token = client.get("/stocks/index/dj30", headers={"Authorization": TOKEN})
    response_index_bad_token = client.get("/stocks/index/dj30")

    assert response_ticker_token.status_code == 200
    assert response_ticker_token.json()["ticker"] == "AAPL"
    assert response_ticker_bad_token.status_code == 401
    assert response_index_token.status_code == 200
    assert response_index_bad_token.status_code == 401


test_data_etf = [
    ("spy", "SPY"),
    ("dji", "DJI")
]
@pytest.mark.parametrize("ticker_lower, ticker_upper", test_data_etf)
def test_etf_app(ticker_lower, ticker_upper):
    TOKEN = get_token()

    response_get_etf_ticker = client.get(f"/etf/{ticker_lower}", headers={"Authorization": TOKEN})
    response_body = response_get_etf_ticker.json()

    response_etf_del = client.delete(f"/etf/spy", headers={"Authorization": "wefrgERG67"})

    assert response_get_etf_ticker.status_code == 200
    assert response_body["ticker"] == ticker_upper
    assert response_etf_del.status_code == 401




# def test_create_new_user():
#     payload = {
#         "username": "test_user",
#         "email": "test@domain.com",
#         "password": "testPassword"
#     }
#     response = client.post("/user/signup", data=json.dumps(payload))
#     assert response.status_code == 201
#     response_body = response.json()
#     print(response_body)


# def test_delete_user(db: Session = Depends(get_db)):
#     user_db = db.query(models.User).filter(models.User.username == "test_user").first()
#     response = client.delete(f"/user/{user_db.id}")
#     assert response.status_code == 204


def test_create_old_user():
    payload = {
        "username": "test_user1",
        "email": "test@mail.com1",
        "password": "testPass"
    }
    response = client.post("/auth/user/signup", data=json.dumps(payload))
    assert response.status_code == 400


def test_new_user():
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the email, hashed_password
    """
    user = models.User(username="ivan", email="ivan@ivan.com", password="ivanPassword")
    assert user.email == "ivan@ivan.com"
    assert user.username == "ivan"
    assert user.password == "ivanPassword"
    hashed_password = pwd_context.hash(user.password)
    varify_password = pwd_context.verify(user.password, hashed_password)
    assert varify_password == True


def test_new_stock():
    """
    GIVEN a Stock model
    WHEN a new Stock is created
    THEN check name, ticker, index_id, momentum_avg
    """
    stock = models.Stock(name="Apple", ticker="AAPL", index_id=1, momentum_avg=0.8, div_p=0.08)
    assert stock.div_p == 0.08
    assert stock.name == "Apple"
    assert stock.ticker == "AAPL"
    assert stock.index_id == 1
    assert stock.momentum_avg == 0.8


def test_new_index():
    """
    GIVEN a Index model
    WHEN a new Index is created
    THEN check ticker
    """
    index = models.Index(ticker="SPY")
    assert index.ticker == "SPY"
