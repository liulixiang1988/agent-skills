---
name: work-record
description: "Record work log / save work summary. TRIGGER when: user says '记录工作', '保存工作', 'record work', 'save work', 'log work', '工作记录', '写工作日志', '保存工作记录', '记录一下', or similar phrases about saving/recording what was done in the current session. Also trigger when user mentions work log, work record, 工作日志, or wants to summarize completed work for future performance review."
---

# Work Record

Record a summary of the work done in the current session to a monthly work log file, so the user can reference it later when writing performance reviews.

## File Path

The work log file is located at:

```
{USERPROFILE}\OneDrive\文档\notes\Work\M365\Work Log\Work log-{YYYY}-{MM}.md
```

- `{USERPROFILE}` — The user's home directory (e.g., `C:\Users\lixiangliu`). Resolve via the `USERPROFILE` environment variable on Windows.
- `{YYYY}` — 4-digit year (e.g., `2026`)
- `{MM}` — 2-digit month (e.g., `03`)

Example: For March 2026, the file path is:
```
C:\Users\lixiangliu\OneDrive\文档\notes\Work\M365\Work Log\Work log-2026-03.md
```

Use **today's date** to determine which year-month file to write to.

## Workflow

1. **Determine the file path** — Use the current date to build the full path.
2. **Read the existing file** — If the file already exists, read its content so you can append to it without overwriting. If it does not exist, you will create it.
3. **Summarize the work** — Review the current conversation to understand what was accomplished. Write a concise but informative summary in **Chinese (中文)**. The summary should include:
   - What task or problem was worked on
   - Key changes made (files modified, features added, bugs fixed, etc.)
   - Any notable decisions or outcomes
   - Related work item IDs / PR links if available
4. **Append to the file** — Add the new entry to the **end** of the file.

## Entry Format

Each entry should follow this format:

```markdown
### {YYYY-MM-DD} {简短标题}

{工作内容摘要}

- **任务/背景**: {做了什么，为什么做}
- **主要改动**: {关键改动点}
- **相关链接**: {PR链接、工作项ID等，如果有的话}

---
```

If there are multiple distinct tasks in one session, create separate entries for each, or group them under a single date heading with bullet points.

## Important Notes

- Always **append** — never overwrite existing content in the file.
- If the directory does not exist, create it.
- Write the summary in **Chinese (中文)** to match the user's preference.
- Keep entries concise but useful for future performance review writing — focus on impact and outcomes, not trivial details.
- If the user provides additional context or instructions about what to record, incorporate that.
- After writing, confirm to the user what was recorded and where the file is located.
