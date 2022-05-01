from app.etf import router_etf
from app.auth import router_auth
from app.main import router_stocks
from fastapi import FastAPI



app = FastAPI()
app.include_router(
    router_etf,
    prefix="/etf",
    tags=["etf"]
)
app.include_router(
    router_auth,
    prefix="/auth",
    tags=["auth"]

)

app.include_router(
    router_stocks,
    prefix="/stocks",
    tags=["stocks"]
)