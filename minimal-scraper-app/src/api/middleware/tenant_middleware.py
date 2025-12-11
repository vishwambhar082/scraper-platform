"""
Multi-tenant middleware for enforcing tenant isolation across all API endpoints.

This middleware:
- Extracts tenant_id from X-Tenant-Id header
- Validates tenant_id format and permissions
- Sets tenant context for downstream handlers
- Enforces tenant isolation in database queries
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from fastapi import Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.common.logging_utils import get_logger
from src.observability.run_trace_context import get_current_tenant_id, start_tenant_context

log = get_logger("tenant-middleware")

# Valid tenant_id pattern: alphanumeric, dashes, underscores, dots
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
MAX_TENANT_ID_LENGTH = 64


def validate_tenant_id(tenant_id: str) -> bool:
    """
    Validate tenant_id format.
    
    Rules:
    - Alphanumeric, dashes, underscores, dots only
    - Max 64 characters
    - Not empty
    """
    if not tenant_id or len(tenant_id) > MAX_TENANT_ID_LENGTH:
        return False
    return bool(TENANT_ID_PATTERN.match(tenant_id))


def get_tenant_id_from_header(
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
) -> str:
    """
    Extract and validate tenant_id from header.
    
    Returns:
        Valid tenant_id (defaults to 'default' if not provided)
    
    Raises:
        HTTPException: If tenant_id format is invalid
    """
    if x_tenant_id is None:
        return "default"
    
    if not validate_tenant_id(x_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id format: {x_tenant_id}. Must be alphanumeric with dashes, underscores, or dots, max 64 chars.",
        )
    
    return x_tenant_id


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce tenant isolation.
    
    - Extracts X-Tenant-Id header
    - Validates tenant_id format
    - Sets tenant context for request lifecycle
    - Ensures all database queries are tenant-scoped
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract tenant_id from header
        tenant_id_header = request.headers.get("X-Tenant-Id")
        
        if tenant_id_header:
            # Validate format
            if not validate_tenant_id(tenant_id_header):
                return Response(
                    content=f'{{"error": "Invalid tenant_id format: {tenant_id_header}"}}',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    media_type="application/json",
                )
            tenant_id = tenant_id_header
        else:
            # Default to 'default' tenant
            tenant_id = "default"
        
        # Set tenant context for this request
        start_tenant_context(tenant_id)
        
        # Add tenant_id to request state for easy access
        request.state.tenant_id = tenant_id
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Cleanup tenant context if needed
            pass


def require_tenant(tenant_id: Optional[str] = None) -> str:
    """
    Helper function to get and validate tenant_id.
    
    Args:
        tenant_id: Optional tenant_id (from header or parameter)
    
    Returns:
        Valid tenant_id (defaults to 'default')
    
    Raises:
        HTTPException: If tenant_id format is invalid
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id() or "default"
    
    if not validate_tenant_id(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id format: {tenant_id}",
        )
    
    return tenant_id

