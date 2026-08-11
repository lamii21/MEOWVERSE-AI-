# MeowVerse AI — ML Pipeline

Cat breed classification via transfer learning. See
`DATASET_LICENSE.md` for dataset source/license.

## Setup

From `backend/`, with the project's `.venv` active:

```bash
pip install -r requirements-ml.txt --extra-index-url https://download.pytorch.org/whl/cu118
```

CPU-only machines can drop the `--extra-index-url` and let pip resolve
plain-PyPI CPU wheels instead — training will be slower but inference
(what the API actually uses at request time) is fine on CPU.

## Run the full pipeline

```bash
python -m ml.scripts.prepare_dataset
python -m ml.training.train_breed_classifier
python -m ml.evaluation.evaluate
```

1. **`prepare_dataset`** downloads the Oxford-IIIT Pet dataset (~800MB,
   cached after first run) and writes an ImageFolder-compatible
   train/val/test split of the 12 cat breeds to
   `ml/dataset/processed/`.
2. **`train_breed_classifier`** fine-tunes an ImageNet-pretrained
   MobileNetV3-Small on that split. Writes:
   - `ml/models/breed_classifier.pt` — best-val-accuracy weights
   - `ml/models/class_names.json` — ordered class list matching the
     model's output indices
   - `ml/models/model_card.json` — architecture, dataset version,
     training params, per-epoch history, final metrics, timestamp
3. **`evaluate`** runs the saved best checkpoint against the held-out
   test split and writes `ml/evaluation/evaluation_report.json`
   (accuracy, macro/weighted precision/recall/F1, per-class report,
   confusion matrix).

## Backend integration

`app/ml/breed_classifier.py` loads `breed_classifier.pt` +
`class_names.json` lazily on first use (see `get_breed_classifier()`
in that file). If either file is missing — or `torch`/`torchvision`
aren't installed at all — `is_available` is `False` and
`app/services/analysis_service.py` falls back to a clearly-labeled
demo result (`breed_mode: "demo"`) instead of failing. Nothing needs
to change in the API layer to go from demo to trained: run the
pipeline above, restart the backend, and real predictions
(`breed_mode: "trained"`) start flowing automatically.

Weight files and processed/raw dataset images are gitignored (large
binaries); `model_card.json` and `evaluation_report.json` are small
JSON and are tracked, so real metrics are visible in the repo without
needing to retrain.

## Fur color analysis (no training needed)

`app/ml/fur_color.py` (`FurColorAnalyzer`) needs no weights or dataset
— it's classical CV (OpenCV GrabCut + scikit-learn K-means), real as
soon as `requirements-ml.txt` is installed. `is_available` is `False`
only if opencv/numpy/scikit-learn aren't importable at all.
