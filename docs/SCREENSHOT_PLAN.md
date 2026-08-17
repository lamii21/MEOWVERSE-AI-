# MeowVerse — Screenshot Plan

10 screenshots, prioritized. Capture at desktop width (≥1440px) unless
noted; use a real, appealing cat photo throughout for consistency
(same cat across shots 2–7 tells a coherent story). Light mode
recommended for README embedding (renders consistently regardless of
GitHub's theme), but capture dark mode too if time allows — the design
system supports both.

---

### 1. Hero / Landing Page
- **Screen:** `/` (landing page)
- **What should be visible:** the hero section, mascot, tagline,
  "how it works" section if it fits above the fold
- **Why it matters:** first impression — sets the tone (playful but
  technical) in the first 2 seconds
- **Readable text:** the main headline/tagline
- **Aspect ratio:** 16:9 (standard hero banner, works in README + LinkedIn)

### 2. Cat Analysis Result — Cat Card
- **Screen:** `/analyze` after a real analysis completes
- **What should be visible:** the full Cat Card — photo, breed, "Model
  confidence" meter, fur palette, rarity badge, magic power
- **Why it matters:** the core product moment — proves the real CV
  output, not just a form
- **Readable text:** breed name, confidence percentage, "Real
  prediction" badge
- **Aspect ratio:** 4:5 or 1:1 (card-shaped, matches the product's own layout)

### 3. Grad-CAM Explanation
- **Screen:** the "Why this breed?" panel after clicking it on an
  analyzed cat
- **What should be visible:** the Original / AI Focus / Overlay
  switcher, ideally on the Overlay view showing the heatmap on the cat
- **Why it matters:** this is the single most differentiating
  technical feature for an ML-literate viewer — most portfolio
  projects don't have this
- **Readable text:** the "interpretability visualization" disclaimer
  text, confidence value
- **Aspect ratio:** 1:1 or 4:3

### 4. Similar Cats
- **Screen:** the "Cats Like This 🐾" section on an analyzed cat or
  public cat page
- **What should be visible:** at least 3 similar-cat result cards with
  real "N% visually similar" scores
- **Why it matters:** demonstrates the FAISS similarity engine
  concretely, not just as a claim
- **Readable text:** the similarity percentage on at least one result
- **Aspect ratio:** 16:9 (wide row of cards)

### 5. Personality Card
- **Screen:** the Cat Personality section
- **What should be visible:** the archetype header (e.g. "🌙 Dreamy
  Explorer"), the 8 trait bars, and the honesty disclaimer text
- **Why it matters:** shows the deterministic-scores-vs-AI-text
  separation visually (two distinct sections on the card)
- **Readable text:** the archetype name, at least 2-3 trait labels,
  the disclaimer
- **Aspect ratio:** 4:5

### 6. AI Story
- **Screen:** the Story section after generation, mid-reveal or fully
  revealed
- **What should be visible:** the story title, opening paragraph, and
  the style selector showing the 5 available styles
- **Why it matters:** shows the generative-AI text feature and its
  honest mode badge
- **Readable text:** story title, first line or two, the mode badge
  ("AI-generated" or "Offline demo content")
- **Aspect ratio:** 4:5 or 1:1

### 7. Portrait Studio
- **Screen:** `/portrait/[id]` or the Portrait Studio section
- **What should be visible:** the style grid (showing several of the
  10 styles) and, if a real generation is available, a before/after
  comparison; otherwise the honest "unavailable" state is also a valid
  (and honest) shot
- **Why it matters:** shows image-conditioned generative AI, the most
  visually striking feature
- **Readable text:** style names, the "AI-generated artwork" label
- **Aspect ratio:** 1:1 (portrait-style, matches generated image
  aspect ratio)

### 8. Collection — "My Cat Universe"
- **Screen:** `/collection`
- **What should be visible:** the stats summary row (total/favorites/
  stories/completion%), the XP/level bar, and a populated grid of
  saved cats with rarity badges
- **Why it matters:** shows the gamification/progression system and
  that the product has real persistent state, not just a one-shot demo
- **Readable text:** the stat numbers, level indicator
- **Aspect ratio:** 16:9

### 9. Explore — Cat Universe
- **Screen:** `/explore`
- **What should be visible:** the search/filter bar, Featured Cats
  section, and a populated grid of public cats
- **Why it matters:** shows the social-discovery layer and that there's
  real accumulated public data, not an empty shell
- **Readable text:** filter labels, at least one cat's name/breed
- **Aspect ratio:** 16:9

### 10. Architecture / Technical View
- **Screen:** not a product screen — a rendered view of the Mermaid
  system-architecture diagram from README.md or
  docs/ARCHITECTURE_DIAGRAM.md (screenshot the rendered diagram from
  GitHub's own Markdown preview, or export it via the Mermaid Live
  Editor)
- **Why it matters:** gives technical reviewers (engineering managers,
  ML engineers) an immediate, legible system overview without reading
  prose
- **Readable text:** all box labels in the diagram
- **Aspect ratio:** 16:9 or wider (diagrams need horizontal space)

---

## Capture checklist

- [ ] Use one consistent, appealing cat photo for shots 2–7 (tells a
      coherent "this one cat's journey" story)
- [ ] Hide/blur any real email addresses or personal account details
      visible in nav bars before capturing
- [ ] Capture at a resolution that stays legible when scaled down to
      README width (~800px)
- [ ] Prefer light mode for README embeds (renders consistently across
      GitHub's light/dark viewer themes); a dark-mode shot is a nice
      bonus, not required
- [ ] Save as PNG (not JPEG — screenshots with text/UI compress better
      losslessly)
