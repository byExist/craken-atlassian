"""Parameter and result annotations shared by the Jira and Confluence tools.

Kept in one place so the two tool sets present the same vocabulary to the
model: one description per concept, one acknowledgement value for writes.
"""

from typing import Annotated, Literal, TypeAlias

from pydantic import Field

# Pagination
Limit: TypeAlias = Annotated[int, Field(description="Max results.")]
Offset: TypeAlias = Annotated[int, Field(description="Pagination offset (0-based).")]

# Output
Plain: TypeAlias = Annotated[
    bool, Field(description="Set false to keep ADF-only features for editing.")
]
Ok: TypeAlias = Literal["ok"]
