# Example: chiaro.ai

A real run of the checker on 5 Nov 2026: 12 non-branded prompts × 3 engines
(ChatGPT `gpt-6-luna`, Claude `claude-haiku-4-5`, Gemini `gemini-3.8-flash`,
each with its vendor's own web search), all through FlyMyAI.

**Report artifact:** https://app.flymy.ai/artifacts/8d1001b8-9ed8-4c12-8fc1-ccec6f41727f

| | |
|---|---|
| AI visibility | **5.6%** — named or cited in 2 of 36 answers |
| By engine | ChatGPT 0% · Claude 8.3% (ranked #1 and cited for "take photo of landmark get audio explanation") · Gemini 8.3% (#6 for "free spoken audio guide for art galleries") |
| Share of voice | Chiaro 3.4% vs. Smartify 31.0%, Google Arts & Culture 19.0%, Bloomberg Connects 19.0%, izi.TRAVEL 17.2%, VoiceMap 10.3% |
| Sentiment index | Chiaro **72**/100 (ChatGPT 60, Claude 85) vs. Smartify 85, Bloomberg Connects 76, Google Arts & Culture 74, izi.TRAVEL 74, VoiceMap 68 |

The engines like Chiaro when asked about it directly (positive tone across the
board), but they rarely bring it up unprompted: it's a discovery problem, not
a reputation problem.

Cost: about $1.30 of FlyMyAI balance ($1.25 for the probe subagents, plus the
lead agent).

Gemini's sentiment probe didn't run in this example because the $2.50
subagent cap ran out, so the sentiment index here averages only ChatGPT and
Claude. `PROMPT.md` now defaults to a $4 cap.

## Files

- `report.raw.json` — the lead agent's output, unchanged except for the
  `generated_at` timestamp and a `notes` field
- `report.json`, `data.js` — the same data after `scripts/compute.py`
  re-derived every metric (it matched the agent's numbers)

Preview: copy `data.js` next to `artifact/index.html` and open the HTML file.
