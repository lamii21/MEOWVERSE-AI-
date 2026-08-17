# MeowVerse — LinkedIn Launch Post

## The post

---

I started this project wanting to build a simple cat breed classifier
to practice deep learning. It did not stay simple. 🐱

**MeowVerse** is what it turned into: a full-stack AI platform where
every AI output is honestly labeled as a real model prediction,
AI-generated creative content, or a deterministic fallback — and that
distinction is enforced in the schema, not just the UI copy.

**What it does:**
Upload a cat photo and MeowVerse fine-tunes MobileNetV3-Small
(transfer learning on the Oxford-IIIT Pet dataset) to predict its
breed — 87.5% top-1 accuracy on a held-out test set. Then it shows you
*why*, with a Grad-CAM explanation I implemented from scratch against
the model's real gradients. It finds visually similar cats through a
FAISS-backed embedding search. It generates an AI-inspired personality
from a deterministic scoring engine, an optional AI-written story, and
an AI portrait that's actually conditioned on your cat's real photo —
not a generic "British Shorthair" stock image.

**The part I'm proudest of isn't the model — it's the guarantees.**
The LLM that writes personality narratives literally cannot overwrite
the deterministic trait scores, because the schema it's forced to
respond in has no field for them. If no AI API key is configured, the
entire product still works — every feature degrades to a clearly
labeled deterministic fallback instead of crashing or faking a result.

**Engineering challenges that taught me the most:**
- OpenCV's GrabCut segmentation turned out to be non-deterministic —
  it draws from its own internal RNG, completely separate from
  scikit-learn's `random_state` sitting right next to it in the same
  function. Five identical calls, three different results, until I
  found and seeded it explicitly.
- Dockerizing the ML pipeline surfaced two bugs I didn't expect:
  `torch` silently resolving a CUDA-bundled wheel on Linux (turning a
  ~500MB image into 3.4GB) despite my own code comments saying
  CPU-only was already chosen, and a package conflict between
  `opencv-python` and `opencv-python-headless` that left `cv2`
  importable but subtly broken — my first fix attempt made it *worse*
  before I found the real one.
- A privacy test kept flaking across sessions. The real cause: a
  hardcoded test fixture color combined with permanent content-hash
  deduplication meant every local test run was silently leaving
  historical data behind. The fix wasn't a "more distinctive" constant
  (I tried that once already) — it was making the fixture genuinely
  unique on every run.

**What I learned:** the difference between "the model works" and "the
system is trustworthy" is mostly about what happens at the edges —
what you do when the AI provider is down, when the upload is
malformed, when two processes disagree about state. That's where I
spent most of this project's engineering time, and it shows: 458
backend tests, 193 frontend tests, a real Docker-based production
verification, and a written validation report that says "NOT
VERIFIED" exactly where something genuinely wasn't.

🔗 GitHub: [link]
🎥 Demo: [link]

#MachineLearning #ComputerVision #DeepLearning #ExplainableAI #GenerativeAI #FullStackDevelopment #FastAPI #NextJS #PyTorch #SoftwareEngineering

---

## Shorter alternative (if LinkedIn's algorithm favors brevity)

---

I set out to build a simple cat breed classifier. It became
**MeowVerse** — a full-stack AI platform combining computer vision,
explainable AI, visual similarity search, and generative AI, with one
rule I held myself to throughout: never claim more certainty than a
real measurement supports.

🧬 A fine-tuned CNN (87.5% top-1 accuracy) predicts your cat's breed
🩻 Grad-CAM, implemented from scratch, shows *why*
🔍 FAISS-backed visual similarity search finds cats that actually look alike
🧠 A deterministic personality engine — with an LLM layer that's
   schema-guaranteed to never overwrite what it computed
🖼️ AI portrait generation conditioned on your cat's real photo, not a
   generic prompt

The engineering challenge I keep coming back to: Dockerizing the real
ML pipeline surfaced a silent CUDA-wheel install bloating the image to
3.4GB, and an OpenCV package conflict where my first fix made things
worse before I found the real one. Both only showed up because I
insisted on actually *running* the built container, not just trusting
`docker build`'s exit code.

458 backend tests, 193 frontend tests, a full production Docker
verification — and an honest validation report documenting exactly
what wasn't tested too.

🔗 GitHub: [link]

#MachineLearning #ComputerVision #ExplainableAI #GenerativeAI #FullStack

---

## Notes on tone

- Both drafts lead with the honest origin story (simple idea →
  real scope), not a claim of grandeur — this reads as authentic
  rather than inflated.
- Every technical claim in both drafts is traceable to a real,
  verified fact in this repository (see
  [CV_PROJECT_DESCRIPTION.md](CV_PROJECT_DESCRIPTION.md) and
  [AI_VALIDATION_REPORT.md](../AI_VALIDATION_REPORT.md)) — nothing
  here should be posted without those numbers still matching the repo
  at the time of posting.
- Replace `[link]` placeholders before posting — no URL is invented
  here.
- A couple of cat emoji are used deliberately (🐱), matching the
  project's own playful identity, without turning the post into
  something that undercuts its technical credibility.
