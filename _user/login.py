# User Login API
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response, Request
from conn_postgre import get_db
from sqlalchemy.orm import Session
from schemes import JoinUser, LoginForm
from models import Users
from register import verify_password, register_user

login_router = APIRouter(prefix="/api")

@login_router.post("/v1/init-login")
def login(response : Response, login_form : LoginForm = Depends(), db : Session = Depends(get_db)):
    return True