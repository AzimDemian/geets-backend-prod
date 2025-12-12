from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import api_router
from config import RMQ_URL
from db.session import init_db
from rabbitmq import RMQConnection
from ws import ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.rabbit = RMQConnection(RMQ_URL)
    await app.state.rabbit.connect()
    await app.state.rabbit.declare_exchange('messages')

    yield

    await app.state.rabbit.close()

app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
app.include_router(ws_router)

@app.get('/')
async def read_root():
    return {'Hello': 'World'}
