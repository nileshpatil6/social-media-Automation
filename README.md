# socialautom

**An autonomous, quality-gated YouTube Shorts pipeline.**
Built for [@ItsCodytek](https://www.youtube.com/@ItsCodytek).

One command turns a topic into a finished vertical video: a sourced script,
narration with word-level timing, synced captions, designed motion graphics,
and a vision-model QA pass on the rendered frames before anything is published.

```bash
npm run make -- "why AI agents keep failing at long tasks"
```

![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white)
![Remotion](https://img.shields.io/badge/Remotion-4-0b84f3)
![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)
![Node](https://img.shields.io/badge/Node-%E2%89%A520-339933?logo=node.js&logoColor=white)

---

## Contents

- [How it works](#how-it-works)
- [Design principle: typed visuals](#design-principle-typed-visuals)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Publishing and compliance](#publishing-and-compliance)
- [Project structure](#project-structure)
- [Retention rules](#retention-rules)

---

## How it works

```
topic
  └─► storyboard      script and visuals written together as typed scenes
  └─► assets          stock footage (Pexels) or AI backdrops (fal), optional
  └─► narration       one TTS request for the whole script, plus word timings
  └─► assemble        scene boundaries snapped to the spoken words
  └─► QA stills       one frame per scene, scored by a vision model
  └─► repair loop     failing storyboards are rewritten and re-checked
  └─► render          final 1080x1920 MP4
  └─► review          out/review/<slug>/  (nothing goes live automatically)
  └─► publish         manual, one command
```

| Stage | Implementation |
|---|---|
| Storyboard and QA brain | Claude, via the `claude` CLI (default) or the Anthropic API |
| Narration | Deepgram Aura-2 (default) or ElevenLabs, behind one provider interface |
| Timing | Character or word alignment from the voice provider, never a WPM estimate |
| Rendering | Remotion 4, React 19 |
| Upload | YouTube Data API v3 |

## Design principle: typed visuals

Most automated Shorts are a TTS voiceover over generated pictures. Viewers
recognise the pattern and scroll past it.

socialautom inverts that. Every visual is one of **11 typed scene primitives**,
each a React component rendering real information through a locked design
system:

| Data | Structure | Media |
|---|---|---|
| `STAT_REVEAL` | `DIAGRAM_FLOW` | `DEVICE_MOCK` |
| `CHART_ANIM` | `TIMELINE` | `BROLL_MASKED` |
| `COMPARE_SPLIT` | `LIST_STACK` | `QUOTE_CARD` |
| `CODE_TYPE` | | `LOOP_END` |

The storyboard agent cannot request "an image of X". It can only fill in a zod
schema (`src/types/scene.ts`), validated at runtime with an automatic repair
loop. Generated imagery is permitted only as a backdrop behind a scene that
already carries its meaning in typed props, and is capped at one third of
scenes by a schema refinement.

The **vision QA gate** then inspects the rendered frames themselves. In
testing it caught a clipped diagram node, a badge overlapping text, and two
closing scenes that looked identical, none of which are detectable from the
storyboard data alone.

## Getting started

### Prerequisites

- Node.js 20 or newer
- The [Claude Code](https://claude.com/claude-code) CLI on your `PATH`
  (for the default `cli` brain), or an Anthropic API key
- A Deepgram or ElevenLabs API key

### Install

```bash
npm install
cp .env.example .env       # then fill in the keys below
npm run studio             # live preview at http://localhost:3000
```

## Configuration

### Environment

| Variable | Purpose | Required |
|---|---|---|
| `VOICE_PROVIDER` | `deepgram` (default) or `elevenlabs` | no |
| `DEEPGRAM_KEY` | Narration and alignment via Deepgram | if Deepgram |
| `DEEPGRAM_VOICE` | Aura-2 voice, default `aura-2-apollo-en` | no |
| `ELEVENLABS_API_KEY` | Narration via ElevenLabs | if ElevenLabs |
| `ELEVENLABS_VOICE_ID` | Voice to use; browse with `npm run voices` | if ElevenLabs |
| `BRAIN_PROVIDER` | `cli` (default, uses your Claude plan) or `api` | no |
| `ANTHROPIC_API_KEY` | Required when `BRAIN_PROVIDER=api` | conditional |
| `PEXELS_API_KEY` | Real stock footage backdrops (free) | no |
| `FAL_KEY` | AI backdrop stills, roughly $0.02 per image | no |
| `QA_ENABLED` | Toggle the vision gate, default `true` | no |
| `QA_MIN_SCORE` | Pass mark out of 100, default `78` | no |
| `QA_REPAIR_LOOPS` | Repair attempts after a failed QA pass, default `1` | no |
| `PUBLISH_MODE` | `review` (default), `private` or `public` | no |

Without Pexels or fal the pipeline still runs; media scenes fall back to the
designed gradient and grid backdrops.

### Tuning

`src/config.ts` holds everything worth adjusting: target length, speaking
rate, voice settings, QA thresholds, the channel's niche and tone, and the
banned-phrase list the writer must avoid. All visual tokens (colour, type,
spacing, motion) live in `src/video/design/`.

### YouTube

```bash
npm run auth:youtube       # one-time OAuth; prints setup steps if unconfigured
```

## Usage

| Command | What it does |
|---|---|
| `npm run make -- "<topic>"` | Full pipeline for one topic, output to `out/review/<slug>/` |
| `npm run trends -- [steer]` | Build a topic queue, informed by the channel's own retention data |
| `npm run batch -- <n>` | Produce the next `n` shorts from the queue, sequentially |
| `npm run publish -- <slug>` | Upload a reviewed short (private by default) |
| `npm run studio` | Remotion Studio for live preview |
| `npm run voices` | List available ElevenLabs voices |
| `npm run sfx` / `npm run music` | Regenerate the sound effect and music beds |
| `npm run typecheck` | TypeScript check with no emit |

Each review folder contains the MP4, a thumbnail, and a `REVIEW.md` with the
QA score, every issue raised, the final script, and the generated metadata.

## Publishing and compliance

```bash
npm run publish -- <slug>                              # private
npm run publish -- <slug> --public
npm run publish -- <slug> --at "2026-08-25T14:00:00Z"  # scheduled
```

- Descriptions include an AI-assistance disclosure and uploads set
  `containsSyntheticMedia`, as YouTube policy requires.
- Numerical claims in scripts must be sourced; `QUOTE_CARD` requires a real
  attribution.
- Nothing is uploaded without an explicit `publish` command.

## Project structure

```
src/
├── types/scene.ts          Scene schemas: the contract between agent and renderer
├── agents/
│   ├── brain.ts            LLM provider abstraction and schema-repair loop
│   ├── storyboard.ts       Writes script and visuals in a single pass
│   ├── qa.ts               Vision gate over rendered stills
│   ├── metadata.ts         Title, description and tags
│   └── trends.ts           Topic selection
├── services/               Deepgram, ElevenLabs, Pexels/fal, YouTube
├── pipeline/               run, assemble, render, publish, trends
└── video/
    ├── design/             Tokens, motion curves, fonts
    ├── scenes/             The 11 primitives and their registry
    └── components/         Shared shell: backdrop, safe area, transitions
scripts/                    OAuth, batch runs, voice listing, audio generation
```

See [`CLAUDE.md`](CLAUDE.md) for architecture notes and the non-obvious
implementation details (asset paths, bundler import rules, font loading).

## Retention rules

The writer is constrained by measured Shorts retention data:

- 50 to 60% of viewers who leave do so in the first 3 seconds
- Hooks under 2 seconds lift average view duration by roughly 30%
- Target swipe-away below 25% for sub-30s videos, 35% for 30 to 60s
- A visual change every 1.5 to 2.5 seconds
- The ending closes the loop so a replay is seamless

---

<sub>Private project. All rights reserved.</sub>
