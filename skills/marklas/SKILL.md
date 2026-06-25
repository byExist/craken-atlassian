---
description: "Writing and editing Jira/Confluence bodies through the atlassian plugin. Apply when composing new issue/page/comment content (write Markdown — marklas converts it to ADF) or editing an existing body (Markdown with adf= attributes from marklas, the ADF↔Markdown converter)."
user-invocable: false
---

<!-- Vendored from byExist/marklas docs/editing.md, extended for the atlassian plugin's create/edit flow. Full syntax reference: format.md. -->

# Marklas

Jira/Confluence bodies are Markdown in this plugin. This skill is the procedure for writing and editing them; [format.md](format.md) is the full syntax reference — consult it for the exact shape of any node, mark, table, or `adf=` element.

ADF-only features (panels, mentions, status, …) appear as HTML shaped `<tag adf="<type>" params='{...}'>content</tag>`: `adf` is the node type, `params` a JSON object of extra fields, `content` the visible body.

## Two Modes

| You are… | Mode | Core rule |
| --- | --- | --- |
| Composing a **new** body (`create_issue`, `create_page`, `add_comment`, …) | **Creating** | Write plain Markdown. Don't hand-author `adf=`. |
| Changing an **existing** body (`update_issue`, `update_page`, `edit_comment`, …) | **Editing** | Download with `plain=false`, edit on disk, publish. Preserve every `adf=` verbatim. |

## Creating

Body parameters (`content`, `description`, `body`) take Markdown.

- Write ordinary Markdown (headings, lists, tables, task lists, fenced code, links, …). **Don't** hand-fabricate `adf=` for anything Markdown already expresses.
- Reach for `adf=` only for ADF-only features (panels, expands, status, mentions, dates, layouts, decisions) — copy the exact shape from format.md; don't guess the type or `params`.
- A mention needs a real account id (`<span adf="mention" params='{"id":"..."}'>@Name</span>`) — look it up with `search_users`; never invent ids.
- For a long body, write it to a file and pass `from_file=<absolute path>`.

## Editing

Download-edit-publish, not regenerate-from-memory — regenerating drops `adf=` metadata and breaks the roundtrip.

1. **Download** — `get_page(page_id, plain=false, to_file="/abs/path.md")` (likewise `get_issue`, `get_comments`, …). `plain=false` keeps the `adf=` metadata the roundtrip needs (default `plain=true` strips it, for reading only); `to_file` writes the body to disk and out of context.
2. **Edit the file** with exact-string edits — change only the target text.
3. **Publish** — `update_page(page_id, from_file="/abs/path.md")` (likewise `update_issue`, `edit_comment`, …).

**Preserve verbatim:** every `adf` attribute and value; `params` JSON (validity + HTML-escaping like `&amp;`, `&#39;`); data-bearing HTML attrs (`href`, `datetime`, `start`); table filler cells; the empty `<p></p>` marker; backticks inside `<span adf="status">`; void elements (`<tag></tag>`) stay void.

**Free to change:** visible text in non-void elements; Markdown outside `adf=` elements; blocks inside panel / expand / layout-column containers; a mention's `@label` (never its `id`); intentional `params` edits (e.g. `panelType`, task `state`).

Before touching tables, nested tables, or block-level `adf=` containers, check format.md — the blank-line separation, cell inline-HTML / `\|` / `<br>` escaping, and nested-table-JSON rules all live there.

A body with no `adf=` attributes is plain Markdown — edit it as ordinary Markdown; these rules don't apply.

## Prohibitions

These corrupt the document — never do them:

- Fabricate an `adf=` element or `params` field you can't ground in format.md. (For standard constructs, write Markdown, not `adf=`.)
- Add non-`adf=` HTML outside table cells (the parser drops it).
- Rename or remove an existing `adf` attribute, or produce malformed `params` JSON.
- Insert a blank line or unescaped `|` inside a GFM table cell.
- Delete a filler cell adjacent to a merge without adjusting `colspan` / `rowspan`.
- Remove the backticks inside `<span adf="status">`.
