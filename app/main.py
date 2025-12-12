from enum import Enum
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

from api import api_router
from db.session import init_db

app = FastAPI()
app.include_router(api_router)

@app.get('/')
async def read_root():
    return {'Hello': 'World'}

def main():
    init_db()

if __name__ == '__main__':
    main()
