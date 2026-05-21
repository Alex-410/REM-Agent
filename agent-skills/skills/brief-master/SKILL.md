---
name: brief-master
description: Writes sharp, precise agent briefs and prompts for OpenClaw agents and cron jobs. Use when asked to write a brief for any agent — dev agents, code reviewers, testers, researchers — or when writing a cron job prompt, a sessions_spawn task, or any instruction that will be executed by an AI agent. Extracts 9 dimensions of intent, asks max 3 clarifying questions, runs a token efficiency audit, and delivers one clean brief. Prevents vague briefs that cause agent failures. Triggers on "write a brief", "write a prompt for", "help me write the agent brief", "draft the cron job", "write the sessions_spawn task".
---

# Brief Master

Write agent briefs that agents actually execute correctly.

Every wasted token is a wasted API call. Every vague word is a future bug. Every missing acceptance criterion is a future rework cycle.

Read `references/9-dimensions.md` before extracting intent.
Read `references/brief-formats.md` for the right format per agent type.

## The Pipeline

1. **Detect the target** — which agent, what runtime (subagent, cron, sessions_spawn)?
2. **Extract 9 dimensions** — see `references/9-dimensions.md`
3. **Ask max 3 questions** — only if critical info is missing. Never more.
4. **Apply the right format** — see `references/brief-formats.md`
5. **Run token efficiency audit** — strip every word that doesn't change the output
6. **Deliver** — one clean brief, ready to use

## Token Efficiency Rule

"The best brief is not the longest. It's the one where every word is load-bearing."

Before delivering, ask: does removing this sentence change what the agent does? If not, cut it.

## What Makes a Bad Brief

- Vague task description ("improve the translation")
- No acceptance criteria (how does the agent know it's done?)
- Missing constraints (what must not break?)
- No non-goals (what's explicitly out of scope?)
- Too long (agent loses focus, context drifts)
- Tool-specific instructions missing (which host? which directory? which branch?)

## What Makes a Good Brief

- One clear task per brief
- Explicit ACs labelled AC1, AC2, AC3 (testable, not descriptions)
- Constraints listed
- Non-goals listed
- Correct status update blocks (start + end)
- 95% confidence gate instruction included
- Right tool commands with correct paths

## Mandatory Sections for Dev Agent Briefs

Every brief for a dev/build agent must include:

```
FIRST — update status to working with task description
...task...
LAST — update status to done + notify orchestrator
```

And the 95% confidence gate:
```
Before starting ANY work, ask clarifying questions until you are 95% confident
you can complete this task successfully. Do not start until you have that confidence.
```

See `references/brief-formats.md` for full templates.
