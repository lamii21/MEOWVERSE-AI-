# MeowVerse AI 🐱✨

> "Every cat has a story."

Turn a photo of a cat into a magical, collectible Cat Card and a
personalized short story — real computer-vision breed and fur-color
analysis, combined with clearly labeled AI-generated creative content
(personality, magic power, rarity, and a 5-style illustrated-in-words
cat story), wrapped in a cinematic reveal and a shareable, downloadable
card.

This README is intentionally minimal during early development. See:

- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, folder structure, AI/ML pipeline
- [ROADMAP.md](ROADMAP.md) — phased build plan and current progress
- [PROJECT_STATUS.md](PROJECT_STATUS.md) — what's done, what's next

A full README (features, screenshots, API reference, deployment guide)
is written in Phase 17 once the product is functional end to end.

## Quick start (local development)

Requires Docker Desktop.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Readiness check (DB + Redis): http://localhost:8000/ready

### Running without Docker

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate  # or .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
pnpm install
pnpm dev
```

### Tests & lint

```bash
# backend (needs a local Postgres — see docker-compose.yml, host port 5433)
cd backend && pytest && ruff check .

# frontend
cd frontend && pnpm lint && pnpm test && pnpm build
```

## Real computer vision (optional)

Without any extra setup, breed and fur-color analysis run in **demo
mode** — a clearly-labeled, deterministic placeholder (`breed_mode` /
`colors_mode: "demo"` in the API response). To enable the real models:

```bash
cd backend
pip install -r requirements-ml.txt --extra-index-url https://download.pytorch.org/whl/cu118
python -m ml.scripts.prepare_dataset        # downloads Oxford-IIIT Pet, cat breeds only
python -m ml.training.train_breed_classifier # ~15-20 min on CPU
python -m ml.evaluation.evaluate            # real accuracy/F1/confusion matrix
```

Fur-color analysis (OpenCV + K-means) needs no training — it's real as
soon as `requirements-ml.txt` is installed. See `backend/ml/README.md`
and `ARCHITECTURE.md` §4 for details, and `backend/ml/models/
model_card.json` / `backend/ml/evaluation/evaluation_report.json` for
this repo's actual training run and metrics.

## Real AI-generated profiles (optional)

Without an API key, the cat profile (name, personality, magic power,
...) is a clearly-labeled **offline demo profile** — the app stays
fully functional, no external call is made. To enable real generation:

1. Get an API key from https://console.anthropic.com/
2. Set it in `backend/.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Restart the backend.

`ANTHROPIC_API_KEY` comes only from the environment (never
hard-coded, never committed — `.env` is gitignored, only
`.env.example` with an empty value is tracked), is never exposed to
the frontend (only the backend calls Anthropic), and never appears in
logs (`app/core/logging.py` keeps the `anthropic`/`httpx`/`httpcore`
loggers at `WARNING`). See ARCHITECTURE.md §5 for the provider
abstraction and PROJECT_STATUS.md for the full security/fallback
design.

## Real AI-generated stories (optional)

Same setup as profiles above — no separate key needed. From an
analyzed cat, pick one of 5 styles (Magical Adventure, Cozy &
Wholesome, Funny & Chaotic, Dreamy & Emotional, Fantasy Quest) and
click "Write My Cat's Story". Without `ANTHROPIC_API_KEY` configured,
you still get a complete, clearly-labeled **offline demo story**
(`story_mode: "demo"`) — deterministic per cat + style, and Regenerate
still visibly cycles between a few hand-written variants even offline.
Stories are private by default; clicking Share makes that one story
viewable at its own `/story/[id]` link.

Story generation needs the analysis to have been saved to Postgres
first (`docker compose up` includes Postgres on host port **5433** —
not the Postgres default 5432, remapped to avoid colliding with a
locally-installed Postgres service; see `docker-compose.yml`). If the
database is unreachable, the rest of the analysis (breed, colors,
profile) still works — only the story section will say so and skip
itself.

## The Cat Card

Every analysis becomes a collectible Cat Card: a cinematic reveal
("A new cat has appeared...") settles into a card showing the cat
photo, name, title, breed, a labeled "Model confidence" meter (never
framed as certainty about your cat's actual identity), a designer-style
fur palette, personality, magic power, and a rarity badge (Common
through Mythical — a playful game mechanic, not a scientific
measurement, with a correspondingly restrained visual treatment per
tier: plain → tinted → shimmer → glow → aura → particles). Hover for a
subtle 3D tilt on desktop; tap on mobile.

Card actions are all real, not stubs: **Save** persists it to your
account's collection, **Favorite** and **Share** work the same way
(Share marks it public and copies a `/cat/[id]` link, or opens your
device's native share sheet where available), **Download PNG** exports
the actual card as an image file, and **Story** jumps to story
generation. **Generate Wallpaper** is an honest placeholder — disabled
with a "coming soon" label — pending Phase 14's image generation.

## Accounts & your cat collection

You can explore MeowVerse as a guest — upload a photo, get a full
analysis and story, view the result — with no account required.
Creating an account is only needed to keep what you find: clicking
**Save** as a guest shows a prompt to register or log in, after which
that cat (and everything you save from then on) belongs to your
account.

- **Register** at `/register`, **log in** at `/login` — email +
  password, hashed with `bcrypt` (never stored in plaintext, never
  logged).
- Sessions are **httpOnly cookies** backed by a database-stored,
  revocable token (not a JWT) — logging out immediately invalidates
  the session server-side. See ARCHITECTURE.md §11 for the full
  security rationale.
- **`/collection`** — "My Cat Universe": your full gallery, real stats
  (total/favorites/stories/rare+/legendary+/completion%), filters
  (rarity tiers, Favorites, Stories, Recently Discovered), debounced
  search (name/breed/color), sort (newest/oldest/name/rarity/breed/
  favorite), and two original views: a **MeowVerse Map** (a
  constellation of your discovered cats, no 3D engine — plain
  SVG/CSS/Framer Motion) and a **Breed Explorer** (every breed the
  classifier recognizes, locked until you discover it).
- **`/profile`** — your level, XP bar, stats, favorite cat, and
  achievements, all computed from your real saved cats — never
  fabricated.
- **`/achievements`** — 9 milestones (First Paw, Cozy Collector,
  Collector, Rare Hunter, Royal Encounter, Color Collector, Storyteller,
  Dream Keeper, Cat Home), each unlocked by a real action, with a
  progress bar toward the locked ones.
- A saved cat is **private by default**; only clicking **Share**
  makes that specific cat viewable at a public `/cat/[id]` link, and
  only its intended public fields are ever exposed there — never your
  email or account details.

## Progression: XP, levels & achievements

Discovering, favoriting, and sharing cats — and generating stories —
earns XP, calculated and awarded **only on the backend** (the frontend
never sends an XP value, and repeating an action, like toggling
favorite on and off or clicking Regenerate, never pays out twice):

| Action | XP |
|---|---|
| Discover a cat | 100 |
| Favorite a cat (first time) | 10 |
| Generate a story (first time per cat) | 25 |
| Share a cat (first time) | 15 |
| Unlock an achievement | 50 |

Levels follow a documented, easy-to-retune curve (level *N* needs
`100 × (N-1)²` XP), capped at level 20. A "collection completion"
percentage compares the breeds you've discovered against a fixed,
real 12-breed universe (`ml/models/class_names.json`) — never an
invented denominator. See ARCHITECTURE.md §15–18 for the full design,
including how duplicate cats of the same breed are counted honestly
(every cat counts toward your total; only genuinely new breeds move
the completion percentage).

## Cats Like This — visual similarity search

Every analyzed cat gets a real, computer-vision **visual embedding** —
a 576-number fingerprint of how the photo actually looks, produced by
an ImageNet-pretrained model (not this project's own breed classifier,
and not a lookup by breed or color label). Cats with similar-looking
photos land close together in that number space; "Cats Like This 🐾"
(shown on a Cat Card, your collection, and any public `/cat/[id]`
page) searches for the closest ones using
[FAISS](https://github.com/facebookresearch/faiss), Meta's vector
search library.

- Every result shows a real **"N% visually similar"** number — the
  mathematical cosine similarity between two embeddings, never a
  fabricated or hand-picked score. Breed and shared fur colors are
  shown alongside each result as *context*, not as what similarity is
  computed from.
- Respects the same privacy model as the rest of the collection: you
  can only ever match against public cats plus (if signed in) your own
  — never someone else's private cat, never leaked metadata.
- If the embedding model or search index isn't available for some
  reason, the section says so honestly rather than showing a made-up
  result.
- A collapsed "How Similarity Works" note explains the four-step
  pipeline (embed → nearby in vector space → FAISS search → closest
  eligible cats) for anyone curious, without getting in the way of
  everyone else. See ARCHITECTURE.md §19–22 for the full architecture,
  the exact preprocessing/normalization, and measured performance
  numbers.

## Why MeowVerse thinks this is a... — real Grad-CAM explanations

MeowVerse doesn't only predict a breed — it can show you **which
regions of your cat's photo actually contributed most to that
prediction**, using [Grad-CAM](https://arxiv.org/abs/1610.02391)
("Gradient-weighted Class Activation Mapping"), implemented from
scratch against the real trained breed classifier's real gradients —
never a decorative heatmap, never a hard-coded region, never generated
from the breed name alone.

1. Your photo is passed through the same breed classifier that made
   the prediction.
2. MeowVerse computes the gradients of that specific predicted breed's
   score, flowing back to the model's last layer that still has
   spatial information.
3. Those gradients become an importance weight per feature, producing
   a heatmap of the regions that mattered most.
4. The heatmap is colorized and blended onto your original photo — you
   can switch between the **Original**, **AI Focus** (heatmap alone),
   and **Overlay** views.

Click **"Why this breed?"** on any analyzed cat to generate it
on-demand (it's never computed automatically — only when you ask). The
**prediction confidence** (a plain probability, e.g. "91%") and the
**Grad-CAM visualization** are always shown as two separate things —
one is never mislabeled as the other. Grad-CAM is described honestly
throughout as *"an interpretability visualization showing regions that
contributed strongly to the prediction"* — never as proof, certainty,
or a causal explanation of your cat's actual breed. If the analysis
was made in demo mode (no trained model available at the time),
MeowVerse says so plainly instead of faking a result. See
ARCHITECTURE.md §23–24 for the exact algorithm, target layer, and
privacy/caching design, and PROJECT_STATUS.md for real measured
performance and a from-real-photos qualitative review (successes and
failures both included).

## Cat Personality — an AI-inspired personality, honestly labeled

MeowVerse builds a **playful, AI-inspired personality** for every
analyzed cat — but a cat's true personality genuinely cannot be
determined from a photo, and MeowVerse never claims otherwise. The
feature is deliberately split into two halves that are never allowed
to blur together:

1. **8 trait scores** (curiosity, playfulness, calmness, cuddliness,
   confidence, mischief, elegance, adventurousness), each 0-100, computed
   by a **deterministic, documented rules engine** from the same real
   breed and fur-color signals already produced by the classifier and
   color analyzer — no LLM invents these numbers, no random numbers are
   involved, and the same photo always produces the same scores.
   Rarity and Grad-CAM data are both deliberately excluded from
   scoring, so neither collectible tier nor "where the model looked"
   is ever treated as behavioral evidence.
2. A **cute archetype** (like "🌙 Dreamy Explorer" or "🎀 Cozy
   Cuddlebug"), chosen deterministically from those 8 scores, and a
   short piece of **creative interpretation** — a headline, catchphrase,
   secret talent, fictional job, and fun fact — optionally written by
   the same LLM provider used for Phase 6/7's profile and story
   generation. The LLM can only ever produce this creative flavor text;
   it structurally cannot see or alter the trait scores or archetype.
   If no API key is configured or the call fails, a hand-written,
   archetype-specific fallback is used instead and clearly labeled
   "Offline demo content."

Every score is shown as **"AI-inspired curiosity: 69"**, never as "your
cat is 69% curious," and every Cat Personality card carries an explicit
disclaimer: *"Personality is an AI-inspired interpretation of visual
signals, not a scientific assessment of your cat's behavior."*
Regenerating the creative text (owner-only) can never change the
underlying trait scores or archetype — verified by both the caching
design and a dedicated test. See ARCHITECTURE.md §25–28 for the scoring
formula, archetype list, and LLM/fallback design.
