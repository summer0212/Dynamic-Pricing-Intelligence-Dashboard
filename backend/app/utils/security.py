from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt,JWTError
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


def hash_password(password:str)-> str:
    '''Hashing the password'''
    return pwd_context.hash(password)

def verify_password(plain_password: str, hash_password: str)-> bool:
    '''Checking the plain password matches the hash.'''
    return pwd_context.verify(plain_password,hash_password)

def create_access_token(data: dict) -> str:
    '''Creating the JWT token'''
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    
    to_encode.update({"exp":expire})

    return jwt.encode(to_encode,settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    '''Decode the jwt token to verify '''
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        return payload
    except JWTError:
        return None


