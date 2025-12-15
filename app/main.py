import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import RMQ_URL
from app.db.session import init_db
from app.rabbitmq import RMQConnection, RMQConsumer, RMQPublisher
from app.services.rmq_ws_bridge import rmq_ws_bridge
from app.ws import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.rabbit = RMQConnection(RMQ_URL)
    await app.state.rabbit.connect()
    await app.state.rabbit.declare_exchange('messages')
    app.state.message_publisher = RMQPublisher(app.state.rabbit, exchange_name='messages')
    app.state.consumers = []
    app.state.consumer_tasks = []

    message_routing_keys = [f'conversation.*.{et}' for et in ('created','edited','deleted','delivered','seen')]
    queue_name = f'ws_bridge.{uuid.uuid4()}'

    message_consumer = RMQConsumer(
        app.state.rabbit,
        queue_name=queue_name,
        routing_keys=message_routing_keys,
        exchange_name='messages',
    )
    app.state.consumers.append(message_consumer)

    for consumer in app.state.consumers:
        task = asyncio.create_task(consumer.start_consuming(handler=rmq_ws_bridge))
        app.state.consumer_tasks.append(task)

    yield

    for consumer in app.state.consumers:
        await consumer.stop_consuming()

    for task in app.state.consumer_tasks:
        task.cancel()

    await app.state.rabbit.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)
