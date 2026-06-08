<h1 align="center">Atlassian</h1>

<p align="center">
  <a href="https://github.com/byExist/craken-atlassian/actions/workflows/ci.yml"><img src="https://github.com/byExist/craken-atlassian/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/byExist/craken"><img src="https://img.shields.io/badge/Claude_Code-plugin-da7756" alt="Claude Code plugin"></a>
  <img src="https://img.shields.io/badge/python-3.13+-3776AB?logo=python&logoColor=white" alt="Python 3.13+">
</p>

<p align="center">
  Claude에서 Jira·Confluence 다루기 — 본문을 납작해진 ADF가 아니라 구조가 살아있는 <b>Markdown</b>으로.
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

---

## 왜 atlassian인가?

Jira·Confluence Cloud는 모든 본문 — 이슈 설명, 댓글, 페이지 — 을 **ADF(Atlassian Document Format)**, 깊게 중첩된 JSON 트리로 저장합니다. `Fixed in **v2.1** — see PROJ-42` 한 줄도 `type`/`content`/`marks` 객체 더미로 부풀어서, 원본 ADF를 그대로 LLM에 건네면 내용이 구조에 파묻힙니다. 평문으로 납작하게 만들면 읽기는 깔끔하지만 표·링크·헤딩·코드가 사라지고, 편집한 내용을 다시 ADF로 되돌릴 길도 없습니다.

atlassian은 모든 본문을 [marklas](https://github.com/byExist/marklas), AST 기반 **Markdown ⇄ ADF** 변환기로 거칩니다. 본문은 표·링크·중첩 리스트·코드블록이 살아있는 충실한 Markdown으로 오고, 작성한 Markdown은 다시 유효한 ADF로 조립되며, ADF 전용 요소(패널·멘션·상태)도 왕복에서 보존됩니다.

## 설치

MCP 서버를 [uv](https://docs.astral.sh/uv/)로 실행하므로 uv가 `PATH`에 있어야 합니다:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux — Windows는 uv 문서 참조
```

```bash
/plugin marketplace add byExist/craken
/plugin install atlassian@craken
```

**비활성화 상태로 설치됩니다** — 계정에 연결되므로 직접 활성화해야 켜집니다(`/plugin` 메뉴 또는 `claude plugin enable atlassian`). 활성화 시 아래 설정을 입력받으며, 토큰은 `settings.json`이 아닌 OS 키체인에 저장됩니다. 이후 변경은 `/plugin config atlassian`에서.

| 설정 | 설명 |
| --- | --- |
| Atlassian site URL | 예: `https://your-company.atlassian.net` |
| Atlassian account email | API 토큰을 소유한 계정 이메일 |
| Atlassian API token | [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens)에서 발급 |
| Enable write operations | 기본 꺼짐 — read-only. 켜면 생성·수정·삭제 도구가 노출되며, 계정에 권한이 없는 작업은 **NOT PERMITTED**로 표시됩니다. |

> **Cloud 전용.** Jira REST v3(ADF)·Confluence v2(`atlas_doc_format`) 기반이라 Server / Data Center는 지원하지 않습니다.

## 도구

| Jira (`jira_*`) | Confluence (`confluence_*`) |
| --- | --- |
| `search_issues` — JQL 검색 | `search_content` — CQL 검색 |
| `get_issue` — 상세 조회 | `get_page` — 본문 조회 |
| `create_issue` | `create_page` |
| `transition_issue` — 상태 변경 | `move_page` — 트리 이동 |
| `add_comment` | `add_comment` |

그 외 보드·스프린트·에픽·워크로그·링크·필드·레이블·첨부·인라인 댓글·블로그 글·태스크까지.

<details>
<summary><b>전체 도구</b></summary>

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

## 개발

```bash
uv sync
uv run pytest
uv run pyright
```
