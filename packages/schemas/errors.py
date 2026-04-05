"""Shared API error schemas for OpenAPI response documentation."""

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    detail: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Authentication required. Provide Authorization: Bearer <token>."}}
    )
