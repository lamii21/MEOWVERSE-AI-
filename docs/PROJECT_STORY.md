# MeowVerse — The Project Story

I initially wanted to build a simple cat recognition project after
learning deep learning. Upload a photo, get a breed name back — a
weekend project to practice fine-tuning a CNN on a real dataset.

It didn't stay simple, and looking back at how it grew, the shape of
that growth says more about how I actually work than the finished
product does.

## It started as computer vision

The first real milestone was a fine-tuned MobileNetV3-Small on the
Oxford-IIIT Pet dataset, predicting one of 12 cat breeds. That part
worked the way tutorials promise it will — transfer learning,
reasonable accuracy, done. But a bare accuracy number felt thin. If
someone asked "why did it predict that breed," I didn't have an answer
better than "the model said so." That bothered me more than I
expected it to.

## → explainability

So I implemented Grad-CAM from scratch — not because a library wasn't
available (`pytorch-grad-cam` was already sitting in
`requirements-ml.txt`), but because I wanted to actually understand
every step: the forward pass, the gradient capture, the feature
weighting, the ReLU, the normalization. Writing it myself meant I
could write a real test for it too — "does a different target class
produce a genuinely different heatmap" — instead of trusting a
black-box call. That test caught real bugs during development that a
"looks right in a screenshot" check wouldn't have.

## → similarity

Once I had a breed classifier, the obvious next question was "what
*else* can a photo's visual features tell you?" — not just the breed
label, but genuine visual similarity between two cats regardless of
breed. That meant a second embedding model (deliberately not reusing
the fine-tuned classifier, so similarity wouldn't just collapse into
"same predicted breed"), a FAISS index, and — because I'd already
learned from the Grad-CAM test that "looks right" isn't the same as
"is right" — a set of controlled mathematical tests for the similarity
math itself, not just the HTTP layer around it.

## → generative AI

Real predictions and real explanations felt complete on the analytical
side, but a bit cold. I wanted the product to feel *alive* — a
personality, a story, art. That's where generative AI came in, and
it's also where I got most protective of the "real vs. generated"
distinction that had built up naturally through the CV work. I didn't
want an LLM anywhere near the actual model output. So the personality
engine became two layers: a deterministic, documented scoring formula
computing real trait numbers from real signals, and a *separate*,
optional LLM layer that writes flavor text — enforced by giving the
LLM's response schema literally no field to put a trait score in. Not
a prompt asking it to behave; a schema making misbehavior structurally
impossible.

## → personality

The personality engine became the clearest expression of a principle I
kept returning to throughout the project: never let a claim be looser
than what actually backs it. "AI-inspired curiosity: 69," never "your
cat is 69% curious." A cat's real personality genuinely cannot be
determined from a photo, and the product says so, explicitly, on every
personality card.

## → social discovery

Once cats had real analyses, real explanations, real personalities,
and real stories, it felt natural that people would want to show them
off — but I was wary of "social feature creep." The explicit rule
became: this is discovery, not a social network. No comments, no DMs,
no follower system, no public likes. Just search, filter, and a
deterministic "Featured Cats" formula (never a random pick that
reshuffles for no reason).

## → gamification

XP, levels, and achievements came from wanting saving and sharing cats
to feel like *progress*, not just storage. The constraint I held
myself to: every number has to be real. No client-trusted XP values,
no invented "collection completion" denominator — it's your discovered
breeds divided by the actual, fixed 12-breed universe the classifier
recognizes, nothing more.

## → production engineering

The last phase was the least glamorous and probably the most
professionally important: making sure everything above actually works
the way it claims to, under conditions closer to production than a
laptop's dev server. This is where I found out the backend's Docker
image had quietly been running the entire CV pipeline in demo mode
since early development — a gap that had been invisible because
nothing ever actually tested the container, only the code inside it in
isolation. Fixing that surfaced two more bugs (a CUDA wheel silently
bloating the image, an OpenCV package conflict that broke `cv2` in a
way that only showed up at runtime, not at build time) that taught me
something I'll carry into every future project: a green `docker build`
proves the image compiled, not that it works. I only found both bugs
because I insisted on actually running the container and uploading a
real photo to it.

## What this shows, I think

Curiosity — each phase came from an honest "but what about..." rather
than a plan drawn up in advance. Iteration — the personality engine's
three-layer separation, the similarity engine's dedicated math tests,
and the Docker hardening pass all came from earlier mistakes or
half-answers I wasn't satisfied with. And a growing insistence, the
further the project went, on being able to defend every claim the
product makes about itself — which is why the validation report says
"NOT VERIFIED" in the places where something genuinely wasn't tested,
instead of rounding up.
