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
is written in Phase 16 once the product is functional end to end.

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
with a "coming soon" label — pending Phase 13's image generation.

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
- **`/collection`** — your full gallery: filter by favorites or
  rarity, search by name or breed, sort by newest/oldest/rarity/name.
- **`/profile`** — your stats (cats discovered, favorite breed, most
  common color, legendary cats, stories written) and achievements,
  all computed from your real saved cats — never fabricated.
- A saved cat is **private by default**; only clicking **Share**
  makes that specific cat viewable at a public `/cat/[id]` link, and
  only its intended public fields are ever exposed there — never your
  email or account details.
