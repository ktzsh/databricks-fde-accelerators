from fastapi import APIRouter, Request
from ..utils import get_current_user_from_headers
from ..models import UserInfoResponse

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/me", response_model=UserInfoResponse)
def get_current_user(request: Request):
    """Get current user information"""
    current_user = get_current_user_from_headers(request)
    
    return UserInfoResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name
    )
