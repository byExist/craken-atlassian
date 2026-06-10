"""Map write tools to Jira PROJECT permissions for read-time gating hints.

Account-wide gaps are surfaced in the write tools' descriptions at bind time
(see ``globally_unavailable`` / ``describe``); per-project gaps can only be
known at call time and surface as 403s (handled in ``client``).
"""

import logging
from collections.abc import Callable
from typing import Any

from atlassian.jira import client

logger = logging.getLogger(__name__)

# Write tool function name -> Jira PROJECT permission key (mypermissions key).
# Only unambiguous 1:1 mappings are listed. Tools whose permission splits into
# OWN/ALL variants (comment/worklog edit & delete) or whose agile permission is
# unclear are intentionally omitted, so they fall through to the 403 path.
_TOOL_PERMISSION: dict[str, str] = {
    "create_issue": "CREATE_ISSUES",
    "update_issue": "EDIT_ISSUES",
    "change_issue_type": "EDIT_ISSUES",
    "delete_issue": "DELETE_ISSUES",
    "assign_issue": "ASSIGN_ISSUES",
    "transition_issue": "TRANSITION_ISSUES",
    "add_comment": "ADD_COMMENTS",
    "upload_attachment": "CREATE_ATTACHMENTS",
    "add_worklog": "WORK_ON_ISSUES",
    "create_issue_link": "LINK_ISSUES",
    "remove_issue_link": "LINK_ISSUES",
    "add_watcher": "MANAGE_WATCHERS",
    "remove_watcher": "MANAGE_WATCHERS",
    "create_version": "ADMINISTER_PROJECTS",
    "update_version": "ADMINISTER_PROJECTS",
    "delete_version": "ADMINISTER_PROJECTS",
}


def globally_unavailable() -> set[str]:
    """Permission keys this account lacks in EVERY project.

    Queries /mypermissions with no project context: a PROJECT permission is
    reported True if held in any project, so a False there means it is missing
    everywhere — the only state safe to assert before a call is attempted.
    Returns an empty set if the lookup fails (no credentials, network), so
    marking is simply skipped and calls fall back to the 403 path.
    """
    keys = sorted(set(_TOOL_PERMISSION.values()))
    try:
        result = client.get_my_permissions(keys)
    except Exception:
        logger.warning(
            "mypermissions lookup failed; skipping write-tool permission gating "
            "(tools fall back to the 403 path)",
            exc_info=True,
        )
        return set()
    return {
        key
        for key in keys
        if (perm := result.permissions.get(key)) is not None
        and perm.have_permission is False
    }


def describe(fn: Callable[..., Any], unavailable: set[str]) -> str:
    """Return fn's docstring, with a not-permitted note appended when the
    permission it requires is globally unavailable."""
    doc = (fn.__doc__ or "").rstrip()
    perm = _TOOL_PERMISSION.get(fn.__name__)
    if perm and perm in unavailable:
        return (
            f"{doc}\n\n"
            f"Not permitted: this account lacks the '{perm}' permission in every "
            f"project, so calling this will fail with 403. Do not call it; "
            f"suggest an alternative (e.g. a status transition) instead."
        )
    return doc
