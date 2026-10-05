from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Welcome to SplitEasy!"}

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name}!"}

from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str


@app.post("/users")
def create_user(user: User):
    return {
        "message": f"Created user {user.name}",
        "email": user.email
    }