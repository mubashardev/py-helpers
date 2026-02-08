from fastapi import Depends, FastAPI, HTTPException, status
from sqlmodel import Session, select
import uvicorn

from db import init_db, get_session, engine
from models.user import User, UserBase
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)

from fastapi.responses import HTMLResponse


@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html", "r") as f:
        return f.read()


@app.post("/create-user")
def create_user(input: UserBase, session: Session = Depends(get_session)):
    user = User(**input.model_dump())
    session.add(user)
    session.commit()
    return user.model_dump()


@app.get("/login")
def login(email: str, password: str, session: Session = Depends(get_session)):
    results = session.exec(
        select(User).where(User.email == email, User.password == password)
    ).all()

    if results:
        return results[0]
    else:
        return HTTPException(
            detail="Invalid details", status_code=status.HTTP_404_NOT_FOUND
        )


if __name__ == "__main__":
    uvicorn.run(app)
