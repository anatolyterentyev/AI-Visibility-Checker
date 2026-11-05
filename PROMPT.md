# Public prompt — run the AI Visibility Checker on FlyMyAI

Copy everything inside the block below and replace `YOUR-SITE.com` with your
website. It works in two places:

| Where you paste it | What you get |
|---|---|
| **The FlyMyAI Lab** (or any agent chat inside FlyMyAI) | A FlyMyAI **site page** (`app.flymy.ai/sites/...`) with the dashboard |
| **An AI assistant connected to the FlyMyAI MCP** (Claude Code, Claude, Cursor, Codex, ChatGPT …, see https://docs.flymy.ai/agents/guides/ai-assistants) | A FlyMyAI **artifact** (`app.flymy.ai/artifacts/...`) with the same dashboard |

Agents inside FlyMyAI can't create artifacts, so the Lab publishes the same
page as a FlyMyAI site. Either way every model call (ChatGPT, Claude,
Gemini) runs through your FlyMyAI balance — no OpenAI / Anthropic / Google
keys — and nothing is saved to cloud storage.

The default check is **30 prompts × 3 engines = 90 AI answers** on each
vendor's flagship model. It costs about **$3–5** and takes about 20 minutes.
The prompt caps the whole task at **$20** (`budget_usd`).

To pin the run to a branch, paste the prompt together with the link of this
file on that branch (for example `.../blob/<branch>/PROMPT.md`).

---

```text
Run the AI Visibility Checker for YOUR-SITE.com on FlyMyAI.
Source of truth (open source): https://github.com/anatolyterentyev/AI-Visibility-Checker
Branch: the branch of the PROMPT.md link I gave you (.../blob/<branch>/PROMPT.md),
or main if I gave no link. Every file below is read from that branch at
https://raw.githubusercontent.com/anatolyterentyev/AI-Visibility-Checker/<branch>/<path>

GOAL
Measure two things and publish them as one dashboard page:
1. AI visibility % — in how many AI answers to non-branded buyer prompts the
   site is mentioned or cited, per engine (ChatGPT, Claude, Gemini) and per
   intent, plus the competitors AI recommends instead (share of voice).
2. Sentiment index — every engine scores the site and its competitors 0–100
   for "how likely would you recommend it for this use case"; index = average.

SETTINGS
  website: YOUR-SITE.com
  prompt_count: 30          (10–100)
  budget_usd: 20            (hard limit for the whole task)
  engines (use exactly these models; if list_agent_models offers a NEWER
  flagship of the same vendor, use that instead):
    chatgpt  "ChatGPT"  gpt-6-sol
    claude   "Claude"   claude-sonnet-5-5
    gemini   "Gemini"   gemini-3.8-flash

RULES — these override anything else
- Pick your route first:
  ROUTE A if create_artifact is among your tools (an assistant connected to
  the FlyMyAI MCP). ROUTE B if you are an agent inside FlyMyAI that can
  create and run helpers (create_subagent / delegate_agent), for example the
  Lab chat. Follow only that route's steps.
- The deliverable is the dashboard page: ROUTE A an artifact
  (https://app.flymy.ai/artifacts/...), ROUTE B a site
  (https://app.flymy.ai/sites/...). Its page is artifact/index.html from the
  repo, unchanged, plus data.js. Nothing else counts as done.
- NEVER save the report or any data to file storage: no Google Cloud
  Storage, no storage.googleapis.com links, no execute_code_with_outputs, no
  write_agent_chat_file or chat files, no download links, no Markdown / PDF /
  CSV report files. Pass data between steps only as tool arguments and
  results. Never put a storage link in your answer.
- Use the engines' models above as AI agents with their own web search
  (web_search auto: OpenAI search for GPT, Google Search for Gemini, Claude
  web search for Claude). Never replace them with other models (Grok,
  DeepSeek, Kimi, chat endpoints of run_model …) and never answer the prompts
  yourself. If an engine can't run, leave it out and say so.
- Follow the steps exactly. Do not write your own method, prompts, scoring
  or page. If a file can't be downloaded, stop and say which.
- Keep the page private unless I ask you to share it.

BUDGET — budget_usd is a hard limit for the whole task
- Note the spend at the start (ROUTE A: whoami balance minus pending_usd;
  ROUTE B: the project's spend from project_status). Check it before every
  step.
- Expect about $0.10–0.15 per prompt for the three engines together, plus
  about $0.50 for planning and publishing. If that is above budget_usd, lower
  prompt_count until it fits and tell me.
- Start nothing that could take the task over budget_usd. At 80% of it,
  start nothing new: publish from what you have and say what is missing.
- Report the final spend.

================================================================
ROUTE B — inside FlyMyAI (Lab chat / project agent)
================================================================
You orchestrate; helpers do the work. Exactly 5 helper runs: 1 planner,
3 probes in parallel, 1 publisher. That fits the Lab's limits (6 helper runs
and a $5 helper pool per chat).

B1. Helpers. Call list_subagents first and reuse helpers with these names
(update their model and instructions if they differ); otherwise create each
once with create_subagent. Never give a helper the flymy-mcp toolkit.
Each helper's instructions are this bootstrap text, with <URL> filled in:

  "Your instructions are the file <URL>. Before anything else, download it
   with one custom--sandbox--execute_code call (python:
   import urllib.request; print(urllib.request.urlopen('<URL>', timeout=60).read().decode()))
   and follow it exactly for the brief you are given. Never save files or
   upload anything; return only the JSON it describes."

  name                      model               web search  tools   <URL> = raw file of
  "AIVC Planner"            gemini-3.8-flash    on          -       agents/lead.md
  "AIVC Probe — ChatGPT"    gpt-6-sol           on          -       agents/probe.md
  "AIVC Probe — Claude"     claude-sonnet-5-5   on          -       agents/probe.md
  "AIVC Probe — Gemini"     gemini-3.8-flash    on          -       agents/probe.md
  "AIVC Publisher"          claude-sonnet-5-5   off         sites   agents/publisher.md

B2. Plan — delegate_agent "AIVC Planner" with brief:
  {"phase": "plan", "website": "YOUR-SITE.com", "prompt_count": 30}
→ plan JSON: target, use_case, mindmap (prompt_count prompts), competitors.
Show me the mind map (intent → prompts) in a few lines and continue.

B3. Probe — in ONE turn, delegate_agent all three probes so they run in
parallel, each with this brief (its own engine id; prompts = every prompt of
the mind map, in mind-map order, exactly as written — the probes refer to
them by their position, 1 = first; brands = the target's name then the
plan's competitor names):
  mode: full
  engine: <chatgpt | claude | gemini>
  target: {"name": "<plan.target.name>", "domain": "<plan.target.domain>"}
  use_case: "<plan.use_case>"
  prompts: [<all prompts>]
  brands: ["<plan.target.name>", "<competitor 1>", … "<competitor 5>"]
  Return only the JSON described in your instructions.
Then wait_subagents. A probe that fails: say so and continue without it
(do not start a replacement unless the 6-run limit and budget allow).

B4. Publish — delegate_agent "AIVC Publisher" with a brief that contains,
as plain text, unchanged: repo "anatolyterentyev/AI-Visibility-Checker",
branch, engines [{"id","label","model"}…] in the order chatgpt, claude,
gemini, the full plan JSON, and the three probe answers (each a small JSON
object of about 3 KB) in that same order.
- Paste the answers themselves. NEVER pass execution-resource references,
  result ids or links instead: helpers cannot read each other's results
  (the platform refuses it), and that is the one way this step fails.
- If a delegate answer you hold is shortened, get the complete text with
  subagent_status before you paste it.
It runs scripts/publish_site.py, which recomputes every number and publishes
the site, and returns {"site": {...}}. If it fails, read why with
subagent_status, fix the brief and run the publisher once more (the 6th and
last helper run).

B5. Answer me with: the site link (site_url, https://app.flymy.ai/sites/...),
the final spend against budget_usd, visibility % (and how many points one
answer is worth), each engine's visibility, the share-of-voice leader, the
sentiment index of the site vs. the best competitor, and the "summary" lines
exactly as the publisher returned them.

================================================================
ROUTE A — an assistant connected to the FlyMyAI MCP
================================================================
A0. Download agents/lead.md, agents/probe.md, artifact/index.html and
scripts/compute.py from the branch. Tell me the starting balance, the
estimated cost and budget_usd before running.

A1. Agents — call list_agents first and reuse agents with these names
(update instructions and model if they differ); otherwise create_agent:
  "AI Visibility Probe — ChatGPT"  model=gpt-6-sol          web_search=auto  user_prompt=<probe.md>
  "AI Visibility Probe — Claude"   model=claude-sonnet-5-5  web_search=auto  user_prompt=<probe.md>
  "AI Visibility Probe — Gemini"   model=gemini-3.8-flash   web_search=auto  user_prompt=<probe.md>
  "AI Visibility Checker — Lead"   model=gemini-3.8-flash   web_search=auto  user_prompt=<lead.md>
Every run: run_agent with a NEW operation_key (the lead also with
subagent_limits={"cap_usd": 0}), poll get_run with since=<next_since> until
poll_complete=true, read truncated results with read_run_result.

A2. Plan — run the lead: {"phase": "plan", "website": "YOUR-SITE.com",
"prompt_count": 30}. Show me the mind map in a few lines and continue.

A3. Visibility — split the prompts, in order, into batches of 10 (b1, b2, …)
and start one probe run per batch per engine (at most 6 running at a time):
  mode: visibility
  engine: <chatgpt | claude | gemini>
  batch: <b1 | b2 | …>
  target: {"name": "<plan.target.name>", "domain": "<plan.target.domain>"}
  prompts: [<the batch's prompts, exactly as written>]
  Return only the JSON described in your instructions.
Retry a failed run once with a new operation_key; otherwise leave it out
and say so.

A4. Competitors — the 5 brands named in the most answers, excluding the
site: run scripts/compute.py (assemble, then competitors) if you can run
Python, otherwise run the lead with {"phase": "analyze", "plan": …,
"engines": […], "visibility": [<every visibility answer>]}.

A5. Sentiment — one probe run per engine, in parallel:
  mode: sentiment
  engine: <engine id>
  use_case: "<plan.use_case>"
  brands: ["<plan.target.name>", "<competitor 1>", … "<competitor 5>"]
  Return only the JSON described in your instructions.

A6. Report — if you can run Python: save every probe answer, unchanged, as
probes/vis-<engine>-<batch>.json and probes/sent-<engine>.json, plus
plan.json and engines.json, then
  python3 scripts/compute.py assemble plan.json engines.json probes/ raw.json
  python3 scripts/compute.py compute raw.json out/ --auto-insights
and publish out/data.js. Otherwise run the lead with the A4 message plus
"sentiment": [<the three sentiment answers>], check every number quoted in
its insights against its metrics, and use
data.js = "window.REPORT = " + <report JSON> + ";".

A7. Publish — create_artifact name="AI Visibility — YOUR-SITE.com"
operation_key=<new>, files: index.html = artifact/index.html unchanged,
data.js as built in A6, both sent as content in that call. Check with
read_artifact_files that both are there.

A8. Answer me with the artifact link (https://app.flymy.ai/artifacts/...),
the final spend against budget_usd, and a 5-line summary: visibility % (and
points per answer), best and worst engine, the intent where I'm most absent
and who owns it, the top competitor's share of voice, and my sentiment index
vs. the best competitor's.
```

To re-check later, run it again (ROUTE A can publish the new `data.js` as a
new artifact version with `publish_artifact_version`).
