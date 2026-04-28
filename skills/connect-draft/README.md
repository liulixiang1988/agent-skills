# connect-draft · Install + Usage Guide (for teammates)

A Claude Code skill that automates the Connect (Microsoft performance review) drafting workflow — from evidence gathering through HTML injection into the Connect tool.

## What it does

Given your Connect period + a few pointers:

1. **Gathers evidence in parallel** — ADO work items + PRs, SharePoint-authored design docs (via workiq), your 1-3 prior Connects (for style / voice reference), and HR philosophy pages.
2. **Builds a local sign-off draft** — a Mermaid flow chart + full 4-question HTML draft in your Obsidian wiki. You review, iterate, approve.
3. **Injects the draft into the Connect tool** at `v2.msconnect.microsoft.com` — correct HTML formatting preserved (nested bullets, hyperlinks, underlines) via Playwright-driven simulated paste events into the Roosterjs rich-text editor.
4. **Never auto-submits** — leaves "Save as draft" to you.

## Install (30 seconds)

Drop this folder into your Claude Code skills directory:

**Windows**
```
%USERPROFILE%\.claude\skills\connect-draft\
  ├─ SKILL.md
  └─ README.md
```

**macOS / Linux**
```
~/.claude/skills/connect-draft/
  ├─ SKILL.md
  └─ README.md
```

That's it. Claude Code auto-discovers skills on session start. Verify by running any Claude Code session — type `/` or just say "帮我写 connect" and the skill should load.

## Prerequisites

You need these MCP servers connected. Check with `/mcp` in Claude Code:

| MCP | Why | Typical install |
|-----|-----|-----------------|
| `playwright` | Reads historical Connects, HR pages, and injects into the new Connect draft | `@playwright/mcp` — see Microsoft internal docs for Edge/CA configuration |
| `workiq` | Identifies SharePoint doc authorship and extracts content | Microsoft internal MCP: https://github.com/microsoft/work-iq-mcp |
| `ado` or `azure-devops` | Queries your ADO work items + commits + PRs | Microsoft internal MCP; provides `wit_*` and `repo_*` tools |

If any are missing, the skill will tell you on the first run. Reconnect via `/mcp`.

## How to use

Just say the trigger phrase to Claude Code. The skill description has the keywords wired in:

```
帮我写 connect
draft my connect
准备绩效盘点
populate my connect at v2.msconnect.microsoft.com
```

Claude will ask you for 5 things up front:

1. **Period** — e.g., "Oct 18, 2025 → Apr 23, 2026"
2. **ADO email** — for the `assignedTo` filter
3. **Repos to search** — e.g., "CARESPlat, TenantSearch" — these differ per team
4. **SharePoint doc titles you think you authored** (or a folder URL for workiq to sweep)
5. **1-3 historical Connect URLs** — `v2.msconnect.microsoft.com/historyrag?connectid=<GUID>&pernr=<ID>` — for style reference. Your `pernr` is personal — find it from any past Connect URL.

Then Claude runs the 3 stages (evidence → local draft → inject). Between stages 2 and 3 it pauses for your review.

## What gets written to disk

Non-secret artifacts end up at:

- `~/.claude/connect-draft/` — evidence inventories + historical-Connect extracts + HR philosophy + pre-injection backup JSON
- `<Obsidian vault>/Claude Wiki/Connect/` — flow chart + paste-ready HTML draft

If you don't use Obsidian, just tell Claude on the first turn to write to a different path (e.g., `~/connect-drafts/`). The skill adapts.

## Things that vary per person (don't hard-code)

- **Personal ADO identifier** (`pernr` in Connect URLs) — comes from your history
- **Repos** — your team's set (ask teammates if unsure)
- **SharePoint site** — your team's site (e.g., `microsoftapc-my.sharepoint.com/personal/<alias>/...`)
- **Reflection period** — your manager sets this
- **Tone / voice** — the skill reads your prior Connects; your first run will establish your pattern

## Safety model

- The skill **backs up your current Connect draft** to `.claude/connect-draft/connect-backup-before-inject.json` before touching anything. If the injection goes wrong, you can restore by hand from the backup.
- The skill **never clicks Save as draft or Submit**. You do that yourself after a final visual review.
- The skill marks unfilled fields with `[PLACEHOLDER]` or `<TBD>` and reports their exact locations so you can `Ctrl+F` and fill them in before saving.

## Troubleshooting

- **"Playwright MCP disconnected"** → `/mcp` to reconnect; the skill checks and will tell you.
- **ADO commit search by email returns empty** → the skill already falls back to partial-name search; if still empty, try the other email variant (e.g., `alias+odspmdb@microsoft.com`).
- **workiq returns null for a doc** → could be on a different SharePoint site, or email-attached, or a `.vsdx`. The skill will list missing docs so you can manually confirm authorship.
- **"Character count exceeded"** → the skill trims the HOW section first (nested bullets → sentences). You can also edit in the Connect editor directly after paste.
- **Formatting looks wrong after paste** → the skill's post-paste DOM fixup (for link underlines) runs automatically. If it didn't, re-run the inject stage.

## Updating / sharing changes

If you improve the skill, just edit `SKILL.md` and share the new version. The skill is one markdown file — version it with your team however you want (git, SharePoint, direct Teams DM).

## Feedback / bugs

Edit `SKILL.md` directly or push back to whoever shared it with you. The gotchas section at the bottom of `SKILL.md` is the main institutional memory — add new ones as you hit them.
