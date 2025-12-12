import asyncio
import logging
from typing import Optional

import aio_pika

logger = logging.getLogger(__name__)

class RMQConnection:
    def __init__(self, url: str, loop=None, reconnect_delay: float = 1.0):
        self.url = url
        self._conn: Optional[aio_pika.RobustConnection] = None
        self._loop = loop or asyncio.get_event_loop()
        self._reconnect_delay = reconnect_delay
        self._closing = False
    
    async def connect(self) -> None:
        if self._conn and self._conn.is_closed:
            return
        
        while not self._closing:
            try:
                self._conn = await aio_pika.connect_robust(self.url, loop=self._loop)
                logger.info('Connected to RabbitMQ')
                return
            except Exception as exc:
                logger.exception(
                    f'Failed to connect to RabbitMQ, retrying in {self._reconnect_delay:.1f}s'
                )
                await asyncio.sleep(self._reconnect_delay)
    
    async def close(self) -> None:
        self._closing = True
        if self._conn:
            await self._conn.close()
    
    async def get_channel(self) -> aio_pika.Channel:
        await self.connect()
        return await self._conn.channel()
    
    async def declare_exchange(self, name: str, type: str = 'topic', durable=True) -> aio_pika.Exchange:
        ch = await self.get_channel()
        return await ch.declare_exchange(name, type=type, durable=durable)
