---
name: work-record
description: "Record work log / save work summary / add TODO items. TRIGGER when: user says '记录工作', '保存工作', 'record work', 'save work', 'log work', '工作记录', '写工作日志', '保存工作记录', '记录一下', or similar phrases about saving/recording what was done in the current session. Also trigger when user mentions work log, work record, 工作日志, or wants to summarize completed work for future performance review. Also trigger when user says '加一个todo', 'add a todo', '添加todo', '加个待办', '记录todo', or similar phrases about adding a TODO/待办 item to the work log."
---

# Work Record

Record work summaries and manage TODO items in a monthly work log file, for performance review reference and task tracking.

## File Path

The work log file is located at:

```
{USERPROFILE}\OneDrive\文档\notes\Work\M365\Work Log\Work log-{YYYY}-{MM}.md
```

- `{USERPROFILE}` — Resolve via the `USERPROFILE` environment variable on Windows.
- `{YYYY}` — 4-digit year, `{MM}` — 2-digit month

Use **today's date** to determine which year-month file to write to.

## Mode Detection

Determine which mode to use based on user intent:

- **TODO mode**: User wants to add a TODO item (e.g., "加一个todo", "add a todo", "添加待办")
- **Record mode**: User wants to record work done (e.g., "记录工作", "save work", "记录一下")

## Workflow: TODO Mode

1. **Determine the file path** — Use the current date to build the full path.
2. **Read the existing file** — If it exists, read content. If not, create it.
3. **Find or create the TODO section** — Look for a `## TODO` section in the file. If it doesn't exist, insert it at the **top** of the file (before any work log entries).
4. **Add the TODO item** — Append a new unchecked item under the `## TODO` section.

### TODO Section Format

```markdown
## TODO

- [ ] {YYYY-MM-DD} {todo内容}
- [ ] {YYYY-MM-DD} {todo内容}
- [x] {YYYY-MM-DD} {todo内容} ✅ {完成日期}
```

Each TODO item is a Markdown checkbox with the date it was added and a description. Completed items use `[x]` and append a ✅ with the completion date.

## Workflow: Record Mode

1. **Determine the file path** — Use the current date to build the full path.
2. **Read the existing file** — If the file exists, read its content. If not, create it.
3. **Update TODOs** — If a `## TODO` section exists, review the current conversation to determine if any TODO items were addressed. For each addressed TODO:
   - Mark it as done: change `- [ ]` to `- [x]` and append ` ✅ {YYYY-MM-DD}` (today's date)
   - If the work changed the scope or details of a TODO, update its description accordingly
4. **Summarize the work** — Write a concise summary in **Chinese (中文)** covering:
   - What task or problem was worked on
   - Key changes made (files modified, features added, bugs fixed, etc.)
   - Any notable decisions or outcomes
   - Related work item IDs / PR links if available
5. **Append the work entry** — Add the new entry to the **end** of the file (after the TODO section).

## Entry Format

```markdown
### {YYYY-MM-DD} {简短标题}

{工作内容摘要}

- **任务/背景**: {做了什么，为什么做}
- **主要改动**: {关键改动点}
- **相关链接**: {PR链接、工作项ID等，如果有的话}

---
```

If there are multiple distinct tasks in one session, create separate entries or group them under a single date heading.

## Important Notes

- Always **append** work entries — never overwrite existing content.
- The `## TODO` section is always at the **top** of the file, before any work log entries.
- When updating TODOs, only mark items as done if the current session's work clearly addresses them. Do not guess.
- If the directory does not exist, create it.
- Write in **Chinese (中文)**.
- Keep entries concise but useful for performance review writing.
- After writing, confirm to the user what was recorded/added and where the file is located.
