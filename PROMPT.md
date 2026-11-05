# Public prompt — build your own AI Visibility Checker on FlyMyAI

Copy everything inside the block below into any AI assistant that is connected
to the **FlyMyAI MCP** (Claude Code, Claude, Cursor, Codex, ChatGPT …).
Replace `YOUR-SITE.com` with your website. That's all.

Not connected yet? Add the FlyMyAI MCP to your assistant
(https://docs.flymy.ai/agents/guides/ai-assistants) and sign in with your
FlyMyAI account. Every model call (ChatGPT, Claude, Gemini) runs through your
FlyMyAI balance — no OpenAI / Anthropic / Google keys needed.

The default check is **30 prompts × 3 engines = 90 AI answers** on each
vendor's flagship model. It costs about **$5** of FlyMyAI balance (the
chiaro.ai run cost $4.64) and takes about 20 minutes. `prompt_count` goes
from 10 (quick, noisy) to 100 (precise, roughly 3× the cost).

---

```text
Build and run an AI Visibility Checker for YOUR-SITE.com on FlyMyAI.
Use only FlyMyAI MCP tools. Source of truth (open source):
https://github.com/anatolyterentyev/AI-Visibility-Checker

GOAL
Measure two things and publish them as a FlyMyAI artifact:
1. AI visibility % — in how many AI answers to non-branded buyer prompts the
   site is mentioned or cited, per engine (ChatGPT, Claude, Gemini) and per
   intent, plus the competitors AI recommends instead (share of voice).
2. Sentiment index — every engine scores the site and each competitor 0–100
   for "how likely would you recommend it for this use case"; index = average.

SETTINGS
  website: YOUR-SITE.com
  prompt_count: 30          (10–100)
  batch_size: 10            (prompts per probe run)

STEP 0 — Instructions
Fetch from the repo (raw.githubusercontent.com, branch main):
  agents/lead.md, agents/probe.md, artifact/index.html, scripts/compute.py
If you cannot fetch them, stop and tell me — do not improvise the agents.
Check my balance with whoami and tell me the estimated cost before running.

STEP 1 — Agents (call list_agents first and reuse agents with these names;
update their instructions and model if they exist)
Call list_agent_models and use each vendor's NEWEST flagship model. At the
time of writing:
  "AI Visibility Probe — ChatGPT"  model=gpt-6-sol          web_search=auto  user_prompt=<probe.md>
  "AI Visibility Probe — Claude"   model=claude-sonnet-5-5  web_search=auto  user_prompt=<probe.md>
  "AI Visibility Probe — Gemini"   model=gemini-3.8-flash   web_search=auto  user_prompt=<probe.md>
  "AI Visibility Checker — Lead"   model=gemini-3.8-flash   web_search=auto  user_prompt=<lead.md>
If a newer OpenAI / Anthropic / Google model than these ids is listed, use
it. web_search=auto makes each probe search with its own vendor's search
(OpenAI search for GPT, Google Search for Gemini, Claude web search for
Claude), which is what real users of those assistants get.

Every run below: run_agent with a NEW operation_key (for the lead also
subagent_limits={"cap_usd": 0}: it never starts subagents), then poll get_run with
since=<next_since> until poll_complete=true, and read the full result with
read_run_result when it is truncated. Results are JSON.

STEP 2 — Plan (1 run of the lead)
  message: {"phase": "plan", "website": "YOUR-SITE.com", "prompt_count": 30}
→ plan JSON: target, use_case, mindmap with exactly prompt_count prompts.
Show me the mind map (intent → prompts) in a few lines, then continue.

STEP 3 — Visibility (probe runs in parallel)
Split the mind map's prompts, in order, into batches of batch_size
(b1, b2, …). For EVERY batch and EVERY engine start one probe run:
  message:
    mode: visibility
    engine: <chatgpt | claude | gemini>
    batch: <b1 | b2 | ...>
    target: {"name": "<plan.target.name>", "domain": "<plan.target.domain>"}
    prompts: [<the batch's prompts, exactly as written>]
    Return only the JSON described in your instructions.
30 prompts = 3 batches × 3 engines = 9 runs. Start them all, keeping at most
6 running at a time. A run that fails or returns invalid JSON: retry it once
with a new operation_key; if it fails again, leave it out and say so.

STEP 4 — Competitors (1 run of the lead)
  message: {"phase": "analyze", "plan": <plan JSON>,
            "engines": [{"id":"chatgpt","label":"ChatGPT","model":"<id>"},
                        {"id":"claude","label":"Claude","model":"<id>"},
                        {"id":"gemini","label":"Gemini","model":"<id>"}],
            "visibility": [<every visibility probe output, as returned>]}
→ {"competitors": [top 5 brands]}
(If you can run Python, `scripts/compute.py assemble …` then
`scripts/compute.py competitors raw.json` gives the same list exactly and
saves this run.)

STEP 5 — Sentiment (3 probe runs in parallel, one per engine)
  message:
    mode: sentiment
    engine: <engine id>
    use_case: "<plan.use_case>"
    brands: ["<plan.target.name>", "<competitor 1>", ... "<competitor 5>"]
    Return only the JSON described in your instructions.

STEP 6 — Report (1 run of the lead)
Same message as STEP 4 plus "sentiment": [<the 3 sentiment outputs>].
→ the full report JSON (schema "ai-visibility-checker.v1").
If you can run Python, check it: save plan.json, engines.json and every probe
output into probes/, then
  python3 scripts/compute.py assemble plan.json engines.json probes/ raw.json --insights report.json
  python3 scripts/compute.py compute raw.json out/
and publish out/data.js — its numbers are exact. Otherwise publish the lead's
report as data.js = "window.REPORT = " + <report JSON> + ";".

STEP 7 — Publish the artifact
  create_artifact name="AI Visibility — YOUR-SITE.com" operation_key=<new>
    files: index.html = artifact/index.html from the repo, unchanged
           data.js    = as built in STEP 6
Give me the artifact link, the total cost of all runs, and a 5-line summary:
overall visibility % (and how many points one answer is worth), best and
worst engine, the intent where I'm most absent and who owns it, the top
competitor's share of voice, and my sentiment index vs. the best competitor's.

To re-check later, repeat STEPS 2–6 (or reuse the same plan for a like-for-like
trend) and publish the new data.js as a new version (publish_artifact_version).
```
