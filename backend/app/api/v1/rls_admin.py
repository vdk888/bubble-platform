"""
PostgreSQL RLS Administration API
For testing and validating multi-tenant isolation
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any

from ...core.database import get_db
from ...core.rls_policies import RLSManager
from ...models.user import User, UserRole
from ..v1.auth import get_current_user

router = APIRouter()


class RLSStatusResponse(BaseModel):
    """RLS status response model"""
    success: bool
    rls_status: Dict[str, Any]
    message: str
    validation_results: Dict[str, Any] = {}


class RLSValidationRequest(BaseModel):
    """RLS validation request"""
    test_user_id: str


@router.get("/status", response_model=RLSStatusResponse)
async def get_rls_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current RLS status for all tables
    Admin-only endpoint for monitoring multi-tenant isolation
    """
    # Check admin privileges
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        rls_manager = RLSManager(db)
        rls_status = rls_manager.check_rls_status()
        
        return RLSStatusResponse(
            success=True,
            rls_status=rls_status,
            message="RLS status retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RLS status: {str(e)}"
        )


@router.post("/validate", response_model=RLSStatusResponse)
async def validate_rls_policies(
    validation_request: RLSValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate RLS policies are working correctly
    Admin-only endpoint for testing multi-tenant isolation
    """
    # Check admin privileges
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        rls_manager = RLSManager(db)
        
        # Validate RLS policies
        validation_results = rls_manager.validate_rls_policies(validation_request.test_user_id)
        
        # Get current RLS status
        rls_status = rls_manager.check_rls_status()
        
        return RLSStatusResponse(
            success=True,
            rls_status=rls_status,
            validation_results=validation_results,
            message=f"RLS validation completed for user {validation_request.test_user_id}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RLS validation failed: {str(e)}"
        )


@router.post("/setup", response_model=RLSStatusResponse)
async def setup_rls_policies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Setup RLS policies manually
    Admin-only endpoint for initializing multi-tenant isolation
    """
    # Check admin privileges
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        rls_manager = RLSManager(db)
        
        # Setup complete RLS
        setup_success = rls_manager.setup_complete_rls()
        
        if setup_success:
            # Get updated RLS status
            rls_status = rls_manager.check_rls_status()
            
            return RLSStatusResponse(
                success=True,
                rls_status=rls_status,
                message="✅ PostgreSQL RLS policies setup completed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="RLS setup failed - check server logs"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RLS setup failed: {str(e)}"
        )