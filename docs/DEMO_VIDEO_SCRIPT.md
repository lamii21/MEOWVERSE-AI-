# MeowVerse — Demo Video Script

A 90-second walkthrough. Screen recording + voiceover, cuts on beat.
Use one real, appealing cat photo throughout so the demo tells one
coherent story. Record at 1080p minimum; export a square/vertical crop
separately if posting to LinkedIn/Instagram alongside the 16:9 YouTube
cut.

| Time | Screen Action | Voiceover | Text Overlay | Transition |
|---|---|---|---|---|
| **0:00–0:05** | Landing page hero, mascot animation | *"This is MeowVerse — an explainable AI platform for cats."* | **MeowVerse** | Hard cut in |
| **0:05–0:15** | Drag-and-drop a cat photo on `/discover`, click "Discover My Cat" | *"Upload a photo, and it runs through a real computer-vision pipeline — not a lookup table."* | `Real CV pipeline` | Cross-fade to loading state |
| **0:15–0:25** | Cat Card reveals: breed name, confidence meter, fur palette | *"A fine-tuned model predicts the breed — 87.5% accuracy on a held-out test set — and analyzes fur color with real segmentation and clustering."* | `87.5% top-1 accuracy` | Quick cut |
| **0:25–0:35** | Click "Why this breed?" → Grad-CAM overlay appears | *"And it shows its work: this is Grad-CAM, implemented from scratch, highlighting exactly what the model looked at."* | `Grad-CAM · from scratch` | Cross-fade |
| **0:35–0:45** | Scroll to "Cats Like This" section, similarity scores visible | *"A visual embedding search finds real similar-looking cats — powered by FAISS, with a real cosine-similarity score, not a random pick."* | `FAISS · exact similarity` | Cut |
| **0:45–0:55** | Personality card reveal — archetype + trait bars | *"A deterministic personality engine scores 8 traits from the real signals above — no LLM, no randomness — plus an optional AI-written narrative that can't touch those numbers."* | `Deterministic · AI-inspired` | Cross-fade |
| **0:55–1:05** | Story generation — style picker, story reveals | *"Pick a style, and a structured LLM call writes a short story — safely, since the model is forced into a schema that can't overwrite any real prediction."* | `Structured generation` | Cut |
| **1:05–1:15** | Portrait Studio — style grid, before/after (or honest "unavailable" state) | *"An AI portrait studio uses the cat's actual photo as identity reference — not a generic prompt."* | `Image-conditioned generation` | Cross-fade |
| **1:15–1:25** | Collection page → Explore page, quick scroll through both | *"Save it to a real, persistent collection with XP and achievements, or share it into a privacy-first public discovery space."* | `Gamification · Privacy-first` | Cut |
| **1:25–1:30** | Back to landing / logo card | *"MeowVerse. Built end-to-end, tested end-to-end."* | **MeowVerse**<br/>`github.com/[your-repo]` | Fade to black |

---

## Production notes

- **Pacing**: keep every screen action moving — no more than 2 seconds
  of static screen before the next cut, except the Grad-CAM and
  Personality reveals (0:25–0:35, 0:45–0:55), which deserve a beat
  longer since they're the most differentiating moments.
- **Voiceover tone**: confident and technical, not salesy — read the
  script above roughly as written; avoid superlatives ("amazing,"
  "revolutionary") that aren't in this document.
- **Cursor/click visibility**: enable a visible click indicator so
  viewers can follow what triggered each transition (especially the
  "Why this breed?" click and style-picker selections).
- **Audio**: light, non-distracting background music under the
  voiceover, ducked low; no music during any section where UI sound
  effects (if any) should be heard.
- **Captions**: burn in captions matching the voiceover — a large
  fraction of LinkedIn/portfolio viewers watch muted.
- **If a real AI provider key is NOT configured** when recording:
  film the honest "unavailable"/demo-fallback state for story/portrait
  generation rather than faking a result — say so in the voiceover
  ("here's the offline fallback in action") rather than silently
  cutting around it. This is consistent with the project's own
  no-fabrication principle and is a genuinely interesting thing to
  show a technical audience (a system that degrades honestly instead
  of breaking).
- **Ending card**: hold the GitHub URL on screen for at least 2 full
  seconds — most viewers pause here to read/screenshot it.
