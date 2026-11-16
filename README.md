# LLM Council Protocol (v4.1)

A manual, evidence-first protocol for getting several AI models to review the same work, packaged as an agent **skill** (`SKILL.md`) that any skills-capable assistant can load, for example Claude Code.

One model coordinates, two other models give independent opinions, one person decides. The protocol exists for a single reason: **do not mistake agreement between models for evidence.** In my own use, three models scored a draft 93, 95 and 88 out of 100 and it still contained factual errors. They only surfaced when the facts were checked against the code and the data instead of the documentation. The protocol is the set of rules I wrote after that.

I use it every week to check public texts (V mode) and to make hard-to-reverse decisions (D mode). Between 2 and 11 November 2026 I logged 10 councils with it. The scorecard has no verdict yet: it needs at least 10 councils per model and group before it says anything about strengths or weaknesses.

## What is in this repository

| Path | What it is |
|---|---|
| `skills/llm-council/SKILL.md` | The skill. Self-contained: phases, rules, prompt templates, scoring schema. Written in Italian, with a configurable output language |
| `scoring/council_stats.py` | Reads the two CSV logs and writes a per-model scorecard (precision, relative coverage, adoption, unique adopted proposals, wrong sources, wrong claims) |
| `scoring/council_registro.csv`, `scoring/council_contributi.csv` | Empty logs with the column headers |
| `examples/` | Two councils of **synthetic** data, only to show the format and to try the script. Not real results |

## How it works

| Phase | Who | What happens |
|---|---|---|
| Triage | Orchestrator | No council (reversible, cheap mistake), **V** (verify a public text), **D** (decide something hard to undo), or both |
| F0. Brief | Orchestrator | Question, constraints, fact sheet with sources. The orchestrator writes and saves its own opinion **before** reading the others |
| F1. Independent opinions | Reviewer A and B | Same prompt, blind. V: check every factual claim, including those everyone agrees on. D: recommendation, best alternative, weakest assumption, pre-mortem |
| F2. Matrix | Orchestrator | Every numbered point, with model names. No proposal is dropped silently. Disputed facts are checked against primary sources |
| F3. Critical round | Reviewer A and B | Only the material disagreements. Every change of position is logged as with or without new evidence |
| F4. Decision | The human | Choice, residual dissent, first step, follow-up date, minutes spent |
| F5. Follow-up | Orchestrator | Outcome of D councils on the agreed date |

Core rules:

- **Primary sources first.** "Active" means configuration plus recent proof of execution. "Implemented" means code. Anything backed only by notes is *declared*, never *verified*.
- **Blind first round.** No model sees another opinion, the coordinator included.
- **One unresolved material error blocks approval.** No 1 to 100 scores: three 1 to 5 votes (feasibility, soundness of assumptions, verifiability).
- **At most two ordinary rounds.** A third only for a new fact, constraint or contradiction.
- **No averages between numbers.** Derive them from the constraints or propose a test.
- **Every objection stays on record**, even when rejected. "No material error found" is a valid answer.
- **The human decides.** Time budget: 10 minutes for V, 25 for D.

## Install (Claude Code)

```bash
mkdir -p ~/.claude/skills/llm-council
cp skills/llm-council/SKILL.md ~/.claude/skills/llm-council/SKILL.md
```

Then run `/llm-council`. On first run the skill asks who the orchestrator, the two reviewers and the decider are, where to keep the logs, and which language to use. In other assistants, save it as `SKILL.md` in the tool's skills folder, or paste it at the start of a chat and say "follow this protocol".

There are no API calls: the orchestrator writes the prompts, the human pastes them into the model apps and brings the answers back. A CLI is used only when the human asks for it, because it can consume credits.

## Scoring

After each council the orchestrator appends rows to the two CSV files and runs:

```bash
cd scoring
python council_stats.py
```

You need `pandas`. Edit `ORCHESTRATORE` and `AREE` at the top of the script first. The script rejects values outside the closed lists and writes `Council - Pagella dei modelli.md`. To see the output on synthetic data, copy `council_stats.py` and the two files from `examples/` into one folder and run it there.

## Related work and scope

- [karpathy/llm-council](https://github.com/karpathy/llm-council) automates a council of models through APIs. This repository is a different thing: a manual protocol with verification rules and scoring. It is not a fork, shares no code, and I am not affiliated with its author.
- This is my personal working protocol, tested on my own tasks. Thresholds marked `[soglia sperimentale]` (experimental threshold) are exactly that. I do not claim that a council beats a single model with the same sources.

## License

MIT, see `LICENSE`.

Author: Daniele Malpassi.
