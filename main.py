from fastapi import FastAPI
import uvicorn

from db import init_db, get_session, engine
from models.user import UserBase
from contextlib import asynccontextmanager

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        yield
    finally:
        engine.dispose()


@app.get("/")
def root():
    return {"Message": "success"}

@app.post('/create-user')
def create_user(user: UserBase):
    return user


if __name__ == "__main__":
    uvicorn.run(app)