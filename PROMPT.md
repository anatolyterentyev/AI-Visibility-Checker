# Public prompt — build your own AI Visibility Checker on FlyMyAI

Copy everything inside the block below into any AI assistant that is connected
to the **FlyMyAI MCP** (Claude Code, Claude, Cursor, Codex, ChatGPT …).
Replace `YOUR-SITE.com` with your website. That's all.

Not connected yet? Add the FlyMyAI MCP to your assistant
(https://docs.flymy.ai/agents/guides/ai-assistants) and sign in with your
FlyMyAI account. Every model call (ChatGPT, Claude, Gemini) runs through your
FlyMyAI balance — no OpenAI / Anthropic / Google keys needed.

A run with 12 prompts × 3 engines costs roughly **$1–2** on FlyMyAI.

---

```text
Build and run an AI Visibility Checker for YOUR-SITE.com on FlyMyAI.
Use only FlyMyAI MCP tools. Source of truth (open source):
https://github.com/anatolyterentyev/AI-Visibility-Checker

GOAL
Measure two things and show them as a FlyMyAI artifact:
1. AI visibility % — in how many AI answers to non-branded buyer prompts the
   site is mentioned or cited, per engine (ChatGPT, Claude, Gemini), plus the
   competitors that AI recommends instead (share of voice).
2. Sentiment index — every engine scores the site and each competitor 0–100
   for "how likely would you recommend it for this use case"; index = average.

STEP 0 — Get the instructions
Fetch these files from the repo (raw.githubusercontent.com, branch main):
  agents/probe.md   – instructions of the per-engine probe agent
  agents/lead.md    – instructions of the orchestrating lead agent
  artifact/index.html – the report page
If you cannot fetch them, write equivalent instructions yourself from the
GOAL and the steps below, keeping the JSON contract described in STEP 3.

STEP 1 — Create three probe agents (reuse them if they already exist in my
account under the same names: list_agents first)
  create_agent name="AI Visibility Probe — ChatGPT" model=gpt-6-luna        web_search=auto user_prompt=<probe.md>
  create_agent name="AI Visibility Probe — Claude"  model=claude-haiku-4-5  web_search=auto user_prompt=<probe.md>
  create_agent name="AI Visibility Probe — Gemini"  model=gemini-3.8-flash  web_search=auto user_prompt=<probe.md>
web_search=auto means each probe searches with its own vendor's search
(OpenAI search for GPT, Google Search for Gemini, Claude web search for
Claude), which is what real users of those assistants get. Pick other ids from
list_agent_models if you want stronger models or to add Grok (grok-4.7).

STEP 2 — Create the lead agent
  create_agent name="AI Visibility Checker — Lead" model=gemini-3.8-flash user_prompt=<lead.md>

STEP 3 — Run it
  run_agent agent_id=<lead> operation_key=<new uuid>
    message:
      website: YOUR-SITE.com
      prompt_count: 12
      engines: [{"id":"chatgpt","label":"ChatGPT","agent_id":"<probe chatgpt>"},
                {"id":"claude","label":"Claude","agent_id":"<probe claude>"},
                {"id":"gemini","label":"Gemini","agent_id":"<probe gemini>"}]
      Run the full check and return only the JSON report.
    subagent_limits: {"agents":[<the three probe ids>],"cap_usd":2.5,
                      "max_children":6,"max_parallel":3}
Poll get_run with since=<next_since> until poll_complete=true; read the full
result with read_run_result if it is truncated. The result is a JSON object
with schema "ai-visibility-checker.v1" (target, engines, mindmap, visibility,
prompts, leaderboard, sentiment, insights). Validate that it parses and that
the numbers are consistent with the per-prompt results; if a number is off,
recompute it from "prompts" and "sentiment" yourself.

STEP 4 — Publish the report as a FlyMyAI artifact
  create_artifact name="AI Visibility — YOUR-SITE.com" operation_key=<new uuid>
    files:
      index.html = artifact/index.html from the repo, unchanged
      data.js    = "window.REPORT = " + <the JSON report> + ";"
  share_artifact visibility=link
Give me the share link, then a 5-line summary: overall visibility %, the best
and worst engine, the top competitor and its share of voice, my sentiment
index vs. the best competitor's, and the single most important fix.

To re-check later, run STEP 3 again with a new operation_key and publish the
new data.js as a new artifact version (publish_artifact_version).
```
