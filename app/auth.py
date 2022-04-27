from fastapi import APIRouter, Depends, HTTPException, Security, Header, Response
from sqlalchemy.orm import Session
from database import models, schemas
from database.db import get_db
from fastapi.responses import JSONResponse
from typing import Dict, Optional
from passlib.context import CryptContext
from decouple import config
import time
import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = config("secret")
JWT_ALGORITH = config("algorithm")

router_auth = APIRouter()

def token_response(token: str):
    return {"access_token": token}


def signJWT(user_id: str):
    payload = {"user_id": user_id, "expires": time.time() + 600}
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
            db.query(models.User)
            .filter(
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


@router_auth.post("/user/signup", status_code=201)
async def create_user(user: schemas.UserInDB, db: Session = Depends(get_db)):
    """
    Signup new user
    return token
    """
    # logger.info(f"User signup: {user.username}, {user.email}")
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


@router_auth.post("/user/login", status_code=200)
async def user_login(user: schemas.UserInDB, db: Session = Depends(get_db)):
    """
    User login
    return token
    """
    # logger.info(f"User login: {user.username}, {user.email}")
    if check_user(user, db):
        return signJWT(user.email)
    return HTTPException(status_code=403, detail="Unauthorized")


@router_auth.delete("/user/{user_id}", status_code=200)
def user_delete(
    user_id: int,
    db: Session = Depends(get_db),
    Authorization: Optional[str] = Header(None),
):
    """
    Delete user by id
    """
    token = decodeJWT(Authorization)
    user_db = (
        db.query(models.User).filter(models.User.email == token["user_id"]).first()
    )
    if not user_db.role == "admin":
        raise HTTPException(status_code=401, detail="Acces denied")
    else:
        # logger.info(f"User to delete: {user_id}, by {user_db.email}")
        user_db = db.query(models.User).filter(models.User.id == user_id).delete()
        db.commit()
        return f"User with id: {user_id} was deleted."