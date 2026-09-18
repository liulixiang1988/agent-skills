# agent-skills

A collection of reusable agent skills for GitHub Copilot and AI-powered development workflows.

## Structure

- `skills/` — Individual agent skill definitions

## Usage

Browse the `skills/` directory to find skills you can use in your projects. Each skill is documented with its purpose, inputs, and expected outputs.

## Installing Skills

You can install individual skills into your project using `npx skills`:

### lumina-image

Build Docker/OCI container images, including Lumina proxy API and sandbox agent images.

```bash
npx skills add https://github.com/liulixiang1988/agent-skills --skill lumina-image
```

### knowledge-notes

Save reusable knowledge from the current session, or a selected topic, into the
OneDrive Obsidian vault at `{USERPROFILE}\OneDrive\文档\notes`. The skill follows
the vault's own rules, chooses folders by subject, and adds new knowledge to
existing notes without duplicating it. For another vault location, set
`KNOWLEDGE_NOTES_VAULT` to its absolute path.

Examples:

- `使用 $knowledge-notes 整理本次会话中值得复用的知识。`
- `只把刚才关于 Kubernetes DNS 排障的部分记到 Obsidian。`
- `保存知识笔记，补充到已有的 Git Worktree 笔记中。`

For a fresh user-level Codex installation from this checkout, run the following
in the repository root. This makes the skill available across projects; it does
not write notes during installation. If the destination already exists, update
that installation deliberately instead of overwriting it with this command.

```powershell
$codexBase = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skillDestination = Join-Path $codexBase 'skills/knowledge-notes'
if (Test-Path -LiteralPath $skillDestination) { throw "Already installed: $skillDestination" }
New-Item -ItemType Directory -Path (Split-Path -Parent $skillDestination) -Force | Out-Null
Copy-Item -LiteralPath './skills/knowledge-notes' -Destination $skillDestination -Recurse
```

Only the installed skill location depends on the agent's installation scope.
The notes vault is always resolved from the invoking user's environment, not
from the project or skill directory.
