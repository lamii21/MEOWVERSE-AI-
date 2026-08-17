# MeowVerse — ML Pipeline

Every stage below is labeled with exactly what it is: **TRAINED**
(a real model with learned weights), **DETERMINISTIC** (a fixed
algorithm/formula, no learning, no randomness), **LLM-GENERATED**
(produced by a generative-AI provider when configured), or **DEMO
FALLBACK** (a deterministic, clearly-labeled placeholder used when a
provider/model isn't available). These categories are never blurred
together in the product UI or the API response — see
[AI_VALIDATION_REPORT.md](../AI_VALIDATION_REPORT.md) for the full,
independently-measured validation of every stage.

```
                          INPUT IMAGE
                               │
                               ▼
                     ┌───────────────────┐
                     │   Preprocessing    │  DETERMINISTIC
                     │ decode·validate·   │  (format/size/dimension
                     │   resize·normalize │   checks, no learning)
                     └─────────┬─────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
    ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
    │Breed Classification│ │Fur Color     │ │Visual Embedding   │
    │MobileNetV3-Small   │ │Analysis      │ │MobileNetV3-Small   │
    │(fine-tuned)         │ │GrabCut+KMeans│ │(ImageNet weights,  │
    │                     │ │              │ │NOT fine-tuned)     │
    │      TRAINED        │ │DETERMINISTIC │ │      TRAINED        │
    └──────────┬──────────┘ └──────┬───────┘ └─────────┬──────────┘
               │                   │                   │
               │                   │                   ▼
               │                   │         ┌───────────────────┐
               │                   │         │FAISS Similarity    │
               │                   │         │Search (cosine, exact)│
               │                   │         │   DETERMINISTIC      │
               │                   │         └───────────────────┘
               ▼                   │
    ┌──────────────────┐           │
    │Grad-CAM Explanation│          │
    │(on-demand only)     │         │
    │      TRAINED*        │        │
    │ *uses trained model's│        │
    │  real gradients       │       │
    └──────────┬──────────┘        │
               │                    │
               └─────────┬──────────┘
                         ▼
              ┌───────────────────────┐
              │  Personality Scoring    │  DETERMINISTIC
              │  8 traits, fixed formula│  (zero ML, zero LLM,
              │  over breed+color signals│  zero randomness)
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   LLM Interpretation     │
              │ (archetype narrative,     │  LLM-GENERATED
              │  story, profile flavor)   │  when ANTHROPIC_API_KEY
              │                            │  is configured
              │  → DEMO FALLBACK otherwise │  DEMO FALLBACK
              └───────────┬───────────────┘  when it isn't
                          │
                          ▼
              ┌───────────────────────┐
              │   Image Generation        │  LLM-GENERATED
              │ (AI Portrait, image-       │  (image-conditioned,
              │  conditioned on real photo)│  OpenAI gpt-image-1)
              │  → DEMO FALLBACK otherwise │  DEMO FALLBACK
              └───────────┬───────────────┘  when not configured
                          │
                          ▼
              ┌───────────────────────┐
              │   Cat Profile / Story /   │
              │   Portrait / Personality  │
              └───────────────────────┘
```

## Stage-by-stage

### 1. Preprocessing — DETERMINISTIC
Decode → verify the file is a genuine, decodable image (Pillow
`.verify()` + a real re-open, catching `UnidentifiedImageError`,
`OSError`, and Pillow's own `DecompressionBombError`) → enforce a
minimum (64px) and maximum (8000px) dimension → resize/normalize for
each model's specific input contract. No learned parameters anywhere
in this stage.

### 2. Breed Classification — TRAINED
MobileNetV3-Small, ImageNet-pretrained, fully fine-tuned on the
Oxford-IIIT Pet dataset's 12 cat breeds. Real gradient-descent
training (AdamW, cosine LR schedule, 15 epochs), not a lookup table.
`Resize(256) → CenterCrop(224) → ToTensor → Normalize(ImageNet
mean/std)` — verified byte-identical between the production inference
code and the training/evaluation code, so what the model was
evaluated on is what it actually runs on. 87.5% top-1 / 98.6% top-3
accuracy on a genuine held-out test set (360 images, never seen during
training). If the trained weights or `torch`/`torchvision` aren't
available, this stage falls back to a deterministic **DEMO FALLBACK**
(a fixed pool of results, selected by the hash of the image bytes so
the same photo always gets the same demo result) — never silently
presented as a real prediction.

### 3. Fur Color Analysis — DETERMINISTIC
OpenCV GrabCut foreground segmentation (excludes background before
clustering, RNG-seeded via `cv2.setRNGSeed(42)` for determinism) →
scikit-learn K-means (`k=3`, `random_state=42`) on the foreground
pixels → each cluster centroid mapped to the nearest name in a small,
fur-relevant reference palette via RGB nearest-neighbor. No trained
weights — the "model" here is a fixed algorithm with a fixed seed.
Explicitly documented as a *visual estimation*, not a colorimetrically
calibrated color measurement.

### 4. Visual Embedding — TRAINED (but a different model)
A **second**, separately-loaded MobileNetV3-Small — the stock
ImageNet-pretrained weights, deliberately *not* the fine-tuned breed
classifier. Reusing the breed classifier's features would make
"visually similar" collapse into "same predicted breed"; a
general-purpose, non-breed-fine-tuned backbone captures how a photo
actually *looks* instead. Produces a 576-dim feature vector,
L2-normalized.

### 5. FAISS Similarity Search — DETERMINISTIC (exact, not approximate)
`IndexFlatIP` — exact cosine similarity via inner product on
normalized vectors, not an approximate-nearest-neighbor index. No
learned parameters; correctness verified with controlled mathematical
tests (identical vectors → 1.0, orthogonal → 0.0, opposite →
negative, closer-ranks-above-farther). SQL-level privacy filtering
(never fetch-then-check) happens before any candidate reaches a
response.

### 6. Grad-CAM Explanation — uses the TRAINED model's real gradients
Computed on-demand only (never automatically during analysis), from
scratch with PyTorch forward/backward hooks against the breed
classifier's actual weights and the specific predicted class's score.
Target layer (`features[-1]`, producing a `(576,7,7)` feature map)
verified empirically. Described everywhere as *"a visual explanation
of regions contributing to the prediction,"* never as proof or a
causal claim about the cat's actual breed. If the underlying analysis
was made in demo mode, Grad-CAM says so plainly rather than
fabricating a heatmap.

### 7. Personality Scoring — DETERMINISTIC
`score = clamp(round(50 + confidence_scale × (breed_offset +
color_offset + entropy_offset)), 0, 100)` — a documented formula over
8 traits (curiosity, playfulness, calmness, cuddliness, confidence,
mischief, elegance, adventurousness), computed from the real
breed/color signals above. Zero ML model, zero LLM, zero
`random`/`np.random` import anywhere in the module (verified by a
dedicated test that inspects the function signature). The archetype
(e.g. "🌙 Dreamy Explorer") is chosen deterministically via
nearest-centroid distance over those same 8 scores — never
LLM-chosen, never random.

### 8. LLM Interpretation — LLM-GENERATED or DEMO FALLBACK
Anthropic Claude, used only for creative *text*: the personality
archetype's narrative flavor text, and full cat stories (5 selectable
styles). **Forced tool use** — the tool's `input_schema` is generated
directly from the Pydantic response schema, so the model cannot return
anything but that exact shape, and that shape has no fields for trait
scores, breed, or color. One semantic retry on invalid schema; no
unbounded retry loop. Falls back to a deterministic, hand-written,
clearly-labeled offline variant (`"_mode": "demo"`) when no
`ANTHROPIC_API_KEY` is configured or a live call fails — **this
fallback path is what's actually verified in this development
environment**; live generation has not been tested here (no key
configured).

### 9. Image Generation — LLM-GENERATED or DEMO FALLBACK
OpenAI `gpt-image-1`, image-conditioned: the cat's real uploaded photo
is attached as the primary identity reference alongside a
backend-only-assembled prompt (breed, colors, chosen style,
personality-driven atmosphere) — not a text-only "a British Shorthair
cat" prompt, which would just generate a generic cat of that breed.
User-supplied customization text is sanitized and structurally
confined to its own prompt section, unable to override
identity-preservation rules. Falls back to an honest "Portrait
generation is currently unavailable" state — never a fake or
placeholder image — when no provider is configured. **Not verified
live** in this development environment; the honest-unavailable path
is.

## The three-way honesty rule

Every AI output in MeowVerse's API responses and UI is one of exactly
three things, and the product never lets them blur together:

1. **REAL MODEL OUTPUT** — breed prediction, fur-color clusters,
   Grad-CAM heatmaps, visual embeddings/similarity scores, personality
   trait scores. Reproducible; the same photo always produces the same
   result.
2. **AI-GENERATED CREATIVE CONTENT** — LLM-written narrative text or
   AI-generated portrait artwork, conditioned on the real signals
   above, always labeled as generated (e.g. "AI-generated artwork"),
   never treated as a measurement.
3. **DEMO FALLBACK** — a deterministic, hand-written placeholder shown
   when a provider/model isn't available, explicitly labeled
   `"_mode": "demo"` in the API and "Offline demo content" in the UI.
