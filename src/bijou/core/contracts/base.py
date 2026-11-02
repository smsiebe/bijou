"""Base Pydantic model for all Bijou DTO contracts."""

from pydantic import BaseModel, ConfigDict


class BijouBaseModel(BaseModel):
    """Base model enforcing immutability, extra-field prohibition, and alias population."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )
