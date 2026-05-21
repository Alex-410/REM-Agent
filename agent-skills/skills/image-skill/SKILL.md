---
name: image
description: Dual-provider image generator (OpenAI GPT-Image-2 + Google Gemini Nano Banana). Use this skill for all image creation unless the user explicitly invokes a different skill or MCP. Detect whether the user is exploring conceptually (--concept, dual, ALWAYS with diverse prompts), wants a final asset (--hq), text-rich content (--text), wants to place a product in a setting (--reference), or is iterating on a previous result (--session). When the user attaches images: automatically use edit mode.
tools:
  - Bash
  - Read
---

# Dual-Provider Image Generator (GPT-Image-2 + Gemini Nano Banana)

One skill, two providers, one Claude that picks based on the briefing. The skill provides the building blocks; Claude orchestrates the combination. Default mindset: ask as few questions as possible, but make the right choices.

## Reference docs (load on demand)

Don't load these up front. Read them with the `Read` tool only when the
specific situation calls for it.

- **`references/provider-matrix.md`** — load when the briefing is ambiguous
  between GPT and Gemini, or when the user asks "which is better for X". Contains
  the full decision matrix, caveats, and properties summary.
- **`references/concept-mode.md`** — load when running `--concept` and you need
  to construct diverse `--prompts`, or when planning concept → final consistency.
- **`references/modes-and-examples.md`** — load when handling `--reference`,
  `--edit`, sessions, or when you need a concrete invocation example. Also
  contains the preset/quality tables.

## Decision flow

### 1. First check: do I have enough to start?

If the user types only "image" without further context: ask in natural language about the subject and a style direction. For example:

> "What should the image be about? Do you have a style direction in mind, for example photorealistic, editorial illustration, minimalist, 3D, cartoon, or something else?"

Wait for an answer before continuing.

If the user provides a subject but no style AND there is no reference image: ask the style question before generating four concepts. Reason: with `--concept` you would otherwise produce four different styles, but if the user already has a style in mind, three of them are automatically off the table. Better to check first.

When a style is mentioned in the briefing (for example "editorial vector illustration" or "photorealistic portrait") or there is a reference image that implies the style: continue directly without asking.

### 2. Detect the type

Concept mode (`--concept`) for briefings with:
- "concept", "concepts", "ideas", "explore", "brainstorm"
- "variants", "find direction", "what fits"
- "show me something"
- vague or broad descriptions

HQ mode (`--hq`) ONLY for briefings with an explicit final-asset signal:
- "final", "definitive", "for production", "for publication", "for print"
- "now make it HQ", "now in high quality", "in hires"
- "this is the one, deliver the final version"

If the user did not explicitly ask for HQ → DO NOT use `--hq`. See "Cost
discipline" below.

Text modifier (`--text`) for briefings that mention:
- "infographic", "diagram", "schema with labels"
- "headline X", "title Y", "text Z in image"
- "column illustration with heading"

Reference mode (`--reference`):
- "place this product in..."
- "use this [logo/photo/character] in a new scene"
- "in the same style as..."

Edit mode (`--edit`) when the user attaches an image with an edit request.

Session mode (`--session`/`--continue`):
- "build on...", "continue with...", "now also add X"
- follow-up questions to a previous generation

Analyze mode (`--analyze IMAGE`) when the user asks "describe this image",
"what style is this", or wants to save the look as a reusable style fingerprint.
Typical flow:
1. `--analyze ref.jpg --save-style brand-look` → produces JSON + saves to library
2. Later: `--style brand-look "new subject in this style"` → injects the
   fingerprint into the prompt prefix before generation.

### 3. Choose a provider based on the use case

Default for `--concept` without further indication: dual mode (2 GPT + 2 Gemini).
For other modes: load `references/provider-matrix.md` and use the decision table.

Quick fallback rules without loading the matrix:
- Text/layout/identity preservation → **GPT**
- Photorealism/atmosphere/style transfer → **Gemini**
- Edit while preserving real person → **GPT**
- Transparent background → **GPT with `--nobg`** (auto-fallback to gpt-image-1.5)
- Need 2K native → **GPT with `--gpt-2K`**

### 4. Additional questions (max 2 per turn)

Only ask questions that actually change the result. Two is the maximum.

Do ask:
- Style direction if there is no reference image and no style in the briefing
- Orientation/aspect ratio if the briefing doesn't mention shape and the context is unclear
- Provider choice if the briefing balances between GPT and Gemini strengths

Don't ask:
- For `--concept` with a clear style direction or a reference: just run
- Format, background, compression: use defaults unless specifically relevant
- Number of variants: default 4 for concept, 1 for hq

### 5. With `--concept`: load `references/concept-mode.md`

That file has the variation-axis logic and concept→final strategies. Load it
when you need to construct genuinely diverse `--prompts` or plan a multi-step
concept-to-final pipeline.

## Cost discipline: stay low until the user calls for HQ

Iterating in low/medium is fast and cheap (~$0.01–0.10 per round). HQ at 2K
can be 10–20× more expensive AND 2–3× slower. Default everything to medium
unless the briefing explicitly demands HQ.

**Default quality per mode:**
- `--concept` → low (already correct)
- Single-shot generation without preset → medium
- Reference mode (placing X in Y) → medium
- Edit mode (modifying an image) → medium
- Multi-image fusion / merge / combine → medium
- Iterations within a session → medium
- Follow-ups on a concept ("merge these two", "tweak the third one") → medium

**NEVER escalate automatically to `--hq` or `--quality high`** for the above.
Wait for the user to say "now in HQ", "make it final", "production version",
"for print", or similar.

**When in doubt about quality, ask:**
> "Should I do this as a medium-quality iteration step, or do you want the
> final HQ version?"

This rule overrides any example in the reference files that happens to use
`--quality high` — those are syntax demos, not defaults.

## Behavior after generation

Speed of delivery over analysis. Show the files with the shortest possible confirmation:

- For `--concept`: "4 concepts ready, varied along [style/composition/etc]"
- For `--hq`: "Here is your hi-res asset"
- For sessions: "Turn 3 in [session name]"

No analysis, comparison, or suggestions unless asked. Always close with:

> *"Want me to analyze the images or develop a specific direction further?"*

Only when explicitly asked for analysis, critique, or prompt improvement, provide it in detail.

## First-time setup

```bash
pip3 install openai google-genai pillow
```

Open `generate.py` and paste your API keys at the top:
- `OPENAI_API_KEY = "sk-proj-..."`
- `GEMINI_API_KEY = "AIza..."`

## All switches (compact)

**Presets** (pick max 1): `--concept`, `--hq`, `--web`, `--social`
**Modifier** (combinable): `--text` (force Gemini Pro)
**Provider** (pick max 1): `--gpt`, `--gemini`

**Generic:** `--size square|landscape|portrait|auto`, `--quality low|medium|high`,
`--variants N` / `-n N`, `--format png|jpeg|webp` (GPT)

**Diverse prompts:** `--prompts "p1|p2|p3|p4"`

**Gemini:** `--aspect-ratio`, `--resolution 512|1K|2K|4K`,
`--gemini-model flash|nb2|pro|auto`, `--grounding`

**GPT:** `--background auto|opaque|transparent`, `--nobg` (transparent →
gpt-image-1.5), `--gpt-1K` / `--gpt-2K` (native 2K; 1K default),
`--moderation auto|low`, `--compression 0-100`

> **Batch consistency**: GPT with `--variants N` (max 8) returns a
> character-consistent set on gpt-image-2.

**Reference/edit (single-provider):** `--reference IMAGE` (multiple allowed),
`--edit IMAGE`, `--edit-latest [DIR]`, `--mask IMAGE`

**Sessions (single-provider):** `--session NAME`, `--continue`,
`--reset-session NAME`, `--list-sessions`

**Analyze (single-provider, Gemini):** `--analyze IMAGE`,
`--save-style NAME` (save analyzed style to library), `--style NAME`
(inject saved style into prompt), `--list-styles`

**Cost tracking:** `--costs [--days N]`

**Workflow:** `--skipquestions`

## Output

In the current working directory:
- `2026-05-16_141523_your-prompt-slug_gpt_v1.png`
- `2026-05-16_141523_your-prompt-slug_gemini_v1.png`
- `2026-05-16_141523_your-prompt-slug_gemini_dash.png` (session-tagged)
- `.txt` sidecar per image with prompt + settings

Cost records: `./.image-sessions/costs.json` (per project).
Style library: `~/.claude/skills/image/.styles/{name}.json` (global, reusable
across projects).

## What is NOT in this skill (deliberately)

- `input_fidelity` GPT parameter (rejected by gpt-image-2; gpt-image-1.5 fallback also uses auto)
- Gemini `includeThoughts` (debug-only)
- Files API for edit (inline_data is enough <20MB)
- Image search grounding separate from web search grounding
