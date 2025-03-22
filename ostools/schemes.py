from fastapi import Form

class LoginForm:
    def __init__(self, user_id : str = Form(...), user_password : str = Form(...)):
        self.user_id = user_id
        self.user_password = user_password