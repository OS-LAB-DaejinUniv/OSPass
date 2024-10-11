from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from challenge import challenge_router
from auth import verify_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def main():
    return {"message" : "hello"}

app.include_router(challenge_router)
app.include_router(verify_router)