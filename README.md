<h1 align="center">Atlassian</h1>

<p align="center">
  <a href="https://github.com/byExist/craken-atlassian/actions/workflows/ci.yml"><img src="https://github.com/byExist/craken-atlassian/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/byExist/craken"><img src="https://img.shields.io/badge/Claude_Code-plugin-da7756" alt="Claude Code plugin"></a>
  <img src="https://img.shields.io/badge/python-3.13+-3776AB?logo=python&logoColor=white" alt="Python 3.13+">
</p>

<p align="center">
  Jira &amp; Confluence in Claude — bodies as faithful <b>Markdown</b>, not flattened ADF.
</p>

<p align="center">
  <a href="README.ko.md">한국어</a>
</p>

---

## Why atlassian?

Jira and Confluence Cloud store every body — issue descriptions, comments, pages — as **ADF (Atlassian Document Format)**, a deeply nested JSON tree. A one-line note like `Fixed in **v2.1** — see PROJ-42` already balloons into a stack of `type` / `content` / `marks` objects, so handing raw ADF to an LLM buries the content under structure. Flattening it to plain text reads cleanly but discards tables, links, headings, and code — and leaves no way to turn edits back into ADF.

atlassian routes every body through [marklas](https://github.com/byExist/marklas), an AST-based **Markdown ⇄ ADF** converter. Bodies arrive as faithful Markdown — tables, links, nested lists, and code blocks intact — and the Markdown you write is assembled back into valid ADF, with ADF-only constructs (panels, mentions, status) preserved across the round trip.

## Installation

atlassian runs its MCP server through [uv](https://docs.astral.sh/uv/), so uv must be on your `PATH`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux — see the uv docs for Windows
```

```bash
/plugin marketplace add byExist/craken
/plugin install atlassian@craken
```

Credentials are prompted on enable, or set anytime with `/plugin config atlassian` — the token is stored in your OS keychain:

| Setting | Description |
| --- | --- |
| Atlassian site URL | e.g. `https://your-company.atlassian.net` |
| Atlassian account email | Account that owns the API token |
| Atlassian API token | Create one at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens) |

**Read-only by default.** Write tools (create / update / delete) appear only after you turn on *Enable write operations* via `/plugin config atlassian` — and even then, actions your account lacks permission for are marked **NOT PERMITTED**.

> **Cloud only.** Built on Jira REST v3 (ADF) and Confluence v2 (`atlas_doc_format`); Server / Data Center isn't supported.

## Tools

| Jira (`jira_*`) | Confluence (`confluence_*`) |
| --- | --- |
| `search_issues` — search by JQL | `search_content` — search by CQL |
| `get_issue` — full detail | `get_page` — full body |
| `create_issue` | `create_page` |
| `transition_issue` — change status | `move_page` — move in tree |
| `add_comment` | `add_comment` |

Plus boards, sprints, epics, worklogs, links, fields, labels, attachments, inline comments, blog posts, and tasks.

<details>
<summary><b>All tools</b></summary>

**Jira** (`jira_*`)

- **Issue** — `search_issues` `get_issue` `get_changelogs` `get_transitions` `get_issue_type_metadata` `list_issue_types` `create_issue` `update_issue` `change_issue_type` `delete_issue` `assign_issue` `transition_issue`
- **Comment** — `get_comments` `add_comment` `edit_comment` `delete_comment`
- **Worklog** — `get_worklogs` `add_worklog` `update_worklog` `delete_worklog`
- **Issue link** — `get_link_types` `create_issue_link` `remove_issue_link`
- **Remote link** — `get_remote_issue_links` `create_remote_issue_link` `delete_remote_issue_link`
- **Watcher** — `get_watchers` `add_watcher` `remove_watcher`
- **Board** — `list_boards` `get_board_issues` `get_backlog_issues`
- **Sprint** — `list_sprints` `get_sprint` `get_sprint_issues` `create_sprint` `update_sprint` `delete_sprint` `move_issues_to_sprint` `move_to_backlog`
- **Epic** — `get_epic_issues` `get_epic` `link_to_epic`
- **Project** — `list_projects` `get_project` `get_project_versions` `get_project_components` `get_project_statuses` `create_version` `update_version` `delete_version`
- **Field** — `search_fields`
- **Label** — `get_labels`
- **Attachment** — `download_attachment` `upload_attachment`
- **User** — `get_current_user` `search_users`

**Confluence** (`confluence_*`)

- **Page** — `search_content` `get_page` `list_pages` `get_page_children` `get_page_descendants` `get_ancestors` `get_page_versions` `get_page_views` `get_likes` `create_page` `update_page` `delete_page` `move_page` `copy_page` `restore_page_version`
- **Blog post** — `list_blog_posts` `get_blog_post` `create_blog_post` `update_blog_post` `delete_blog_post`
- **Comment** — `get_comments` `add_comment` `edit_comment` `delete_comment` `reply_to_comment` `get_comment_replies`
- **Inline comment** — `get_inline_comments` `create_inline_comment` `resolve_inline_comment` `delete_inline_comment` `get_inline_comment_replies`
- **Label** — `get_labels` `add_label` `remove_label`
- **Attachment** — `get_attachments` `download_attachment` `upload_attachment` `delete_attachment`
- **Task** — `get_tasks` `update_task`
- **Space** — `list_spaces` `get_space`
- **User** — `get_current_user` `search_users`

</details>

## Development

```bash
uv sync
uv run pytest
uv run pyright
```
