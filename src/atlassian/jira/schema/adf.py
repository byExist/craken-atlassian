"""Atlassian Document Format (ADF) type.

REST API v3 returns rich-text fields (description, comment body) as ADF objects (dict).
Agile API v1.0 returns the same fields as plain text (str) — a v2 compatibility layer.
"""

from typing import Any

ADF = dict[str, Any]
"""Atlassian Document Format — a JSON document tree."""
