from enum import unique
from faulthandler import disable
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)
    role = Column(String)


class Index(Base):
    __tablename__ = "indexes"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True)

    stocks = relationship("Stock", back_populates="indexes")


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=False)
    ticker = Column(String, unique=False, index=True)
    momentum_avg = Column(Float)
    div_p = Column(Float)
    index_id = Column(Integer, ForeignKey("indexes.id"))

    indexes = relationship("Index", back_populates="stocks")


class ETF(Base):
    """
    TODO: SPY, DJI, bonds, TB
    """
    __tablename__ = "etf"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True)
    momentum_12_1 = Column(Float)