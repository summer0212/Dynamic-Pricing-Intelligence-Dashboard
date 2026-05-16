from pydantic import BaseModel
from typing import Optional

class SignupRequest(BaseModel):
    email : str
    password : str
    name : str
    org_name : Optional[str ]= None
    invite_code : Optional[str ] = None


class LoginRequest(BaseModel):
    email : str
    password : str

class TokenResponse(BaseModel):
    access_token : str
    token_type : str = "bearer"
    user_id : str
    role : str
    org_name : str



