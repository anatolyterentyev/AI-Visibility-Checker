# AI Visibility Checker

**Free, open-source check of how AI assistants see your website.**
Does ChatGPT, Claude or Gemini mention you when a buyer asks for what you do —
and how likely are they to recommend you versus your competitors?

It measures just two things:

| Metric | Question it answers |
|---|---|
| **AI visibility %** | Out of all non-branded buyer prompts × AI engines, in how many answers is your site **mentioned or cited**? Plus: which competitors AI names instead (share of voice). |
| **Sentiment index (0–100)** | Each engine is asked how likely it is to recommend you — and each competitor — for your use case. The index is the average across engines. |

All models are reached through **[FlyMyAI](https://flymy.ai)**: one account,
one balance, no OpenAI / Anthropic / Google keys. The report is published as a
**FlyMyAI artifact** (a shareable web page).

**Example — [chiaro.ai](examples/chiaro.ai/):** 5.6% AI visibility (ChatGPT 0%,
Claude 8.3%, Gemini 8.3%), 3.4% share of voice against Smartify's 31%, and a
sentiment index of 72/100 against Smartify's 85. The engines like the product
when asked about it, but rarely bring it up on their own.

---

## Quick start (2 minutes)

1. Connect the FlyMyAI MCP to your AI assistant (Claude Code, Claude, Cursor,
   Codex, ChatGPT …): https://docs.flymy.ai/agents/guides/ai-assistants
2. Open [`PROMPT.md`](PROMPT.md), copy the prompt, replace `YOUR-SITE.com`.
3. Paste it into the assistant. It creates the agents on your FlyMyAI account,
   runs the check, and returns a link to your report artifact.

A run with 12 prompts × 3 engines on the flagship models costs roughly $3–5
of FlyMyAI balance.

---

## How it works

```
             ┌────────────────────────────── Lead agent (FlyMyAI) ──────────────────────────────┐
 website ──▶ │ 1. read the site      2. prompt mind map (non-branded, 2–10 words)               │
             │                         e.g. "app to recognize artworks"                         │
             │ 3. visibility probes ─┬─▶ ChatGPT probe (GPT + OpenAI web search)                │
             │                       ├─▶ Claude probe  (Claude + Claude web search)             │
             │                       └─▶ Gemini probe  (Gemini + Google Search)                 │
             │ 4. competitors = brands the engines recommended most                             │
             │ 5. sentiment probes: each engine scores you + competitors 0–100                  │
             │ 6. compute metrics → JSON report                                                 │
             └──────────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
                           FlyMyAI artifact (artifact/index.html + data.js)
```

1. **Understand the site.** The lead agent reads the website and writes down
   the product, category, audience and the jobs it solves.
2. **Prompt mind map.** It builds a tree: category → 3–5 intents → 2–5 prompts
   each. Prompts are 2–10 words, typed the way people talk to ChatGPT, and
   **never contain your brand** — we measure discovery, not reputation.
3. **Visibility probes.** For every engine, a probe subagent runs on that
   vendor's model with that vendor's own web search
   (`web_search=auto` on FlyMyAI), answers every prompt as it would for a real
   user, and reports the brands it recommended (in order) and the URLs it cited.
4. **Competitors** are not configured — they are discovered: the brands the
   engines named most often across all answers.
5. **Sentiment probes.** Every engine describes you and each competitor and
   gives a 0–100 "would I recommend it for this use case" score, plus tone,
   pros and cons.
6. **Report.** The lead returns one JSON object
   (`schema: ai-visibility-checker.v1`); the assistant publishes it with the
   report page as a FlyMyAI artifact.

### Formulas

- **Visibility % (engine)** = answers that mention **or** cite you ÷ prompts
  answered by that engine × 100
- **Visibility % (overall)** = same over all prompt × engine pairs
- **Share of voice** = your mentions ÷ mentions of you + top 5 competitors
- **Sentiment index (brand)** = mean of the engines' 0–100 recommendation
  likelihoods

## Repository

| Path | What it is |
|---|---|
| [`PROMPT.md`](PROMPT.md) | The public prompt: paste into any assistant connected to FlyMyAI |
| [`agents/lead.md`](agents/lead.md) | Instructions of the orchestrating lead agent |
| [`agents/probe.md`](agents/probe.md) | Instructions of the per-engine probe agent (visibility + sentiment modes) |
| [`artifact/index.html`](artifact/index.html) | The report page; reads `window.REPORT` from `data.js` |
| [`scripts/compute.py`](scripts/compute.py) | Re-derives every metric from the raw answers and writes `report.json` + `data.js` (no dependencies) |
| [`examples/chiaro.ai/`](examples/chiaro.ai/) | A real run on chiaro.ai: raw and recomputed JSON + `data.js` |

Preview a report locally: copy an example's `data.js` next to
`artifact/index.html` and open the HTML file in a browser.

## Customising

- **Models:** the probes use each vendor's newest flagship on FlyMyAI —
  GPT-6 Sol (`gpt-6-sol`), Claude Sonnet 5.5 (`claude-sonnet-5-5`) and
  Gemini 3.8 Flash (`gemini-3.8-flash`, the newest Gemini FlyMyAI offers).
  Swap in `claude-opus-5-5` for Claude if you want Anthropic's top model
  (about 2× the price of Sonnet 5.5). The public prompt tells the assistant
  to check `list_agent_models` and move to newer models as they appear.
- **More engines:** add another probe agent (e.g. Grok, `grok-4.7`) and add it
  to `engines` in the run message.
- **More prompts:** `prompt_count` up to 20 (cost grows linearly).

## Limitations

This is a basic, honest approximation, not a panel of real users. Answers from
the API models with web search differ from the consumer apps (personalisation,
memory, model version), and each prompt is asked once per engine, so small
percentages are noisy. Re-run weekly and watch the trend rather than a single
number.

## License

MIT — free for anyone. Model access via [FlyMyAI](https://flymy.ai).
