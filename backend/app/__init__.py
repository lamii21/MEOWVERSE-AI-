import os

# torch and faiss-cpu each bundle their own copy of Intel's OpenMP
# runtime (MKL) on Windows; loading both in the same process aborts
# the interpreter outright ("OMP: Error #15") unless this is set
# *before* either is imported for the first time. This is the
# standard, documented workaround for that specific conflict (not a
# generic "ignore all errors" flag) — found via a real crash while
# building Phase 11's visual similarity feature (test_vector_index.py
# imports faiss, then test_embedding_model.py imports torch in the
# same pytest process → Fatal Python error: Aborted).
#
# Set here, in the package's own `__init__.py`, because it's the one
# place guaranteed to execute before *any* `app.*` submodule — the
# production app (`app.main`), every test (`tests/conftest.py` imports
# `app.main`), and the CLI (`python -m app.cli.similarity_index`) all
# trigger this file first, so there's no import-order race to get
# wrong at any of those three entry points.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
