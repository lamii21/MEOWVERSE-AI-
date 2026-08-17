# Multi-stage build. Stage 1 compiles/installs into a venv (needs gcc/
# libpq-dev); stage 2 only copies the finished venv + app code, so the
# final image doesn't carry build tooling or pip's download cache.
#
# ML dependencies (torch/torchvision/opencv/faiss/scikit-learn — see
# requirements-ml.txt) are installed by default, resolving the
# long-standing gap where this image only ever ran the CV pipeline in
# demo mode. Set INSTALL_ML_DEPS=false at build time for a smaller,
# demo-mode-only image (e.g. a quick frontend-focused preview build) —
# pair it with REQUIRE_ML_MODELS=false at runtime, which is already the
# default.
FROM python:3.13-slim AS builder

ARG INSTALL_ML_DEPS=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt requirements-ml.txt ./
# A real bug found by actually building this image (not assumed): a
# plain `pip install torch==2.7.1` on Linux resolves PyPI's default
# CUDA-bundled wheel (pulls in ~10 nvidia-cu12 packages, pushing the
# install past 500s and several extra GB) — not the CPU-only build
# requirements-ml.txt's own comment says was chosen. That assumption
# held on Windows (this project's dev machine) but not in this Linux
# container. Installing torch/torchvision from PyTorch's own CPU wheel
# index *first* fixes it: `pip install -r requirements-ml.txt` below
# then finds them already satisfied at the exact pinned version and
# installs everything else (opencv/faiss/scikit-learn/grad-cam) from
# regular PyPI as normal.
#
# Second and third real bugs found by actually *running* this image,
# not just building it. (2) `grad-cam` transitively depends on plain
# `opencv-python` (the GUI-capable build) in addition to the
# `opencv-python-headless` requirements-ml.txt asks for directly —
# both packages install the same importable `cv2`, so whichever
# installs *last* wins on disk. Here that was the GUI build, and
# `import cv2` failed at container startup with `libxcb.so.1: cannot
# open shared object file` — this slim runtime deliberately has no X11
# libs. (3) A first fix attempt (`pip uninstall -y opencv-python`)
# made the crash *worse*, not better: `import cv2` started succeeding
# again, but `cv2.cvtColor` (and other real functionality) was gone,
# because opencv-python's install had overwritten some of
# opencv-python-headless's own compiled files, and uninstalling
# opencv-python only removes files *it* owns — it doesn't restore what
# it clobbered. The actual fix is a forced, dependency-free reinstall
# of the headless build, which overwrites every file it owns with its
# own correct versions regardless of what pip's resolver did before —
# confirmed working via a real upload against the running container,
# not just an import check.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_ML_DEPS" = "true" ]; then \
         pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 \
           --index-url https://download.pytorch.org/whl/cpu \
         && pip install --no-cache-dir -r requirements-ml.txt \
         && pip install --no-cache-dir --force-reinstall --no-deps \
              opencv-python-headless==4.12.0.88; \
       fi


FROM python:3.13-slim AS runtime

WORKDIR /app

# libpq5 (runtime half of libpq-dev, for psycopg2/asyncpg) + the shared
# libs opencv-python-headless still dlopen's for common image codecs
# even in its "headless" build (no GUI/X11 libs needed, unlike the
# non-headless `opencv-python` package).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

# A non-root user — the container writes nothing under /app itself in
# production (uploads/similarity index are volumes or object storage,
# not baked into the image path), so this has no functional downside.
RUN useradd --create-home --uid 1000 meowverse \
    && chown -R meowverse:meowverse /app
USER meowverse

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
