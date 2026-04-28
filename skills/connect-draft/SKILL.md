---
name: connect-draft
description: End-to-end Microsoft Connect (half-yearly performance review) drafting + inject into the Connect tool. Trigger when user mentions Connect, connect draft, 绩效盘点, Microsoft performance review, "write my connect", "draft my connect", "帮我写 connect", or asks to populate v2.msconnect.microsoft.com. Gathers evidence (ADO work items + PRs, SharePoint-authored docs via workiq, historical Connects via Playwright for style), builds a local sign-off flow chart for the user to review, then injects HTML-formatted content (with hyperlinks, nested lists, underlines) directly into the Roosterjs rich-text editor fields via simulated paste events. Asks the user for period dates, repos, SharePoint URLs, and historical Connect IDs at runtime because these vary per person.
---

# Connect Draft Skill

Assemble a Connect (Microsoft performance review) from hard evidence, let the user sign off locally, then **inject** into the Connect tool — HTML formatting intact.

## When to invoke

- User says: "帮我写 connect", "draft my connect", "update my connect draft", "准备绩效盘点", "write my perf review", "populate connect tool"
- User pastes `v2.msconnect.microsoft.com` URL or mentions Connect period
- User shares historical Connect IDs and asks for new draft

## Required MCP tools (check before starting)

- `mcp__playwright__*` — browser_navigate, browser_evaluate, browser_snapshot, browser_take_screenshot, browser_close
- `mcp__workiq__ask_work_iq` — SharePoint doc author + content + URL lookup
- `mcp__ado__*` — wit_my_work_items, wit_get_work_items_batch_by_ids, search_workitem, repo_search_commits, repo_list_pull_requests_by_repo_or_project, repo_get_repo_by_name_or_id

If any are missing, tell the user and ask them to `/mcp` to reconnect.

---

## Runtime inputs to ask from user

These **vary per person** — always ask, never assume.

```
1. Connect period: start date → end date (e.g., "Oct 18, 2025 → Apr 23, 2026")
2. ADO organization (e.g., "o365exchange.visualstudio.com"), project (e.g., "O365 Core")
3. ADO user email (for wit_my_work_items filter)
4. Relevant repos to search for the user's commits/PRs
   (e.g., CARESPlat, TenantSearch, Mimir — ask, because repos differ per team)
5. SharePoint doc inventory:
   - Either a list of doc titles the user suspects they authored
   - Or a SharePoint folder URL for workiq to sweep
6. ⭐ Historical Connect URLs (1-3) for style + voice reference — MANDATORY
   Format: v2.msconnect.microsoft.com/historyrag?connectid=<GUID>&pernr=<ID>
   If the user can't share URLs, fall back to auto-discovery (see Stage 1d).
7. New Connect URL (the draft page to populate)
   Usually just: https://v2.msconnect.microsoft.com/
8. Language preference for the draft (default: match the user's prior Connects;
   fall back to English if no priors available)
```

Don't block on all 8. Ask the first 5 upfront; ask #6-#8 just before the phases that need them. **Never skip #6** — voice matching is the primary lever for making the output feel like the user's own writing, not a generic template.

---

## Stage 1 · Gather evidence (parallelizable)

Spawn these in parallel where possible (they don't touch each other):

### 1a. ADO work items (assigned to user, in window)

```
wit_my_work_items(project, type=myactivity, includeCompleted=true, top=200)
wit_my_work_items(project, type=assignedtome, includeCompleted=true, top=200)
wit_get_work_items_batch_by_ids(ids, fields=[Title, WorkItemType, State, IterationPath, AreaPath, Tags, CreatedDate, ChangedDate, AssignedTo, ClosedDate, Parent])
```

Filter: keep where `ChangedDate ∈ [start, end]`. Theme/group items by parent feature or area-path. Save to `.claude/connect-draft/ado-inventory.md`.

### 1b. ADO commits + PRs per repo (user-provided list)

For each repo:
```
repo_get_repo_by_name_or_id(project, repoName)  // sanity check repo exists
repo_search_commits(project, repo, author=<first-name-fragment>, fromDate, toDate, top=50)
```
If email filter returns empty, use `author: <first name fragment>` — ADO ADO email + display name matching is quirky. Save PR IDs for hyperlinks.

### 1c. SharePoint docs authorship (workiq)

For each suspect doc title (from user's list):
```
ask_work_iq("Find the SharePoint document titled '<title>'. Return author, sharepoint URL, 3-sentence summary, any concrete numbers/metrics. If authored by someone other than <user email>, just return author.")
```

Batch related titles in one question. Save as `.claude/connect-draft/cares-docs-authored.md` (or similar per-topic).

### 1d. Historical Connects (Playwright) — voice calibration ⭐

This is the load-bearing step for voice matching. Skipping it produces a generic template that sounds nothing like the user.

**If user provided URLs**:
```
browser_navigate(connectUrl)
browser_evaluate(() => ({
  title: document.querySelector('h1').textContent,
  text: document.querySelector('main').innerText
}))
```

**If user didn't provide URLs** — auto-discover from the Connect home page:
```
browser_navigate('https://v2.msconnect.microsoft.com/')
browser_evaluate(() => {
  // Look for a "History" / "Past connects" section with links to past Connects
  const anchors = Array.from(document.querySelectorAll('a[href*="historyrag"], a[href*="connectid="]'));
  return anchors.map(a => ({ href: a.href, text: a.textContent.trim() }));
})
```
Pick the 2-3 most recent past Connects from the list. Confirm with the user before reading ("I found your last 3 Connects — use these for style reference?"). Only proceed without confirmation if the user explicitly said "just use my prior ones".

Persist each Connect's extracted text to `.claude/connect-draft/connect-<n>-<period>.md`. Extract these specifically:

- **Period** (reflection window)
- **Template version** — old Three-Circles vs. new What/How 4-question. Pick the template that matches the CURRENT Connect being populated; don't mix.
- **Opening formula** — verbatim. Examples: *"In conclusion, I have N deliveries during this connect reflection period: 1. X, 2. Y"* or *"In general, my work can be categorized as 1. X, 2. Y"* or *"In the past six months, my core priorities can be categorized into..."*. Reuse this exact formula in the new draft so the opening sounds like the same writer.
- **Bracket / heading conventions** — does the user use `[Project Name]` tags? `**Project: X**` headers? Bare project names? Nested `<ul>`? Match it.
- **Per-project sub-structure** — is each project decomposed into Challenges → Solutions → Effectiveness? Or flat bullets? Or What + How separately? Preserve the decomposition style.
- **Reflection structure** — does the user write *"Case Background: ... What I learned: ... How I am applying it: ..."*? Or a flowing 1-paragraph story with a one-line punchline? Match.
- **Qualities-shown vocabulary** — collect the exact adjectives the user has used across priors: "dive deep", "drive projects forward", "maturity", "agility", "growth mindset", "one-microsoft", etc. Reuse from this pool; don't introduce new buzzwords.
- **Numerical density** — does the user lean on concrete numbers ("6+ Sev1/Sev2", "~2.4 hours → 0")? Mirror the density. If priors are number-heavy, the new draft should be number-heavy.
- **Language** — Chinese-inflected English vs. plain English. Idiom preferences ("pivoted to", "self-made", "turnaround"). Match.
- **Link / artifact-citation style** — does the user hyperlink loops / Teams threads / dashboards? If yes, do the same.
- **Manager comment highlights** — tell the user what their manager specifically praised last time ("your manager noted technical leadership"), so they can play to that in goals / behaviors.

Save a `.claude/connect-draft/voice-profile.md` summarizing the extracted style patterns — this becomes the style guide for Stage 2.

### 1e. HR philosophy (Playwright)

Navigate `hrweb/sitepages/connects.aspx`, `hrweb/SitePages/perfphilosophy.aspx`, `hrweb/SitePages/Performance-and-Development-Evolution-Frequently-Asked-Questions.aspx`. For the FAQ page, click-expand all `aria-expanded="false"` before extracting. Save to `.claude/connect-draft/hr-philosophy.md`.

Key takeaways to record:
- The 4 required questions (What delivered / How / Goals / Behaviors)
- "Significant impact" definition (what + how)
- Security / AI / quality inclusion expectations

---

## Stage 2 · Local sign-off (flow chart + draft)

### 2a. Flow chart in Obsidian

Write `Claude Wiki/Connect/FY<year>-<month>-WorkFlowChart.md` with:
- Mermaid diagram: top-level project → sub-feature → task/impact
- Key numbers table (with "⟨TBD⟩" placeholders for anything not in evidence)
- Candidate reflection topics (2-3) — offer user choice
- 3 goals (copy carry-over from last Connect + update with current period's active threads)
- 5 behaviors (build on last period's setback lessons)

### 2b. Paste-ready HTML draft

Write `Claude Wiki/Connect/FY<year>-<month>-Connect-Body-HTML.md` with paste-ready HTML per field:

```
Q1 · What results did you deliver, and how did you do it?
Q2 · Reflect on recent setbacks
Q3 · Goal #1/#2/#3 descriptions (+titles)
Q4 · How will your actions and behaviors help you reach your goals?
```

**Structure to use** (nested, matches user preference):

```html
<p>Opening sentence w/ three arcs.</p>
<p><strong>What is delivered?</strong><br><em>[prompt reminder]</em></p>
<ul>
  <li><strong>Project A</strong>
    <ul>
      <li><strong>Feature 1:</strong> impact sentence with hyperlinks...</li>
      <li><strong>Feature 2:</strong> ...</li>
    </ul>
  </li>
  <li><strong>Project B</strong>...</li>
</ul>
<p><strong>How are they delivered?</strong>...</p>
```

**Hyperlink every referenced artifact**:
- Docs → SharePoint URL (from workiq)
- PRs → `https://<org>/<project>/_git/<repo>/pullrequest/<id>`
- Repos → `https://<org>/<project>/_git/<repo>`
- Team sharing PPTs → SharePoint URL

### 2c. User review loop

After writing the draft, **stop and ask the user**:
- Is the project breakdown right? (they may merge/split categories)
- Are the numbers right? (they may replace TBDs)
- Which reflection topic? (present 2-3 options)
- Names that must be [PLACEHOLDER] (privacy preference; user may not want names in the draft)
- Any section to trim / expand?

Iterate until user says "go inject". Don't inject unilaterally.

---

## Stage 3 · Inject into Connect (Playwright + Roosterjs)

### 3a. Navigate + snapshot current state

```
browser_navigate(newConnectUrl)
// Check editors exist + capture baseline
browser_evaluate(() => {
  const editors = Array.from(document.querySelectorAll('[contenteditable="true"][role="textbox"]'));
  return editors.map(e => ({id: e.id, aria: e.getAttribute('aria-label'), html: e.innerHTML, text: e.innerText}));
})
```

**Save baseline to `.claude/connect-draft/connect-backup-before-inject.json`.** User can revert by hand from this backup.

### 3b. Paste injection function (core primitive)

```js
async function injectViaPaste(editor, html) {
  editor.focus();
  const sel = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(editor);
  sel.removeAllRanges();
  sel.addRange(range);
  const dt = new DataTransfer();
  dt.setData('text/html', html);
  dt.setData('text/plain', editor.textContent);
  editor.dispatchEvent(new ClipboardEvent('paste', {
    bubbles: true, cancelable: true, clipboardData: dt
  }));
  await new Promise(r => setTimeout(r, 250));
}
```

This is the **only way** to preserve formatting — raw innerHTML doesn't update Roosterjs's internal model, and DOM text copy loses formatting.

### 3c. Inject each rich-text field

Locate by aria-label substring:
- `"What results did you deliver"` → Q1 editor
- `"Reflect on recent setbacks"` → Q2 editor
- `"Description for goal number"` → Goal description (per-goal)
- `"How will your actions and behaviors"` → Q4 editor

### 3d. Goal titles (INPUT elements, not contenteditable)

```js
function setInputValue(input, value) {
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  setter.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}
```

Required because React tracks `value` via its own descriptor; plain `input.value = x` won't trigger state update.

Find via: `document.querySelectorAll('input[aria-label*="Title for goal" i]')`.

### 3e. Add a 3rd goal (button click)

```js
const btn = Array.from(document.querySelectorAll('button'))
  .find(b => (b.getAttribute('aria-label') || '').toLowerCase() === 'add a new goal');
btn.click();
await new Promise(r => setTimeout(r, 800));
// Re-query title inputs + desc editors; the new one is at index [2]
```

### 3f. Force link underlines (post-paste DOM fixup)

Roosterjs **strips** `<u>` inside `<a>` and inline `text-decoration: underline` during paste sanitization. Work around by DOM-wrapping after paste:

```js
for (const editor of editors) {
  for (const a of editor.querySelectorAll('a')) {
    if (a.querySelector('u')) continue;
    const u = document.createElement('u');
    while (a.firstChild) u.appendChild(a.firstChild);
    a.appendChild(u);
    a.style.textDecoration = 'underline';
  }
  editor.dispatchEvent(new Event('input', { bubbles: true }));
}
```

This persists: Roosterjs serializes the current DOM when the user clicks Save as draft.

### 3g. Verify + character counts

The page shows counter elements like `5054/6000`. Grab them:

```js
Array.from(document.querySelectorAll('*'))
  .filter(el => /^\d{2,5}\/\d{3,5}$/.test((el.textContent || '').trim()) && !el.children.length)
  .map(el => el.textContent.trim())
```

Hard limits to respect:
- Q1 (big): 6000
- Q2 (reflection): 1000
- Goal descriptions: 1200 each
- Q4 (behaviors): 1000

If over, tell the user and offer to trim (HOW section compresses well — collapse nested bullets into sentences).

### 3h. Screenshot for user review

```
browser_take_screenshot({ fullPage: true, filename: 'connect-after-inject.png' })
```

Scroll tip: **Q1/Q2/Q4 editor bodies are internally scrollable** (`.pi-editor-textarea` has `overflow: auto`). To see all content in screenshot, scroll the editor itself via `editor.scrollTop = 0` — page-level `window.scrollTo` won't affect inside.

### 3i. Leave the save to the user

**Never click Save as draft automatically.** Report completion with:
- Injected fields + char counts per field
- Remaining `[PLACEHOLDER]` / `<TBD>` markers by location (user uses Ctrl+F to find)
- Path to the backup JSON
- Screenshot path

---

## Defaults and conventions

### Tone (match prior Connect style)

- First person ("I designed", "I led", "I drove") — foreground individual impact
- Open with: "In this connect reflection period, my work unfolded in three arcs: 1. X, 2. Y, 3. Z"
- `[Project]` bracket tags for each bullet, or nested `<ul>` per top-level project
- End with a single "Qualities shown:" line summarizing (dive deep, design-before-code, …)

### Dates

- Default to **omitting specific dates from prose** (user's preference: date ranges in the middle of bullets look clunky)
- If dates are included, only at the very start of a line (before the project name) or at the very end, never in the middle

### Names

- Default to `[PLACEHOLDER]` for any partner-team / reviewer / cross-team person names
- In the report, tell the user each PLACEHOLDER location + context so they can fill in with their preferred honorific

### Hyperlinks

- Every referenced doc, PR, repo, or artifact gets a hyperlink
- Link text should be the doc/PR title, not raw URL
- Wrap link text in `<u>` post-paste to force underline (Roosterjs strips it from paste HTML)

---

## Gotchas (learned from prior runs)

1. **Playwright MCP can disconnect between sessions.** Check with ToolSearch before starting; if disconnected, ask user to `/mcp` reconnect.
2. **ADO author filter by email returns empty sometimes.** Fall back to partial-name search (`author: "kefan"`). Email-suffix variants like `username+odspmdb@microsoft.com` also appear — sweep both.
3. **workiq returns `null` for files it can't index** (different team site, email attachments, `.vsdx` Visio). Don't assume missing = not-user-authored; tell user and let them confirm manually.
4. **Microsoft SharePoint `.aspx` pages use canvas rendering for Word/PPT viewers.** DOM innerText returns 0 chars. Use **workiq** for doc content; use Playwright only for static HTML pages.
5. **Connect FAQ page uses collapsible accordions** — must click all `[aria-expanded="false"]` before extracting text.
6. **Historical Connects use different template versions.** Check `<h1>` date label — old ones have "Three Circles of Impact" framing; new ones have 4 questions directly. Match the format of the NEW Connect being populated.
7. **HR pages show "recommended" character count warnings** — not hard limits, but exceeding them is a smell. Trim HOW section first (compress nested bullets).
8. **Goals carry over from prior Connect.** The Connect tool auto-populates old goal titles + descriptions. Replacing them means: (a) re-setting title via React-safe setter, (b) paste-injecting the new description into the same editor, (c) clicking "Add a new goal" if you have more goals than slots.

---

## Example first turn

User: "帮我写下一个 connect"

Claude:
> I'll gather evidence in parallel, build a local flow chart for your review, then inject into the Connect tool once you sign off. A few inputs I need up front because they vary per person:
>
> 1. What's the Connect reflection period? (start → end date)
> 2. Your ADO email for the `assignedTo` filter
> 3. Which repos should I search for your PRs? (e.g., names you've pushed to in that window)
> 4. SharePoint doc titles you think you've authored in that window (or a folder to sweep)
> 5. 1-3 historical Connect URLs (`v2.msconnect.microsoft.com/historyrag?connectid=...`) for style reference
>
> After you answer, I'll kick off ADO + workiq + Playwright research in parallel, then come back with a flow chart to review.

---

## Output artifacts (paths)

- `.claude/connect-draft/ado-inventory.md` — work items inventory
- `.claude/connect-draft/commits-<repo>.md` — PR/commit inventory per repo
- `.claude/connect-draft/docs-authored.md` — SharePoint-authored docs
- `.claude/connect-draft/connect-1|2|3-<period>.md` — historical Connect extracts
- `.claude/connect-draft/hr-philosophy.md` — HR framework notes
- `.claude/connect-draft/connect-backup-before-inject.json` — pre-injection baseline (for revert)
- `Claude Wiki/Connect/FY<Y>-<M>-WorkFlowChart.md` — Obsidian sign-off flow chart
- `Claude Wiki/Connect/FY<Y>-<M>-Connect-Body-HTML.md` — HTML draft (for audit + backup)
