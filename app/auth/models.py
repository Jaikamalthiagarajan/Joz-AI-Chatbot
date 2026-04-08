from pydantic import BaseModel

class HRLogin(BaseModel):
    username: str
    password: str
