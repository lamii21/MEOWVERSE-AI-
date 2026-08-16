"""Phase 16 validation & benchmarking — extends evaluate.py with:
top-1/top-3 accuracy, confidence calibration buckets, a rendered
confusion matrix image, and a real dataset report. Every number here
comes from an actual forward pass over the real held-out test split —
nothing is estimated or invented.

Usage (from backend/, with the venv active):
    python -m ml.evaluation.phase16_validate
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

CONFIDENCE_BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0001)]


def main() -> None:
    weights_path = MODELS_DIR / f"{MODEL_NAME}.pt"
    class_names_path = MODELS_DIR / "class_names.json"
    if not weights_path.exists():
        raise SystemExit(f"{weights_path} not found — run training first.")

    class_names = json.loads(class_names_path.read_text())
    model_card = json.loads((MODELS_DIR / "model_card.json").read_text())
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _, eval_tf = build_transforms()
    test_ds = ImageFolder(PROCESSED_DIR / "test", transform=eval_tf)
    assert test_ds.classes == class_names, "test set classes don't match trained model"
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=2)

    model = build_model(len(class_names))
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.to(device).eval()

    all_top1, all_top3_correct, all_labels, all_confidences = [], [], [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            logits = model(images)
            probs = torch.softmax(logits, dim=1)
            top1 = probs.argmax(dim=1).cpu()
            top3 = probs.topk(3, dim=1).indices.cpu()
            conf = probs.max(dim=1).values.cpu()

            all_top1.extend(top1.tolist())
            all_top3_correct.extend(
                [
                    label in top3_row.tolist()
                    for label, top3_row in zip(labels.tolist(), top3, strict=True)
                ]
            )
            all_labels.extend(labels.tolist())
            all_confidences.extend(conf.tolist())

    top1_correct = [pred == truth for pred, truth in zip(all_top1, all_labels, strict=True)]
    top1_accuracy = sum(top1_correct) / len(top1_correct)
    top3_accuracy = sum(all_top3_correct) / len(all_top3_correct)

    report = classification_report(
        all_labels, all_top1, target_names=class_names, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(all_labels, all_top1)

    # --- Confidence calibration: real accuracy per confidence bucket ---
    calibration = []
    for low, high in CONFIDENCE_BUCKETS:
        indices = [i for i, c in enumerate(all_confidences) if low <= c < high]
        if not indices:
            calibration.append(
                {"range": f"{low:.1f}-{min(high, 1.0):.1f}", "n": 0, "accuracy": None}
            )
            continue
        bucket_correct = sum(top1_correct[i] for i in indices)
        calibration.append(
            {
                "range": f"{low:.1f}-{min(high, 1.0):.1f}",
                "n": len(indices),
                "accuracy": bucket_correct / len(indices),
            }
        )

    # High-confidence-but-wrong cases — the specific failure mode spec
    # §7 asks us to surface, not just compute an aggregate calibration
    # number.
    high_conf_wrong = [
        {
            "true_label": class_names[all_labels[i]],
            "predicted_label": class_names[all_top1[i]],
            "confidence": all_confidences[i],
        }
        for i in range(len(all_labels))
        if all_confidences[i] >= 0.8 and not top1_correct[i]
    ]

    # --- Confusion matrix analysis: strongest/weakest classes, top pairs ---
    per_class_recall = {name: report[name]["recall"] for name in class_names}
    strongest = sorted(per_class_recall.items(), key=lambda kv: kv[1], reverse=True)[:3]
    weakest = sorted(per_class_recall.items(), key=lambda kv: kv[1])[:3]

    confusion_pairs = []
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            if i != j and cm[i, j] > 0:
                confusion_pairs.append(
                    {
                        "true": class_names[i],
                        "predicted": class_names[j],
                        "count": int(cm[i, j]),
                    }
                )
    confusion_pairs.sort(key=lambda p: p["count"], reverse=True)

    # --- Render confusion matrix PNG ---
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Breed Classifier Confusion Matrix (test n={len(test_ds)})")
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            if cm[i, j] > 0:
                ax.text(
                    j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=8,
                )
    fig.colorbar(im, ax=ax, label="count")
    fig.tight_layout()
    png_path = SCRIPT_DIR / "confusion_matrix.png"
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    result = {
        "model_name": MODEL_NAME,
        "model_version": model_card["version"],
        "dataset_version": model_card["dataset_version"],
        "evaluation_date": datetime.now(UTC).isoformat(),
        "test_set_size": len(test_ds),
        "classes": class_names,
        "preprocessing_version": "Resize(256)->CenterCrop(224)->Normalize(ImageNet mean/std)",
        "top1_accuracy": top1_accuracy,
        "top3_accuracy": top3_accuracy,
        "macro_avg": report["macro avg"],
        "weighted_avg": report["weighted avg"],
        "per_class": {name: report[name] for name in class_names},
        "confusion_matrix": cm.tolist(),
        "strongest_classes_by_recall": strongest,
        "weakest_classes_by_recall": weakest,
        "top_confusion_pairs": confusion_pairs[:5],
        "confidence_calibration": calibration,
        "high_confidence_wrong_predictions": high_conf_wrong,
        "high_confidence_wrong_count": len(high_conf_wrong),
        "high_confidence_wrong_rate": len(high_conf_wrong) / len(all_labels),
    }

    out_path = SCRIPT_DIR / "classification_results.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"Top-1 accuracy: {top1_accuracy:.4f}")
    print(f"Top-3 accuracy: {top3_accuracy:.4f}")
    print(f"Macro F1: {report['macro avg']['f1-score']:.4f}")
    print(f"High-confidence-wrong cases (conf>=0.8 but incorrect): {len(high_conf_wrong)}")
    print(f"Strongest classes (recall): {strongest}")
    print(f"Weakest classes (recall): {weakest}")
    print(f"Top confusion pairs: {confusion_pairs[:5]}")
    print(f"Wrote {out_path}")
    print(f"Wrote {png_path}")


if __name__ == "__main__":
    main()
