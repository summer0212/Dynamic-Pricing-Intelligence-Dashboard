import string
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.org_settings import OrgSettings
from app.utils.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags = ["Authentication"])

def generate_invite_code(length = 8):
    '''Generate a random code for organization'''
    return "".join(random.choices(string.ascii_uppercase + string.digits, k = length))

@router.post("/signup", response_model=TokenResponse)
def signup(request : SignupRequest , db : Session = Depends(get_db)):

    '''Register a new user. Create a new org'''
   # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if request.invite_code:
        # Join existing organization
        org = db.query(Organization).filter(
            Organization.invite_code == request.invite_code
        ).first()
        if not org:
            raise HTTPException(status_code=404, detail="Invalid invite code")
        role = UserRole.analyst
    elif request.org_name:
        # Create new organization
        org = Organization(name=request.org_name, invite_code=generate_invite_code())
        db.add(org)
        db.flush()
        
        # Create default settings for this org
        org_settings = OrgSettings(org_id=org.id)
        db.add(org_settings)
        role = UserRole.admin
    else:
        raise HTTPException(status_code=400, detail="Provide either org_name or invite_code")
    
    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        org_id=org.id,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate JWT
    token = create_access_token({"user_id": str(user.id), "org_id": str(user.org_id)})
    
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
        org_name=org.name
    )
@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password. Returns JWT token."""
    
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    
    token = create_access_token({"user_id": str(user.id), "org_id": str(user.org_id)})
    
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
        org_name=org.name
    )


