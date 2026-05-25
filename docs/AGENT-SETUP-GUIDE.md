# Agent Setup 配置指南

一次配置，所有项目复用。本文档记录常用 agent 工具的安装与配置方法，避免每次重复设置。

---

## 目录

1. [Work IQ (Microsoft 365 数据查询)](#1-work-iq)
2. [Playwright MCP (浏览器自动化)](#2-playwright-mcp)
3. [Azure DevOps MCP (ADO 集成)](#3-azure-devops-mcp)
4. [Matt Pocock Skills (工程方法论)](#4-matt-pocock-skills)
5. [Superpowers (完整开发方法论)](#5-superpowers)
6. [统一 MCP 配置模板](#6-统一-mcp-配置模板)

---

## 1. Work IQ

**用途**: 用自然语言查询 Microsoft 365 数据 — 邮件、日历、文档、Teams 消息、人员信息等。

**前置条件**: Node.js 18+

### Copilot CLI 安装 (推荐)

```bash
# 添加插件市场 (一次性)
/plugin marketplace add microsoft/work-iq

# 安装插件
/plugin install workiq@work-iq
/plugin install workiq-productivity@work-iq
/plugin install microsoft-365-agents-toolkit@work-iq
```

### MCP Server 配置

添加到 `~/.copilot/mcp-config.json` 或项目 `.vscode/mcp.json`:

```json
{
  "workiq": {
    "command": "npx",
    "args": ["-y", "@microsoft/workiq@latest", "mcp"],
    "tools": ["*"]
  }
}
```

### 首次使用

```bash
# 接受 EULA (首次必须)
npx -y @microsoft/workiq accept-eula
```

> ⚠️ 需要租户管理员授权。如果你不是管理员，联系租户管理员授予 consent。

### 常用提示词

- "What meetings do I have tomorrow?"
- "Summarize emails from Sarah about the budget"
- "Find documents I worked on yesterday"

---

## 2. Playwright MCP

**用途**: 通过 MCP 提供浏览器自动化能力，基于 accessibility snapshots 而非截图，适合 LLM 交互。

**前置条件**: Node.js 18+

### Copilot CLI 安装

```bash
/mcp add
# 选择 playwright，或手动配置如下
```

### MCP Server 配置

`~/.copilot/mcp-config.json`:

```json
{
  "playwright": {
    "type": "local",
    "command": "npx",
    "args": ["@playwright/mcp@latest"],
    "tools": ["*"]
  }
}
```

`.vscode/mcp.json`:

```json
{
  "servers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

### 常用选项

| 选项 | 说明 |
|------|------|
| `--browser chromium/firefox/webkit` | 指定浏览器 |
| `--headless` | 无头模式 |
| `--port <port>` | SSE 传输端口 |

> 💡 如果你是 coding agent 场景且注重 token 效率，考虑使用 [Playwright CLI+SKILLS](https://github.com/microsoft/playwright-cli) 替代 MCP。

---

## 3. Azure DevOps MCP

**用途**: 将 Azure DevOps 上下文带入 AI agent — 项目、仓库、构建、工作项、Wiki 等。

**前置条件**: Node.js 20+

### 方式一: Remote MCP Server (推荐)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "ado-remote-mcp": {
      "url": "https://mcp.dev.azure.com/{organization}",
      "type": "http"
    }
  }
}
```

将 `{organization}` 替换为你的 ADO 组织名。

### 方式二: Local MCP Server

`.vscode/mcp.json`:

```json
{
  "inputs": [
    {
      "id": "ado_org",
      "type": "promptString",
      "description": "Azure DevOps organization name (e.g. 'contoso')"
    }
  ],
  "servers": {
    "ado": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@azure-devops/mcp", "${input:ado_org}"]
    }
  }
}
```

### Copilot Instructions (建议添加)

在项目中创建 `.github/copilot-instructions.md`:

```markdown
This project uses Azure DevOps. Always check to see if the Azure DevOps MCP server has a tool relevant to the user's request.
```

### 常用提示词

- "List my ADO projects"
- "List work items in current iteration for 'ProjectName' and 'TeamName'"
- "List ADO Repos for 'ProjectName'"
- "Create a wiki page '/Architecture/Overview'"

---

## 4. Matt Pocock Skills

**用途**: 一套工程实践 skills — grilling sessions、TDD、架构改进、诊断调试等。不是 MCP server，而是直接安装到 agent 的 skills。

### 安装

```bash
npx skills@latest add mattpocock/skills
```

交互式选择需要的 skills，然后运行 `/setup-matt-pocock-skills` 完成初始化配置。

### 核心 Skills

| Skill | 用途 |
|-------|------|
| `/grill-me` | 在动手之前让 agent 盘问你的想法，消除对齐偏差 |
| `/grill-with-docs` | 同上 + 建立 CONTEXT.md 共享语言 + ADR 决策记录 |
| `/tdd` | 红-绿-重构 TDD 循环 |
| `/diagnose` | 系统化调试流程 |
| `/to-prd` | 将对话转化为 PRD |
| `/to-issues` | 将计划拆分为可独立执行的 issue |
| `/improve-codebase-architecture` | 发现架构改进机会 |
| `/prototype` | 快速原型验证设计 |
| `/handoff` | 生成交接文档给下一个 agent |

### 推荐工作流

1. 每次新功能/变更前先跑 `/grill-with-docs`
2. 实现阶段用 `/tdd`
3. 遇到难以复现的 bug 用 `/diagnose`
4. 定期跑 `/improve-codebase-architecture`

---

## 5. Superpowers

**用途**: 完整的软件开发方法论 — 从头脑风暴到子 agent 驱动开发，自动触发，无需手动调用。

### Copilot CLI 安装

```bash
# 注册市场
/plugin marketplace add obra/superpowers-marketplace

# 安装插件
/plugin install superpowers@superpowers-marketplace
```

### 其他 Agent 安装

| Agent | 安装方式 |
|-------|----------|
| Claude Code | `/plugin install superpowers@claude-plugins-official` |
| Codex CLI | `/plugins` → 搜索 superpowers → Install |
| Cursor | `/add-plugin superpowers` |
| Gemini CLI | `gemini extensions install https://github.com/obra/superpowers` |

### 自动工作流 (无需手动调用)

1. **brainstorming** — 写代码前自动启动，通过提问细化需求
2. **using-git-worktrees** — 设计批准后创建隔离工作分支
3. **writing-plans** — 将工作拆分为 2-5 分钟的小任务
4. **subagent-driven-development** — 每个任务分派子 agent，两阶段 review
5. **test-driven-development** — 强制 RED-GREEN-REFACTOR
6. **requesting-code-review** — 任务间自动 review
7. **finishing-a-development-branch** — 完成后提供合并/PR/保留/丢弃选项

### 核心理念

- TDD 优先
- 系统化 > 临时起意
- 减少复杂度
- 证据 > 声明

---

## 6. 统一 MCP 配置模板

以下是合并所有 MCP server 的完整配置，放入 `~/.copilot/mcp-config.json` 即可全局生效:

```json
{
  "mcpServers": {
    "workiq": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "@microsoft/workiq@latest", "mcp"],
      "tools": ["*"]
    },
    "playwright": {
      "type": "local",
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "tools": ["*"]
    }
  }
}
```

对于 VS Code 项目级配置 (`.vscode/mcp.json`):

```json
{
  "servers": {
    "workiq": {
      "command": "npx",
      "args": ["-y", "@microsoft/workiq@latest", "mcp"]
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "ado-remote-mcp": {
      "url": "https://mcp.dev.azure.com/{your-organization}",
      "type": "http"
    }
  }
}
```

---

## 快速 Setup Checklist

```
[ ] Node.js 18+ 已安装
[ ] Work IQ: EULA 已接受，租户 consent 已授权
[ ] Playwright MCP: 已加入 mcp-config.json
[ ] Azure DevOps MCP: Remote server URL 已配置 (替换 organization)
[ ] Matt Pocock Skills: npx skills add 已执行，/setup 已完成
[ ] Superpowers: marketplace 已注册，plugin 已安装
```

---

## 参考链接

- [Work IQ](https://github.com/microsoft/work-iq)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
- [Azure DevOps MCP](https://github.com/microsoft/azure-devops-mcp)
- [Matt Pocock Skills](https://github.com/mattpocock/skills)
- [Superpowers](https://github.com/obra/superpowers)
- [VS Code MCP Server 配置文档](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)
