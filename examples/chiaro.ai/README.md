# Example: chiaro.ai

Two real runs of the checker on chiaro.ai, both on 5 Nov 2026, both through
FlyMyAI.

## run-30: the default check (flagship models)

30 non-branded prompts × 3 engines = **90 AI answers**. Each engine used its
vendor's own web search:

| Engine | Model |
|---|---|
| ChatGPT | GPT-6 Sol (`gpt-6-sol`) |
| Claude | Claude Sonnet 5.5 (`claude-sonnet-5-5`) |
| Gemini | Gemini 3.8 Flash (`gemini-3.8-flash`) |

**Report artifact:** https://app.flymy.ai/artifacts/s/81qPErOZ9CjIQl_6

**Cost:** $4.64 of FlyMyAI balance for the whole run (plan, 9 visibility
batches, 3 sentiment runs, analysis), about 20 minutes end to end.

| | |
|---|---|
| AI visibility | **1.1%**: named in 1 of 90 answers (one answer is worth 1.1 points) |
| By engine | ChatGPT 0% · Claude 3.3% · Gemini 0% |
| The one hit | Claude recommended Chiaro **#3**, with a link to chiaro.ai, for "app that explains monuments in Spanish" |
| By intent | Multilingual travel audio 6.7%; every other intent 0% |
| Share of voice | VoiceMap 24.5% · Smartify 20.9% · izi.TRAVEL 20.0% · Rick Steves Audio Europe 18.2% · SmartGuide 15.5% · **Chiaro 0.9%** |
| Sentiment index | Smartify **79** · **Chiaro 63** · VoiceMap 50 · izi.TRAVEL 44 · SmartGuide 44 · Rick Steves 36 |

**What it means:**
- **Chiaro has a discovery problem, not a reputation problem.** When asked
  about Chiaro directly, ChatGPT scored it 89/100 and Gemini 92/100 (both
  higher than Smartify), describing it accurately as a photo-to-audio,
  multilingual guide. But when buyers ask for what Chiaro does, it almost
  never comes up.
- **Claude doesn't know Chiaro yet.** Claude Sonnet 5.5 gave it 8/100 and
  said it couldn't describe the product reliably. That pulls the index down
  to 63; without Claude, Chiaro would lead the field.
- **The intents that fit Chiaro best are owned by others:** Smartify for
  artwork recognition, VoiceMap and izi.TRAVEL for landmark tours, and a long
  tail of new AI-guide apps (Artlas, Musa, SeeMuseums) for "ask questions
  about paintings".

**Caveat:** 49 of Gemini's 118 citations were Google search-redirect links
rather than real URLs, so a Gemini citation of chiaro.ai could have been
missed. Mentions are unaffected, and Gemini never named Chiaro.

### Files

- `plan.json`: the lead agent's site summary and 30-prompt mind map
- `engines.json`: the engines and models used
- `insights.json`: the lead agent's insights. Its per-intent counts in two
  of them were wrong and are corrected against `compute.py`; the note in the
  file says which.
- `probes/`: every probe output exactly as returned: `vis-<engine>-<batch>.json`
  (9 visibility batches) and `sent-<engine>.json` (3 sentiment answers)
- `report.raw.json`, `report.json`, `data.js`: rebuilt from `probes/` with

```bash
python3 scripts/compute.py assemble examples/chiaro.ai/run-30/plan.json examples/chiaro.ai/run-30/engines.json examples/chiaro.ai/run-30/probes examples/chiaro.ai/run-30/report.raw.json --insights examples/chiaro.ai/run-30/insights.json
```

```bash
python3 scripts/compute.py compute examples/chiaro.ai/run-30/report.raw.json examples/chiaro.ai/run-30
```

## run-12: the first, small run

12 prompts × 3 engines on each vendor's small model (GPT-6 Luna, Claude
Haiku 4.5, Gemini 3.8 Flash), with Gemini's sentiment probe missing. It
measured 5.6% visibility, but with 36 answers one answer moved the score by
2.8 points, so it was mostly noise. It's kept for comparison; the checker no
longer defaults to it.
