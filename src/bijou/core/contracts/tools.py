"""Tool registry and analytical tool descriptor schemas."""

from typing import Literal
from pydantic import Field

from bijou.core.contracts.base import BijouBaseModel


class ToolDescriptorDTO(BijouBaseModel):
    """Descriptor metadata defining an analytical tool available to Bijou."""

    tool_id: str = Field(..., alias="tool_id", description="Unique tool identifier")
    title: str = Field(..., alias="title", description="Human-readable title")
    icon: str = Field(..., alias="icon", description="Icon identifier (e.g. zap, globe, target, history)")
    category: Literal["simulation", "graph_projection", "audit", "workbench"] = Field(
        ...,
        alias="category",
        description="Tool category"
    )
    target_entity: Literal["thing", "milestone", "organization", "global"] = Field(
        ...,
        alias="target_entity",
        description="Target entity type that can be passed to this tool"
    )
    description: str = Field(..., alias="description", description="Brief tool description")
    endpoint: str = Field(..., alias="endpoint", description="API endpoint providing backend analytical support")
    ui_component: str = Field(..., alias="ui_component", description="Registered frontend UI component or modal name")
