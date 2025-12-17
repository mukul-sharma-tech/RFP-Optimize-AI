from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from pymongo.database import Database

from models import User
from database import users_collection

# =========================
# CONFIG
# =========================
SECRET_KEY = "CHANGE_ME_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60



# =========================
# JWT
# =========================
def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
):
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# AUTH
# =========================
async def authenticate_user(db: Database, email: str, password: str):
    """Authenticate user and return User model"""
    print(f"DEBUG: Authenticating user: {email}")
    user_doc = await db.users.find_one({"email": email})

    if not user_doc:
        print(f"DEBUG: User not found: {email}")
        return None

    # ✅ FIX: Convert MongoDB _id to string
    user_doc["_id"] = str(user_doc["_id"])

    if password != user_doc["password"]:
        print(f"DEBUG: Password verification failed for: {email}")
        return None

    print(f"DEBUG: Authentication successful for: {email}")
    user = User(**user_doc)
    return user

async def get_current_user(token: str, db: Database):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as e:
        print(f"DEBUG: JWT decode error: {e}")
        raise credentials_exception
    
    user_doc = await db.users.find_one({"email": email})
    if user_doc is None:
        print(f"DEBUG: User not found in database: {email}")
        raise credentials_exception
    
    # ✅ FIX: Convert MongoDB _id to string
    user_doc["_id"] = str(user_doc["_id"])
    
    try:
        user = User(**user_doc)
        return user
    except Exception as e:
        print(f"DEBUG: Error creating User model from token: {e}")
        raise credentials_exception