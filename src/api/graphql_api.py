# src/api/graphql_api.py
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.common.logging_utils import get_logger

log = get_logger("graphql-api")
router = APIRouter(prefix="/graphql", tags=["graphql"])


class GraphQLRequest(BaseModel):
    query: str
    variables: dict | None = None
    operationName: str | None = None


@router.post("")
async def graphql_endpoint(body: GraphQLRequest) -> dict:
    log.info("Received GraphQL request (len(query)=%d)", len(body.query))
    return {
        "data": None,
        "errors": [
            {
                "message": "GraphQL execution not implemented yet in v4.9 patch.",
                "extensions": {"code": "NOT_IMPLEMENTED"},
            }
        ],
    }
