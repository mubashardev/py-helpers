from fastapi import FastAPI
import uvicorn

from models.user import UserBase

app = FastAPI()


@app.get("/")
def root():
    return {"Message": "success"}

@app.post('/create-user')
def create_user(user: UserBase):
    return user


if __name__ == "__main__":
    uvicorn.run(app)