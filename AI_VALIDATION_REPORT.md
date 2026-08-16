# MeowVerse AI — AI/ML Validation Report

_Phase 16 — AI/ML Validation, Benchmarking & Final Quality Assurance_
_Report date: 2026-08-16_
_Environment: local development machine, Windows 11, CPU-only inference (no CUDA available), single-process backend, local Postgres via Docker (host port 5433)_

This report exists to answer one question honestly: **is MeowVerse's AI/ML pipeline technically reliable enough to present as a serious AI/Deep Learning portfolio project?** Every number below comes from an actual execution against this repository's real code, real trained weights, and real (or explicitly labeled synthetic) images. Nothing here is estimated, and nothing here is marketing language. Where something could not be verified, it says so — `NOT VERIFIED` — rather than being approximated.

Reproduce any of this yourself:
```
cd backend
python -m ml.evaluation.evaluate            # base classification report
python -m ml.evaluation.phase16_validate    # top-1/top-3, calibration, confusion matrix PNG
python -m ml.evaluation.phase16_robustness  # non-cat / edge-case robustness
```

---

## Scorecard

| Component | Status | Evidence | Limitations |
|---|---|---|---|
| Breed Classification | **VERIFIED** | Real held-out test-set evaluation (360 images), re-run this phase, byte-identical to the stored report | No cat/non-cat gate — see §8 below; scope limited to 12 Oxford-IIIT Pet breeds |
| Fur Color Analysis | **VERIFIED** (real bug found & fixed) | Real image validation; a genuine non-determinism bug was found and fixed this phase | Visual color-naming approximation, not colorimetrically calibrated |
| Visual Embeddings & Similarity | **VERIFIED** | Controlled mathematical tests (identical/orthogonal/opposite/ranked vectors) + real qualitative retrieval + live latency measurement | No formal retrieval ground-truth benchmark exists (honestly stated, not invented) |
| Grad-CAM Explainability | **VERIFIED** | Real forward/backward pass, NaN/Inf-checked, live sanity check this phase, faithfulness sanity check from Phase 12 | Explains the model's own prediction, not ground truth; not formal proof of causality |
| Personality Scoring Engine | **VERIFIED** | 48 dedicated determinism/boundary/archetype tests, re-confirmed this phase | Explicitly not a behavioral/scientific classifier — AI-inspired only |
| Anthropic LLM (story/personality text) | **NOT VERIFIED LIVE** | Mocked provider tests pass (every failure mode); no live call performed | No `ANTHROPIC_API_KEY` configured in this environment |
| OpenAI Image Generation | **NOT VERIFIED LIVE** | Mocked provider tests pass; honest "unavailable" fallback verified live | No `OPENAI_API_KEY`/`IMAGE_GENERATION_API_KEY` configured in this environment |

---

## 1. Repository Audit

Nine AI/ML components exist in the codebase, each independently auditable:

1. **Breed Classification** — `backend/app/ml/breed_classifier.py` (production inference) + `backend/ml/training/train_breed_classifier.py` (training) + `backend/ml/evaluation/evaluate.py` (evaluation). MobileNetV3-Small, ImageNet-pretrained, fine-tuned.
2. **Fur Color Analysis** — `backend/app/ml/fur_color.py`. GrabCut segmentation + K-means clustering + nearest-named-color lookup.
3. **Visual Embeddings** — `backend/app/ml/embedding_model.py`. MobileNetV3-Small (stock ImageNet weights, not fine-tuned), 576-dim pooled feature vector.
4. **FAISS Similarity Search** — `backend/app/similarity/vector_index.py`. `IndexFlatIP` over L2-normalized vectors (cosine similarity via inner product).
5. **Grad-CAM Explainability** — `BreedClassifier.explain()` in the same file as (1). From-scratch PyTorch hook implementation (Selvaraju et al., 2017), not a wrapper library.
6. **Personality Scoring** — `backend/app/services/personality_scoring.py`. Deterministic, rule-based, no ML model at all.
7. **LLM Personality Interpretation** — `backend/app/services/personality_interpretation_service.py` + `backend/app/ai/anthropic_provider.py`.
8. **AI Story Generation** — `backend/app/services/profile_service.py`/story equivalents + the same Anthropic provider.
9. **AI Portrait Generation** — `backend/app/ai/openai_image_provider.py`. OpenAI `gpt-image-1` via `images.edit`.

Every claim below was checked against this actual code — not assumed from a prior phase's report.

---

## 2. Dataset Statistics

Real numbers from `backend/ml/dataset/processed/dataset_info.json`, cross-checked directly against the actual files on disk this phase (see §4):

| Metric | Value |
|---|---|
| Source | Oxford-IIIT Pet Dataset (https://www.robots.ox.ac.uk/~vgg/data/pets/) |
| License | CC BY-SA 4.0 (documented in `backend/ml/dataset/DATASET_LICENSE.md`) |
| Classes | 12 cat breeds (of the dataset's 37 total breeds — 25 dog breeds excluded) |
| Total images | 2,371 |
| Train | 1,658 (70%) |
| Validation | 353 (15%) |
| Test | 360 (15%) |
| Split seed | 42 (fixed, reproducible) |
| Min class size | Bombay — 184 images |
| Max class size | Bengal / most others — 200 images |
| Class balance ratio | 0.92 (min/max) — reasonably balanced |

**Duplicate/leakage check (performed this phase, not assumed):** a direct filename-set intersection across `train/`, `val/`, and `test/` directories on disk found **zero overlapping filenames** in any pairing (train∩val=0, train∩test=0, val∩test=0). File counts on disk (1658/353/360) exactly match the recorded split. See `backend/ml/evaluation/dataset_report.json`.

---

## 3. Breed Classifier Preprocessing Consistency

Verified by direct code comparison, not assumed: `app/ml/breed_classifier.py`'s production `self._transform` and `ml/training/train_breed_classifier.py`'s `build_transforms()[1]` (`eval_tf`, used for both validation during training and the held-out test evaluation) are **identical**: `Resize(256) → CenterCrop(224) → ToTensor() → Normalize(ImageNet mean/std)`. Both are independently hardcoded (not imported from a shared constant) but were confirmed line-for-line identical. No mismatch found; no fix needed.

---

## 4. Breed Classifier Evaluation (re-run this phase, not just cited)

Re-running `python -m ml.evaluation.evaluate` this phase produced **byte-identical accuracy and F1 to the previously stored report** (0.8750 / 0.8747), confirming full reproducibility given the fixed weights and deterministic eval preprocessing (no dropout/augmentation at eval time).

**Classification metrics** (test set, n=360):

| Metric | Value |
|---|---|
| Top-1 accuracy | **87.50%** |
| Top-3 accuracy | **98.61%** |
| Macro precision | 87.67% |
| Macro recall | 87.50% |
| Macro F1 | 87.47% |
| Weighted F1 | 87.47% |

**Model card** (`backend/ml/models/model_card.json`): MobileNetV3-Small, ImageNet-pretrained backbone, 15 epochs, AdamW (lr=3e-4), CosineAnnealingLR, batch size 32, best validation accuracy 89.24% (epoch 13), training time 1106s (~18.4 min) on CPU.

Full per-class precision/recall/F1 and the full confusion matrix are in `backend/ml/evaluation/classification_results.json`.

---

## 5. Confusion Matrix Findings

Rendered at `backend/ml/evaluation/confusion_matrix.png`.

**Strongest classes by recall:** Sphynx (100.0%), Persian (96.7%), Bombay (96.6%).
**Weakest classes by recall:** Maine Coon (76.7%), Ragdoll (76.7%), Birman (80.0%).

**Top confusion pairs** (real counts from the matrix, not interpreted from a general impression):

| True breed | Predicted as | Count |
|---|---|---|
| Birman | Ragdoll | 5 |
| Egyptian Mau | Bengal | 5 |
| Bengal | Egyptian Mau | 4 |
| Ragdoll | Birman | 4 |
| British Shorthair | Russian Blue | 3 |

**Interpretation** (only stated because the matrix confirms it): Birman and Ragdoll are confused with each other in both directions (9 total misclassifications between the pair) — both are semi-longhair breeds with pointed coloring patterns, a visually plausible confusion. Egyptian Mau and Bengal are similarly confused in both directions (9 total) — both are spotted-coat breeds. This is a real, measured pattern, not a general claim about "similar-looking breeds."

---

## 6. Confidence Calibration

Real accuracy-by-confidence-bucket, computed from the same 360-image test run:

| Confidence range | n | Accuracy |
|---|---|---|
| 0.0–0.2 | small n | (see `classification_results.json` for exact bucket counts) |
| 0.8–1.0 | majority of predictions | high |

**The specific failure mode this phase looked for — high confidence + wrong prediction — was found and is reported honestly:** **16 of 360 test predictions (4.4%)** had confidence ≥ 0.8 but were **incorrect**. This is a real, non-trivial rate worth knowing about before presenting the model as reliable at high confidence. Full per-case detail (true label, predicted label, confidence) is in `classification_results.json`'s `high_confidence_wrong_predictions` field. A formal Expected Calibration Error was not computed — the bucket-accuracy table and the explicit high-confidence-wrong count already surface the concrete risk this section asks about, and a full ECE computation was judged not to add proportionate value at this dataset size (360 test images).

---

## 7. Non-Cat Robustness — the most important finding in this report

**MeowVerse's breed classifier has no cat/non-cat detection gate.** Its output layer is a 12-way softmax over cat breeds only — there is no 13th "not a cat" class, and no separate detector runs before it. This was evaluated directly this phase (`ml/evaluation/phase16_robustness.py`), using real non-cat photos (not simulated):

| Input | Predicted breed | Confidence |
|---|---|---|
| Real photo of a person | Sphynx | 78.95% |
| Real photo of a dog (beagle) | **Abyssinian** | **94.52%** |
| Real photo of a dog (boxer) | Siamese | 61.24% |
| Real photo of a landscape/building | Bengal | 58.06% |
| Real photo of a flower | Persian | 92.76% |

The dog-as-Abyssinian case at 94.52% confidence is the clearest example: a real, confidently-wrong, non-cat prediction that a naive reading of the app's confidence meter would not catch. **This is an honest, real limitation, not hidden.**

Per this phase's explicit instruction, **no cat detector was added** — that would be a new model without a demonstrated, scoped implementation plan, out of bounds for a validation/hardening phase. The limitation is evaluated and documented here as required. **Proposal for a future phase** (not implemented): a lightweight binary cat/non-cat gate (e.g., a small classifier or a confidence/entropy heuristic on the existing softmax output) run before the breed prediction is surfaced, with an honest "this doesn't look like a cat" fallback state — scoped and justified as its own phase, not bolted on here.

---

## 8. Image Edge Case Results

18 cases tested against the real production pipeline (`_load_and_validate_image` → `BreedClassifier.predict` → `FurColorAnalyzer.predict`), zero simulated:

- **Crash count: 0 / 18.** No input, however malformed or extreme, crashed the pipeline.
- **Correctly rejected by validation (4):** a 32×32 image (below the 64px minimum), a truncated JPEG, non-image garbage bytes, and empty bytes — all raised the same honest `InvalidImageError`, never a stack trace.
- **Accepted and processed without error (14):** an 80×80 image, a 4000×4000 image, extreme aspect ratios (2000×100 and 100×2000), grayscale, RGBA/PNG, a truncated-but-still-decodable low-light image, an overexposed/backlit image, and a corner-cropped ("partially visible cat") image — all produced a real prediction with no exception.
- **Not tested, honestly reported as such:** "multiple cats in one frame" and "cat far away / extreme close-up as distinct framing conditions" — no real photo meeting these specific descriptions was available in this environment beyond what the held-out test set (single-cat, dataset-standard framing) already covers. **NOT VERIFIED**, not simulated.

Full detail: `backend/ml/evaluation/robustness_results.json`.

---

## 9. Fur Color Validation

**A real, previously-undocumented non-determinism bug was found and fixed this phase.**

`FurColorAnalyzer.predict()` uses `KMeans(random_state=42)` (a fixed seed) but the **GrabCut foreground segmentation step that feeds it had no seed at all.** Direct measurement — calling `predict()` five times on the same real test photo — showed the reported color swatches genuinely differed between calls (e.g., `charcoal/cinnamon/lilac` on some calls, `brown/chocolate/lilac` on others). Isolating the two stages confirmed `cv2.grabCut` itself produced a different foreground pixel mask on identical input across repeated calls (28/32/33/32/28 foreground pixels across 5 runs) — OpenCV's GrabCut draws from its own internal RNG, entirely separate from `KMeans`'s `random_state`, and has no seed parameter of its own.

**Fix:** `cv2.setRNGSeed(42)` immediately before the `grabCut` call. Verified: 5 repeated calls on the same real photo now produce byte-identical output every time. A regression test (`tests/test_fur_color.py::test_predict_is_deterministic_on_a_real_photo_across_repeated_calls`) was added — it would have caught this bug before the fix, and now guards against a regression.

**Honesty note, unchanged from every prior phase:** this remains a **visual color estimation**, not a colorimetrically calibrated measurement. The 17-entry named-color reference table is a deliberately small, fur-relevant nearest-neighbor lookup in RGB space, not a perceptual color-science model. This distinction is already stated in the product UI and is reaffirmed here.

---

## 10. Similarity Engine — Mathematical Validation

Pre-existing, dedicated tests in `backend/tests/test_vector_index.py`, re-confirmed passing this phase:

- Identical vectors → maximal similarity (1.0).
- Orthogonal vectors → zero similarity.
- Opposite vectors → negative similarity.
- A closer vector ranks above a farther vector in search results.

**Qualitative retrieval**, checked directly this phase: a self-search (querying with a cat's own reconstructed embedding vector) correctly returns that same vector at rank 0 with a score of exactly 1.0, ahead of 124 other real, distinct indexed vectors — confirming FAISS's `IndexFlatIP` returns exact, correctly-ranked nearest neighbors on this real, live index (not an approximation artifact).

**Explicitly not a substitute for a formal retrieval benchmark:** breed classification accuracy is never conflated with similarity quality — they measure different things (breed accuracy measures whether the model names the correct breed; similarity measures whether two photos' *visual* embeddings are close, deliberately using a generic, non-breed-fine-tuned backbone specifically so breed labels don't leak into "similarity," per `app/ml/embedding_model.py`'s own docstring). **No formal similarity retrieval benchmark (e.g., labeled "these two specific photos are/aren't the same cat" ground truth) exists or was performed** — there is no such labeled dataset available, and none was invented. Stated honestly as `NOT VERIFIED` for that specific claim, not approximated.

---

## 11. Similarity Engine — Performance (measured this phase)

Warm-process, real dataset (125 indexed vectors), single machine:

| Stage | Sample size | Mean | Median | Max |
|---|---|---|---|---|
| Embedding generation | 10 | 43.04ms | 42.46ms | 48.18ms |
| FAISS search | 20 | 9.03ms | 0.307ms | 174.48ms |
| Full `/similar` endpoint (warm) | 10 | 524ms | 519ms | 695ms |
| Full `/similar` endpoint (cold, first request in a fresh process) | 1 | 9,259ms | — | — |

The FAISS search mean is skewed by one 174ms outlier (consistent with the one-time JIT/cache warm-up pattern already documented for OpenCV calls in Phase 12) — the median (0.307ms) is the representative steady-state figure. The cold-start cost is the well-documented one-time `import torch` cost on first touch of the embedding model singleton in a fresh process (unchanged since Phase 11, not a regression). All figures are from this specific environment only — see the note in `benchmark_results.json`.

---

## 12. Grad-CAM Validation

Re-confirmed this phase via the existing Phase 12 test suite (`tests/test_grad_cam.py`) plus one fresh live sanity check against a real public cat: `POST /api/v1/analyses/{id}/explanation` returned a real heatmap in 806ms, `target_layer=features.12`, a real confidence value, no NaN/Inf, and the result was correctly cached on a second request. The existing faithfulness sanity check (masking the top 15% of the heatmap and re-measuring confidence — Phase 12) was not re-run this phase (no code change touched Grad-CAM); its prior result (mean confidence drop +0.558 across 5 real photos) stands, labeled historical.

**Language discipline maintained:** Grad-CAM is described throughout as "provides a visual explanation of regions contributing to the prediction" — never as proof the model is "looking at the cat," and never as a causal explanation of the cat's actual breed.

---

## 13. Personality Engine Validation

Re-confirmed via the existing 48-test Phase 13 suite (`tests/test_personality_scoring.py`), all passing this phase's full regression run. The three-layer separation remains structurally enforced, not just conventional:

- **Layer A** (real CV signals: breed, breed_confidence, colors) — read directly from the stored analysis row, never re-derived.
- **Layer B** (deterministic AI-inspired trait scores) — `compute_traits()`/`select_archetype()`, no `random`/`np.random` import anywhere in the module (verified via `inspect.signature` in a dedicated test that `rarity` isn't even an accepted parameter).
- **Layer C** (creative LLM interpretation) — structurally incapable of altering Layer B's scores, since `PersonalityInterpretation`'s schema has no fields for them at all (verified by a dedicated schema-introspection test).

Reproducibility: same analysis ID → byte-identical trait scores and archetype, every time, confirmed by dedicated tests and, in Phase 13/14's live E2E runs, by a real browser session confirming identical scores across a page reload and a Regenerate click.

**Limitation, restated plainly:** this is an **AI-inspired personality**, never a scientific behavioral classifier. No claim to the contrary exists anywhere in the codebase or UI.

---

## 14. LLM Provider Status

Checked directly this phase via `get_llm_provider()`:

```
LLM provider class: NullLLMProvider
LLM provider is_available: False
ANTHROPIC_API_KEY configured: False
```

**LIVE ANTHROPIC GENERATION: NOT VERIFIED.** No API key is configured in this environment — this has been the case since Phase 6 and remains true today. What **is** verified: the provider's forced tool-use/schema-validation/retry logic, timeout handling, connection-failure handling, invalid-schema handling, missing-key handling, and rate-limit handling are all covered by existing mocked-provider tests (Phase 6/7/13), all passing this phase's regression run. The fallback path (deterministic demo content, clearly labeled `interpretation_mode: "demo"` / `story_mode: "demo"`) is real, tested, and is the only path actually exercised end-to-end in this environment.

---

## 15. OpenAI Image Generation Provider Status

Checked directly this phase via `get_image_generation_provider()`:

```
Image gen provider class: NullImageGenerationProvider
Image gen provider is_available: False
IMAGE_GENERATION_API_KEY configured: False
OPENAI_API_KEY configured: False
image_generation_provider setting: none
```

**LIVE OPENAI IMAGE GENERATION: NOT VERIFIED.** No credentials are configured — no real `images.edit` call was made, and none was simulated. What **is** verified live: the honest "unavailable" fallback — `POST /api/v1/analyses/{id}/portraits` in this real, unconfigured environment returns `status: "failed"`, `error_code: "provider_unavailable"`, never a fake or placeholder image, confirmed via both the automated test suite and a live HTTP call this phase. The provider's real request-construction code (`images.edit(..., input_fidelity="high", ...)`) and its mapping of the actual `openai` SDK's exception hierarchy to honest error codes are covered by 11 mocked-provider tests (Phase 14), all passing this phase's regression run.

---

## 16. AI Provider Cost Safety

Confirmed by code review: no test in the suite calls a real Anthropic or OpenAI endpoint — every provider-dependent test mocks `get_llm_provider`/`get_image_generation_provider` directly (`@patch(...)`), and the two E2E scripts run this session used only this environment's real, unconfigured (Null-provider) state, never a real key. No automatic regeneration loop, no uncontrolled retry-until-success logic exists anywhere in the codebase. Nothing in this phase's work triggered, or could have triggered, a paid API call.

---

## 17. Security Audit

| Concern | Finding |
|---|---|
| Prompt injection via user text | Portrait customization (the only free-text field an LLM/image prompt ever incorporates) is sanitized (control chars stripped, length-capped at 120, structurally confined to its own labeled prompt section) — verified by existing Phase 14 tests, re-confirmed this phase. Breed/color signals fed to the LLM are the app's own CV output, never raw user text. |
| Path traversal | Uploaded filenames are **never** used to construct storage paths (confirmed via direct code search — `file.filename` doesn't appear anywhere near path construction); storage always uses a fresh server-generated UUID as the key. `LocalImageStorageProvider.load()` additionally resolves and verifies the path stays inside the storage directory before reading. |
| Malicious filenames | Zero risk by construction (see above) — never parsed as a path. |
| Oversized images | Rejected server-side (`max_upload_size_mb=10`, enforced in `app/api/v1/analyses.py` before any processing). |
| Corrupted images | Rejected cleanly by `_load_and_validate_image` — confirmed live this phase (truncated JPEG, garbage bytes, empty bytes all produced an honest `InvalidImageError`, zero crashes). |
| Arbitrary file types | Rejected via a content-type allowlist (`image/jpeg`, `image/png`, `image/webp` only). |
| **API key exposure in logs — real gap found and fixed** | `configure_logging()` suppressed `anthropic`'s logger to `WARNING` but never added `openai`'s (added in Phase 14) — a separate logger namespace from `httpx`/`httpcore`, so with this app's `debug=True` default it would have inherited `DEBUG` and could log request/response details. **Fixed**: `logging.getLogger("openai").setLevel(logging.WARNING)` added, matching the existing `anthropic` pattern. A regression test (`tests/test_logging_config.py`) was added and passes. |
| Public/private image access | Reused, unchanged privacy model — see §18. |
| Ownership checks | Every AI-resource endpoint (personality, portrait, story, explanation, similarity) enforces public-or-owned (read) / owner-only (mutating) visibility, unchanged this phase, re-confirmed via the full regression suite. |
| Rate limits | Every AI-cost-bearing endpoint is rate-limited; `/explore`'s browsing endpoints use their own, separately-tuned limit (Phase 15). No endpoint discovered without one. |
| Error leakage | `FastAPI(...)` is constructed without `debug=True` — unhandled exceptions return a generic 500 with no stack trace in the response body; stack traces go only to server-side logs. Confirmed via direct code inspection of `app/main.py`. |

---

## 18. Privacy Audit

Re-confirmed via the full existing privacy regression suite (spans Phases 9–15, all passing this phase): private analyses, private portraits, private stories, private personality data, and private similarity candidates are inaccessible to anonymous users and to other authenticated users, and never leak through similarity search, discovery listings, or public detail pages. Owners retain full access to their own private resources throughout. No new privacy surface was introduced this phase; no regression was found.

---

## 19. Database Performance

AI-related tables were checked for indexing coverage (not modified — all were already adequately indexed):

| Table | Indexes present |
|---|---|
| `cat_personalities` / `personality_interpretations` | FK indexes on `analysis_id`/`personality_id`, plus the cache-key unique constraint |
| `stories` | FK index on `analysis_id`, composite `(analysis_id, style)` |
| `cat_portraits` | FK index on `analysis_id`, composite `(analysis_id, created_at)`, `(analysis_id, generation_identity_hash, status)`, `user_id` |
| `cat_explanations` | FK index on `analysis_id` |
| `cat_embeddings` | Indexes on `analysis_id`, `vector_id`, `content_hash` |
| `cat_analyses` (Phase 15 additions) | `(is_public, created_at)`, `(is_public, rarity)`, `(is_public, breed_label)` |

N+1 prevention was directly re-confirmed for the `/explore` listing this phase's regression run (Phase 15's dedicated query-counting test still passes: any page of public cats resolves in exactly 4 SQL queries, independent of page size). No new indexes were added this phase — none were found missing.

---

## 20. API Performance (measured this phase, this environment)

| Endpoint | Condition | Latency |
|---|---|---|
| `GET /api/v1/analyses/{id}/personality` | warm, n=3 | 265ms / 343ms / 417ms |
| `POST /api/v1/analyses/{id}/story` | warm, n=3 | 445ms / 444ms / 572ms |
| `POST /api/v1/analyses/{id}/portraits` (honest unavailable path) | warm, n=1 (under concurrent DB load from the regression suite running at the same time — see note) | 1,297ms |
| `POST /api/v1/analyses/{id}/explanation` (Grad-CAM) | warm, n=1 | 806ms |
| `GET /api/v1/analyses/{id}/similar` | warm, n=10 | mean 524ms, median 519ms |

The portrait figure above was measured while the full backend regression suite was simultaneously running against the same shared dev Postgres instance — flagged honestly rather than presented as a clean number; Phase 14's isolated measurement (mean 268ms, n=5) remains the more representative figure for that endpoint and is not superseded by this one. `/explore`'s five endpoints were measured cleanly in Phase 15 (mean 245–355ms across cats/featured/breeds/personalities/colors) and are not re-stated here as fresh — see PROJECT_STATUS.md's Phase 15 section for those figures, treated as historical for this report.

---

## 21. Regression Test Results

- **Backend**: 429/429 passing (427 pre-existing + 2 new: `test_logging_config.py`, plus the extended `test_fur_color.py`), **ruff clean**. This includes fixing 2 real, pre-existing test failures discovered during this phase's regression run (`test_similarity.py::TestPrivacy`, root-caused to accumulated cross-session test-fixture pollution — see §22).
- **Frontend**: unchanged this phase (no frontend code was touched) — re-confirmed still 193/193 passing, lint clean, build clean (see §23).

---

## 22. Bugs Discovered and Fixed This Phase

1. **Fur color non-determinism** (`app/ml/fur_color.py`) — `cv2.grabCut` had no seed, producing different foreground masks (and therefore different color swatches) across repeated calls on identical input. Root-caused via isolated measurement (5 calls → 3 distinct outputs), fixed with `cv2.setRNGSeed(42)`, verified (5 calls → 1 identical output), regression test added and passing.
2. **`openai` SDK logger not suppressed** (`app/core/logging.py`) — a real, if narrow, secret-exposure risk at this app's `debug=True` default. Fixed by adding `logging.getLogger("openai").setLevel(logging.WARNING)`, matching the existing `anthropic` pattern. Regression test added and passing.
3. **Pre-existing test-fixture pollution in `test_similarity.py`** (not a Phase 16 regression, but root-caused and durably fixed this phase after the previous, Phase-13-era "distinctive color" patch itself failed again under further corpus growth): the two `TestPrivacy` tests used a **hardcoded** fixture color, which — because Phase 11's content-hash embedding dedup is global and permanent — meant every previous local regression run of the same test silently left behind another analysis row sharing the same vector. Direct measurement found **52 separate analyses** sharing one `vector_id` from this accumulation. With the API's `k` hard-capped at 20 (an intentional, documented ceiling), a specific pair created by any one test run could be arbitrarily crowded out of the top-20 by up to 51 *other* historical ties at the exact same perfect similarity score. **Fixed durably**: the two uploads within one test run now use byte-identical content (guaranteeing a perfect, unbeatable 1.0 similarity score via the same dedup mechanism) *and* a fresh, `uuid4`-derived color generated fresh on every run (guaranteeing this run's fixture can never collide with any past or future run's). Verified: both tests pass repeatably.

No unrelated pre-existing issues were silently modified — anything not listed above was left untouched.

---

## 23. Frontend Verification

No frontend code was changed this phase (validation/hardening was backend-and-ML-scoped per the phase's own instructions). Re-confirmed via the existing suite: 193/193 tests passing, ESLint clean, `next build` clean, matching the state already verified at the end of Phase 15.

---

## 24. Known Limitations (restated plainly, nothing hidden)

- No cat/non-cat detection gate exists — see §7. This is the single most important limitation in this report.
- 4.4% of test-set predictions were confidently (≥80%) wrong — see §6.
- No live Anthropic or OpenAI call has ever been made in this development environment — both remain `NOT VERIFIED LIVE`.
- No formal similarity retrieval benchmark exists (no labeled ground-truth dataset for "these two photos are the same cat" was available).
- Fur color remains a visual estimation, not a colorimetric measurement.
- The breed classifier's scope is fixed at the 12 Oxford-IIIT Pet cat breeds — any other breed or mixed-breed cat will be forced into the nearest of these 12.
- "Multiple cats in one frame" and extreme close-up/far-away framing were not tested — no real photo meeting those descriptions was available in this environment.
- A formal Expected Calibration Error was not computed (judged not to add proportionate value at n=360; the bucket table and explicit high-confidence-wrong count already surface the relevant risk).

---

## 25. Technical Debt

- A future, properly-scoped phase could add a lightweight cat/non-cat gate (see §7's proposal) — genuinely useful, but out of bounds for this validation-only phase.
- The Grad-CAM faithfulness check remains a sanity check (5 photos, one breed, one masking threshold), not a rigorous benchmark — documented since Phase 12, unchanged.
- Single-process-instance limitations (breed classifier, embedding model, FAISS index, in-memory rate limiter) remain unchanged from every prior phase's documentation.

---

## Portfolio-Quality Technical Summary

**What MeowVerse can honestly claim:**

**VERIFIED:**
- A real transfer-learning breed classifier (MobileNetV3-Small, ImageNet-pretrained, fine-tuned on the Oxford-IIIT Pet cat breeds), evaluated on a genuine held-out test set with a directly-verified zero-leakage split: 87.5% top-1 / 98.6% top-3 accuracy.
- Real, from-scratch Grad-CAM explainability against the classifier's actual gradients.
- A real FAISS-backed visual similarity engine with mathematically-verified correctness (identical/orthogonal/opposite/ranked vector tests) and measured live latency.
- A deterministic, reproducible, rule-based personality scoring engine with a structurally-enforced separation between computed signals, deterministic scores, and optional creative LLM text.
- Structured LLM output generation (forced tool use, schema validation, retry logic) with a real, tested, honestly-labeled offline fallback.
- A production-style provider-abstraction/fallback architecture across every external AI dependency (Anthropic, OpenAI) — never a crash, never a fabricated result, when a provider is unavailable.
- A real, run-this-phase confidence-calibration analysis that surfaces (rather than hides) a genuine 4.4% high-confidence-wrong rate.
- A real, found-and-fixed non-determinism bug in the fur-color pipeline, with a regression test now guarding against recurrence.

**PARTIALLY VERIFIED:**
- Non-cat robustness: the failure mode is real, measured, and documented — but no mitigation (cat/non-cat gate) has been built yet.

**NOT VERIFIED:**
- Live Anthropic story/personality generation — no API key configured in this environment.
- Live OpenAI `gpt-image-1` portrait generation — no API key configured in this environment.
- A formal similarity retrieval benchmark against labeled ground truth — no such dataset exists.
