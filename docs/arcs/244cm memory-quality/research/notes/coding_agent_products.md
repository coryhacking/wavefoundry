# Persistent memory in AI coding-agent products (2025-2026)

Owner: Engineering
Status: active
Last verified: 2026-11-23

The body below is copied unchanged from wave 245na's work folder on 2026-11-23 as the evidence base for arc `244cm-arc memory-quality`.

Research date: 2026-11-23. Vendor doc pages were fetched through a summarizing fetch tool, so exact wording is paraphrased unless quoted. Items marked "doc" are documented vendor behavior; "anecdote" or "secondary" are not.

## Storage: repo-visible files, hidden vendor store, or vector DB? Editable and reviewable?

### Takeaway
Products split into three families: repo-visible markdown instruction files (Claude Code CLAUDE.md, Cursor rules, Kiro steering, Codex AGENTS.md, Cline Memory Bank, Devin/Windsurf rules); local-machine generated memory (Claude Code auto memory, Windsurf memories, Codex memories); and vendor-hosted memory (Copilot Memory, ChatGPT, Devin Knowledge). Only the first family is committed and reviewed with the code. Nothing documented here uses a vector DB as the user-visible store.

### Cited Findings
- Claude Code CLAUDE.md files load in order from broad to specific: managed policy (`/Library/Application Support/ClaudeCode/CLAUDE.md`, `/etc/claude-code/CLAUDE.md`, `C:\Program Files\ClaudeCode\CLAUDE.md`), user, project, and `CLAUDE.local.md` (gitignored). `.claude/rules/*.md` hold modular rules; `~/.claude/rules/` holds personal rules. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code CLAUDE.md `@path` imports are recursive to a maximum depth of four hops. Imports do not reduce context cost, because imported files load with the importer. External imports (path outside the working directory) trigger a one-time approval dialog, protecting against files committed by others. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code reads `AGENTS.md` directly (needs v2.1.277+), or via an `@AGENTS.md` import in CLAUDE.md. `claudeMdExcludes` skips ancestor files in monorepos, except the managed file. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code auto memory is machine-local: `~/.claude/projects/<project>/memory/`, keyed on the git repo so worktrees share it. It holds a `MEMORY.md` index (one line per memory) plus one topic file per memory. Files are plain markdown, editable via `/memory`, not shared across machines, and exempt from the transcript cleanup sweep. `autoMemoryDirectory` relocates it. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code auto memory files carry a `type` frontmatter field (`user`, `feedback`, `project`, `reference`) and a `modified` ISO 8601 timestamp that Claude Code writes on each write, so staleness is visible to the user and to Claude. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Anthropic API memory tool (`memory_20250818`) is client-side: Claude issues `view`, `create`, `str_replace`, `insert`, `delete`, `rename` against a `/memories` path prefix; the developer's handler maps it to real storage (directory, database, encrypted files). Anthropic stores nothing; ZDR-eligible. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Cursor project rules live in `.cursor/rules/` (version-controlled, `.mdc` with `description`, `globs`, `alwaysApply` frontmatter; plain `.md` there is ignored). Also User Rules (global, in settings), Team Rules (dashboard, Team/Enterprise), and nested `AGENTS.md`. — [Cursor rules docs](https://cursor.com/docs/context/rules)
- Windsurf auto-generated memories are workspace-bound, stored locally in `~/.codeium/windsurf/memories/`, not committed to the repo. — [Windsurf memories docs via search summary](https://docs.windsurf.com/windsurf/cascade/memories.md)
- Windsurf/Devin Desktop rules: `.devin/rules/*.md`, `.devin/global_rules.md`, `~/.devin/rules/`, `AGENTS.md` (plus `AGENTS.local.md` for personal, unversioned rules); triggers `always_on`, `glob`, `model_decision`, `manual`. — [Devin Desktop rules docs](https://docs.devin.ai/desktop/cascade/memories)
- GitHub Copilot custom instructions are repo files (not fetched in this pass). Copilot Memory is a hosted store: repository-level facts (shared with collaborators, repo-scoped, forks do not inherit) and user-level preferences. Reviewed and deleted in repo settings (write access) or personal settings; "You cannot create or edit individual memories directly on GitHub.com" (CLI bulk import exists). — [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Cline Memory Bank is a documentation pattern, not a built-in feature: markdown files in `memory-bank/` (`projectbrief.md`, `productContext.md`, `activeContext.md`, `systemPatterns.md`, `techContext.md`, `progress.md`), enabled by pasting custom instructions into `.clinerules/` or global instructions. An older variant uses `cline_docs/`. — [Cline Memory Bank docs](https://docs.cline.bot/features/memory-bank.md); [Cline docs search results](https://docs.cline.bot/improving-your-prompting-skills/custom-instructions-library/cline-memory-bank)
- Kiro steering files: `.kiro/steering/` (workspace) and `~/.kiro/steering/` (global; workspace wins on conflict); foundation files `product.md`, `tech.md`, `structure.md` generated by "Generate Steering Docs" (IDE only). Teams can distribute global files via MDM or Group Policy. — [Kiro steering docs](https://kiro.dev/docs/steering/)
- Devin Knowledge: org or enterprise-scoped items (Trigger Description plus Content), editable, enable/disable per item, optional `!macro` names, folders. Hosted. **Knowledge is now documented as deprecated**, migrating automatically to Skills in Plugins. — [Devin Knowledge docs](https://docs.devin.ai/product-guides/knowledge)
- Codex AGENTS.md: global `~/.codex/AGENTS.md` (or `AGENTS.override.md`), then one file per directory from project root down to cwd, concatenated root-to-leaf so nearer files override. Codex memories are a separate, generated, local store in `~/.codex/memories_v2/` (or legacy `memories/`), per machine, "generated state ... shouldn't be edited by hand." — [Codex AGENTS.md docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md); [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- ChatGPT has two layers: saved memories (stored separately from chat history; survive chat deletion) and reference chat history (broader summary, "continually updates"). Users can view, edit when controls are available, or delete in Settings > Personalization > Memory. — [OpenAI Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)

### Inferences
- Wavefoundry's repo-visible typed records sit between Kiro/Cursor rules (committed, hand-written) and Claude Code auto memory (agent-written, typed frontmatter, but machine-local). No surveyed product combines committed storage, agent-written entries and required evidence refs; Copilot comes closest in schema but is hosted and not user-editable.
- The `type` taxonomy in Claude Code auto memory (user/feedback/project/reference) is a lightweight analogue of Wavefoundry's "kind"; it has no decay behavior attached in the documentation.

### Gaps
- Copilot custom-instruction file names and size limits were not fetched this pass.
- No documentation found for a vector DB backing any of these memory features; vendors do not disclose retrieval internals for ChatGPT, Copilot Memory, or Windsurf.
- Roo Code was not researched (no source gathered); Cline's Memory Bank is the nearest comparable pattern, and Roo has community variants I could not confirm.

## Creation: explicit command, automatic extraction, or agent-proposed with approval? What verification exists?

### Takeaway
Most products now let the agent write memory autonomously, with the user able to audit afterward; few require approval before write. Copilot is the only surveyed product that requires evidence (code citations) at creation. Devin Knowledge is the one agent-proposed, human-approved flow, and it is now deprecated.

### Cited Findings
- Claude Code auto memory: Claude decides what is worth saving; it skips anything derivable from the codebase and anything CLAUDE.md already says. User says "remember X" and it goes to auto memory; to put it in CLAUDE.md the user must say so. No approval prompt is documented; the UI shows "Saved N memories". — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code: `/doctor prompt-audit` (v2.1.283+) reviews CLAUDE.md, AGENTS.md, rules, skills and more for outdated or contradictory content and references to nonexistent files or commands, and proposes edits without applying them. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Anthropic memory tool: Claude decides what to write; the API injects a system instruction ("ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE ... ASSUME INTERRUPTION"). The developer's handler is the only gate. Docs recommend validation that strips sensitive data, because "Claude usually refuses" to write it but that is not guaranteed. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Copilot Memory: created automatically when Copilot identifies durable facts; users can ask it to remember; repository facts require write access; secrets-containing memories are rejected; model-control tokens can cause rejection (prompt-injection defense). Each memory has `subject`, `fact`, `citations` (file and line refs), `reason`. — [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory); [GitHub engineering blog, 2026-01-09](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Copilot repository facts are only creatable by contributors with write access, scoped to one repo. — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Windsurf Cascade: auto-generates memories when it judges them useful; creating and using them consumes no credits. — [Windsurf memories docs via search summary](https://docs.windsurf.com/windsurf/cascade/memories.md)
- Codex memories: off by default; generated in the background from "eligible prior chats" after an idle period; skips active or short sessions; `generate_memories`, `disable_on_external_context` (excludes chats that used MCP, web search or tool search), and rate-limit gating; secrets redacted from generated fields; consolidation model configurable. — [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- Devin Knowledge: Devin suggests items from chat feedback and can suggest updates to existing items; the user edits, dismisses or saves; effective only after save. — [Devin Knowledge docs](https://docs.devin.ai/product-guides/knowledge)
- ChatGPT: saved memories come from explicit requests or from details ChatGPT "saves as useful context"; temporary chats do not create memories. — [OpenAI Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)
- Cline Memory Bank: the user triggers "initialize memory bank" and "update memory bank"; Cline also updates on discovering patterns or after significant changes. No approval step beyond normal tool-call approval. — [Cline Memory Bank docs](https://docs.cline.bot/features/memory-bank.md)

### Inferences
- "Evidence required at creation" is rare. Copilot's citations are the closest to Wavefoundry's required evidence refs; Claude Code instead filters by "not derivable from code", a negative rule.
- Wavefoundry's candidate status plus agent validation is a heavier gate than any surveyed product except Devin's save-after-review flow.

### Gaps
- Cursor Memories creation flow (the 2025 background "sidecar" generation with user approval) was not confirmed from an official page this pass; only forum evidence of its removal surfaced.
- No official detail found on how Windsurf decides to create a memory, or on ChatGPT's selection heuristics.
- Kiro: no documented auto-memory; steering is hand-authored or generated once.

## Retrieval: always-loaded, glob-scoped, semantic, or tool calls? Caps and budgets?

### Takeaway
Always-loaded instruction files with explicit size guidance dominate. Scoping is by glob (Claude rules, Cursor, Kiro, Windsurf/Devin) or model-judged description (Cursor, Kiro `auto`, Windsurf). Generated memory is capped by a loaded index (Claude 200 lines or 25KB) or retrieved by the vendor (ChatGPT, Copilot top-recent).

### Cited Findings
- Claude Code: the first 200 lines or 25KB of `MEMORY.md` load at session start, whichever is smaller; topic files are read on demand with ordinary file tools. When MEMORY.md nears a limit, Claude Code reminds Claude to shorten it (one line per entry, move detail, merge or drop stale); over the limit, the write succeeds but returns an error telling Claude to rewrite the index. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code CLAUDE.md: target under 200 lines per file; longer files "consume more context and reduce adherence". Files up to 4 MiB load; subdirectory CLAUDE.md files load on demand when Claude works there. CLAUDE.md is delivered as a user message after the system prompt, with no guarantee of compliance; hooks are recommended for must-run behavior. Contradictory instructions: "Claude may pick one arbitrarily." — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Claude Code path-scoped rules: `paths:` glob frontmatter in `.claude/rules/` loads only when matching files are touched; unscoped rules load at launch. Auto memory is not loaded into subagents (except forks). — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Anthropic memory tool: just-in-time retrieval by tool call; directory listing 2 levels deep; `view` truncates files over 16,000 characters; `view_range` pages. Developers are advised to cap file sizes and return size. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Cursor: four application modes (Always Apply, Apply Intelligently by description, Apply to Specific Files by globs, Apply Manually by @-mention); guidance to keep rules under 500 lines, split into composable rules, and "reference files instead of copying their contents, so rules stay short and don't go stale". — [Cursor rules docs](https://cursor.com/docs/context/rules)
- Kiro: `always`, `fileMatch`, `manual`, `auto` (description-matched) modes; foundation files always on; `#[[file:...]]` live file references; no documented size limits. — [Kiro steering docs](https://kiro.dev/docs/steering/)
- Windsurf rules caps: global rules 6,000 characters (truncated beyond), workspace rule files 12,000 characters each; an older page says both global and `.windsurfrules` are 6,000 and another says combined rules past 12,000 are truncated with global priority (sources conflict). — [Windsurf docs via search results](https://docs.windsurf.com/windsurf/memories); [fast.io summary](https://fast.io/resources/windsurf-token-limit/)
- Copilot Memory: at session start the agent retrieves the repo's most recent memories into the prompt, then verifies citations before applying; memories count toward token usage; docs recommend custom instructions for rules that "must always be followed". — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/); [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Codex AGENTS.md: `project_doc_max_bytes` default 32 KiB across the concatenated chain; Codex "stops adding files once the combined size reaches the limit" (silent truncation is the risk). Codex memories docs: "a helpful recall layer, not ... the only source for rules that must always apply." — [Codex AGENTS.md docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md); [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- Devin Knowledge: retrieved by trigger-description match, pinned to a repo (always used there) or all repos; Devin reads an item's whole content, so items should be focused. — [Devin Knowledge docs](https://docs.devin.ai/product-guides/knowledge)
- Cline Memory Bank: the instructions require reading all Memory Bank files at the start of every task (recurring context cost; docs give no token figures); `activeContext.md` kept as current state only. — [Cline Memory Bank docs](https://docs.cline.bot/features/memory-bank.md)
- ChatGPT: "ChatGPT decides which available information is relevant to a response"; no separate storage limit for chat-history reference. — [OpenAI Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)

### Inferences
- Wavefoundry's briefing cap of 5 plus hybrid retrieval with reranking is more selective than any documented product. Closest are Copilot (recent N, then verify) and Claude Code (index capped at 200 lines or 25KB, topic files by agent choice).
- The common vendor advice, "always-follow rules belong in instruction files, not memory", reflects that memory retrieval is probabilistic. A Wavefoundry briefing of 5 has the same property and should not carry mandatory rules.

### Gaps
- Copilot's number of memories retrieved at session start is not disclosed in sources found.
- No official Windsurf figures on how many memories load per request.

## Lifecycle: staleness, contradiction, expiry; validation against current code?

### Takeaway
Copilot is the only documented product that validates memories against current code at use time and has reinforcement-based expiry. Everyone else relies on timestamps, manual audit, or the agent tidying its own index.

### Cited Findings
- Copilot validates at read time: before applying a memory, the agent checks cited locations against the current branch; if contradicted or the citation is invalid, it stores a corrected memory; if valid and useful, it re-stores to refresh the timestamp. — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Copilot's rationale: they considered an offline curation service (dedupe, resolve conflicts, track branches, expire) and rejected it as too complex and costly at scale, and still needing read-time reconciliation. Retrieval is "hard to solve, but easy to verify". — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Copilot adversarial test: repos seeded with false memories with irrelevant or nonexistent citations; agents "consistently" caught them and replaced them. (This is vendor-reported, no published sample size.) — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Copilot expiry (current docs): memories expire after a period without reinforcement; default 90 days, org or enterprise owners can set repository-fact expiry 7 to 180 days; upvoting resets the clock but mere retrieval does not; memories downvoted past a threshold stop being used and are eventually deleted. Validation is "a judgment by Copilot, not an enforced guarantee". — [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Conflict on expiry: DevOps.com reported unused memories expire after 28 days (earlier, 2026), while current GitHub docs say 90 days default; treat 28 days as an earlier figure. — [DevOps.com via search results](https://devops.com/githubs-security-autofix-agent-now-remembers-what-it-fixed/); [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Copilot results: coding agent PR merge rate 83% to 90%; code review positive feedback 75% to 77%; precision +3%, recall +4% (vendor A/B, p < 0.00001). — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Claude Code: no automatic expiry for auto memory; the `modified` timestamp and the size-limit nudge ("merge or drop stale entries") are the only lifecycle aids; `/doctor prompt-audit` surfaces dead references and contradictions on request. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Anthropic memory tool: expiry is the developer's job ("periodically delete memory files that haven't been accessed in a long time"); the docs pair it with context editing and compaction. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Anthropic multi-session pattern: an initializer session writes a progress log and feature checklist; features marked complete only after end-to-end verification. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- ChatGPT: deletion and updates "can take time to propagate"; deleted saved-memory logs may be retained up to 30 days; turning off chat-history reference schedules deletion within 30 days. — [OpenAI Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)
- Codex memories: docs describe no retention policy, size limit, or staleness handling; only "Delete Codex memories". — [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- Cursor advises referencing files rather than copying content to avoid rule staleness. — [Cursor rules docs](https://cursor.com/docs/context/rules)
- Cursor Memories (the auto-generated feature) was removed from the UI around 2.1.x (Nov 2025 per a third-party blog); staff said it was replaced by Rules, and conflicting staff replies say the capability may still function without a management UI. — [Cursor forum: Are my memories gone?](https://forum.cursor.com/t/are-my-memories-gone/144057); [Cursor forum: Memories not showing](https://forum.cursor.com/t/memories-not-showing/143820)
- Devin Knowledge being deprecated in favor of Skills. — [Devin Knowledge docs](https://docs.devin.ai/product-guides/knowledge)

### Inferences
- Copilot's read-time citation check is the closest external analogue to Wavefoundry's evidence refs plus agent validation. Differences: Copilot self-heals by rewriting at use time and has no status states; Wavefoundry's statuses (stale, superseded) keep history and make decisions reviewable.
- Copilot's upvote/downvote reinforcement versus Wavefoundry's kind-aware confidence decay: both approximate "usefulness over time"; Copilot says plain retrieval does not reset the clock, only validation does. That is a design point worth copying: decay should reset on re-validation, not on read.
- Copilot's stated reason for rejecting offline curation (cost, branch awareness, still needs read-time reconciliation) is a caution for any consolidation pass tied to one branch.

### Gaps
- Copilot's behavior on divergent branches (memory valid on main, wrong on feature branch) is not documented in what I read.
- No quantified rate of stale or wrong memories from any vendor.

## Failure modes: bloat, stale rules, wrong memories, poisoning, privacy

### Takeaway
Documented vendor concerns are instruction-following dilution from size, contradiction, and probabilistic application. Security research shows memory is a persistence vector for prompt injection (Windsurf, Claude Code). Privacy controls are strongest in ChatGPT and Copilot (admin and opt-out), weakest where memory is local files outside the repo.

### Cited Findings
- Bloat and dilution: Claude Code says longer CLAUDE.md files "reduce adherence"; Cursor says keep rules under 500 lines; Windsurf truncates at 6,000 or 12,000 characters; Codex truncates the chain at 32 KiB; Claude Code drops anything beyond line 200 or 25KB of MEMORY.md. — [Claude Code memory docs](https://code.claude.com/docs/en/memory); [Cursor rules docs](https://cursor.com/docs/context/rules); [Codex AGENTS.md docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Memory vs enforcement: Claude Code, Copilot and Codex docs all say memory or instructions are context, not guaranteed, and mandatory behavior belongs in hooks or checked-in instructions. — [Claude Code memory docs](https://code.claude.com/docs/en/memory); [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory); [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- Windsurf SpAIware (Embrace The Red, 2025): Cascade's `create_memory` tool ran without user approval, so indirect prompt injection could plant persistent false or malicious memories that carried across conversations; the researcher said Windsurf had not responded since the May 2025 report. Status of a fix is unconfirmed. Original SpAIware was shown on ChatGPT, which OpenAI mitigated. — [Embrace The Red](https://embracethered.com/blog/posts/2025/windsurf-spaiware-exploit-persistent-prompt-injection)
- Adversa rates Windsurf's memory component high-risk for storing generated memories without integrity checks (secondary). — [Adversa AI](https://airq.adversa.ai/agent/windsurf)
- Claude Code MEMORY.md poisoning (Cisco, 2026-04-01): an npm `postinstall` payload run on approval of a setup command in an untrusted repo overwrote every project's `MEMORY.md` and `~/.claude/settings.json` hooks, and added a shell alias re-enabling auto-memory, so the poisoned memory told the agent e.g. to hardcode API keys. Anthropic changed Claude Code v2.1.50 to remove user memories from the system prompt; its stated position is that the local user is fully trusted. — [Cisco blog](https://blogs.cisco.com/ai/identifying-and-remediating-a-persistent-memory-compromise-in-claude-code)
- Claude Code mitigations in docs: external imports require approval; managed CLAUDE.md cannot be excluded; hooks for hard rules. — [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Anthropic memory tool warns of path traversal (`/memories/../../secrets.env`, URL-encoded variants) and says handlers must validate canonical paths; also advises stripping sensitive data and capping file size. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Copilot defenses: reject memories with detected secrets or recognized model-control tokens; instruct the model not to store personal, confidential, or short-lived task data; repo memory writable only by users with write access; verify citations before use. — [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Copilot admin controls: user preferences off by default for Business and Enterprise; repo admins can disable repository facts; admins can view, export, delete user preferences. — [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Codex: secrets redacted in generated fields, but the docs say to review files before sharing the Codex home directory; `disable_on_external_context` excludes chats that used MCP or web, a poisoning-exposure control. — [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)
- ChatGPT: anything shared can appear in Memory; business workspaces are not used for training by default; personal accounts may be, unless opted out; temporary chats create no memory; project-only memory is available in regulated workspaces. — [OpenAI Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)
- Cursor user reports (forum, anecdote): memories not persisting, disappearing after window reload or version change, and "can't clear memories" after the UI was removed. — [Cursor forum: Memories get deleted when reloading window](https://forum.cursor.com/t/memories-get-deleted-when-reloading-window/137462); [Cursor forum: Can't clear memories](https://forum.cursor.com/t/cant-clear-memories/148254)
- Cline Memory Bank: maintenance "depends on the user or Cline keeping files accurate" and every task re-reads all files (docs-stated limitation). — [Cline Memory Bank docs](https://docs.cline.bot/features/memory-bank.md)

### Inferences
- The two documented poisoning cases both involve memory the agent writes without a human gate, or memory files outside the repo review path (`~/.claude/projects/...`, `~/.codeium/...`). Wavefoundry's repo-visible records with a candidate status and agent validation put memory writes in git diff review; that is a genuine structural advantage, though a poisoned candidate that an agent validates is still possible.
- Memory must not be able to rewrite its own enabling configuration (Cisco showed memory plus hooks plus shell alias persistence); keep memory files separated from executable config.

### Gaps
- No vendor publishes a quantitative rate of wrong or stale memories or of poisoning success.
- Windsurf's fix status for SpAIware is unconfirmed.
- Practitioner accounts of Memory Bank token cost were not gathered; only the docs-stated limitation.

## Lessons: what vendors have publicly said they changed or learned

### Takeaway
Direction of travel: from opaque auto memory toward verifiable or reviewable records and plain files (Cursor removed Memories UI in favor of Rules; Devin deprecated Knowledge for Skills; Claude Code added audit, timestamps and size nudges; Copilot added citations and expiry controls). Vendors consistently say mandatory rules belong in committed instructions, not memory.

### Cited Findings
- Copilot team: chose just-in-time verification over curation; "memory is an action" shaped by agents validating and rewriting; cross-agent sharing (code review, coding agent, CLI) of one repo-scoped pool. — [GitHub engineering blog](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)
- Copilot product timeline: agentic memory announced as public preview 2026-01-15; current docs list it for all paid plans with admin-configurable expiry. A secondary source calls it generally available; status was not confirmed from an official GA announcement. — [GitHub changelog](https://github.blog/changelog/2026-01-15-agentic-memory-for-github-copilot-is-in-public-preview/); [Copilot Memory docs](https://docs.github.com/en/copilot/concepts/agents/copilot-memory)
- Cursor staff directed users to move saved memories into Rules (and offered an "Export memories" command), after the Memories UI was removed around 2.1.x. — [Cursor forum](https://forum.cursor.com/t/are-my-memories-gone/144057)
- Devin: Knowledge deprecated, existing items auto-migrate to Skills in Plugins. — [Devin Knowledge docs](https://docs.devin.ai/product-guides/knowledge)
- Anthropic: AGENTS.md is read natively by Claude Code (v2.1.277+), signaling convergence on AGENTS.md as the shared instruction file; Cursor, Kiro, Codex and Devin/Windsurf also read it. — [Claude Code memory docs](https://code.claude.com/docs/en/memory); [Cursor rules docs](https://cursor.com/docs/context/rules); [Kiro steering docs](https://kiro.dev/docs/steering/); [Codex AGENTS.md docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md); [Devin Desktop docs](https://docs.devin.ai/desktop/cascade/memories)
- Anthropic: Claude Code v2.1.50 removed user memories from the system prompt after the Cisco report; auto memory later gained write-time `modified` stamps and index size nudges (version of those additions not established). — [Cisco blog](https://blogs.cisco.com/ai/identifying-and-remediating-a-persistent-memory-compromise-in-claude-code); [Claude Code memory docs](https://code.claude.com/docs/en/memory)
- Anthropic's "effective harnesses" guidance: memory as a recovery mechanism across sessions with a progress log and feature checklist, marking work complete only after end-to-end verification. — [Memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Codex shipped a new store layout (`memories_v2`, `dual_write`) with migration flags, local-only, opt-in, with rate-limit gating on background generation. — [Codex memories docs](https://learn.chatgpt.com/docs/customization/memories?surface=app)

### Inferences
- Comparable-to-Wavefoundry list: Copilot (typed fields, evidence citations, read-time validation, expiry, reinforcement); Claude Code auto memory (typed frontmatter, index, size cap, timestamps, topic files); Kiro and Cursor (glob and description-scoped committed files); Codex (opt-in, generation gated, external-context exclusion). Nothing surveyed has multi-status lifecycle (candidate, stale, superseded, rejected), file/symbol targets, or kind-aware decay.
- Features that look transferable: expire or decay reset only on re-validation; exclude sessions that touched external content from candidate generation (Codex `disable_on_external_context`); reject candidates containing secrets or model-control tokens (Copilot); write-time modified stamp visible to the reader (Claude Code); an audit command that lists dead references and contradictions without applying edits (`/doctor prompt-audit`).
- Convergence on "memory is a recall layer, mandatory rules live in committed instructions" supports keeping Wavefoundry memory briefings separate from AGENTS.md rules.

### Gaps
- Roo Code was not researched: no evidence gathered either way.
- Vendor retrospectives beyond GitHub's engineering post (e.g. Cursor or Windsurf engineering posts on why Memories were reshaped) were not found.
- Not read in full: the Windsurf docs pages (only search summaries), ChatGPT "memory full" behavior in 2025 (the current FAQ says no limit for chat-history reference and does not mention a full state), Copilot custom-instructions docs, the Amazon Q Developer rules/project-rules equivalent.
