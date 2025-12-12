from contextlib import asynccontextmanager
from enum import Enum
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

from api import api_router
from db.session import init_db
from ws import ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
app.include_router(ws_router)

@app.get('/')
async def read_root():
    return {'Hello': 'World'}
