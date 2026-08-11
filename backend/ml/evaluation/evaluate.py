"""Evaluate the trained breed classifier on the held-out test split.

Computes accuracy, macro precision/recall/F1, per-class report, and a
confusion matrix. Writes ml/evaluation/evaluation_report.json.

Usage (from backend/, with the venv active):
    python -m ml.evaluation.evaluate
"""

import json
from pathlib import Path

import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from ml.training.train_breed_classifier import (
    MODEL_NAME,
    PROCESSED_DIR,
    build_model,
    build_transforms,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
MODELS_DIR = ML_DIR / "models"


def main() -> None:
    weights_path = MODELS_DIR / f"{MODEL_NAME}.pt"
    class_names_path = MODELS_DIR / "class_names.json"
    if not weights_path.exists():
        raise SystemExit(f"{weights_path} not found — run training first.")

    class_names = json.loads(class_names_path.read_text())
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _, eval_tf = build_transforms()
    test_ds = ImageFolder(PROCESSED_DIR / "test", transform=eval_tf)
    assert test_ds.classes == class_names, "test set classes don't match trained model"
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=2)

    model = build_model(len(class_names))
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.to(device).eval()

    all_preds, all_labels = [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            preds = model(images).argmax(dim=1).cpu()
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.tolist())

    report = classification_report(
        all_labels, all_preds, target_names=class_names, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(all_labels, all_preds).tolist()

    result = {
        "model_name": MODEL_NAME,
        "test_set_size": len(test_ds),
        "classes": class_names,
        "accuracy": report["accuracy"],
        "macro_avg": report["macro avg"],
        "weighted_avg": report["weighted avg"],
        "per_class": {name: report[name] for name in class_names},
        "confusion_matrix": cm,
    }

    out_path = SCRIPT_DIR / "evaluation_report.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"Accuracy: {report['accuracy']:.4f}")
    print(f"Macro F1: {report['macro avg']['f1-score']:.4f}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
