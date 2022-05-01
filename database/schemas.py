from faulthandler import disable
from os import truncate
from typing import List, Optional

from pydantic import BaseModel


class TokenBase(BaseModel):
    token: str


class UserBase(BaseModel):
    id: Optional[int]
    username: str
    email: Optional[str]
    role: Optional[str]
    

class UserInDB(UserBase):
    password: str
    

class StockBase(BaseModel):
    name: str
    ticker: str
    momentum_avg: Optional[float]
    div_p: Optional[float] = None

    class Config:
        orm_mode = True
        

class IndexBase(BaseModel):
    ticker: str

    class Config:
        orm_mode = True


class IndexDataBase(IndexBase):
    stocks: Optional[List[StockBase]]

    class Config:
        orm_mode = True


class ETFBase(BaseModel):
    ticker: str
    momentum_12_1: str

    class Config:
        orm_mode = True


