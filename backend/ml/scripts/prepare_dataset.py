"""Download the Oxford-IIIT Pet dataset and prepare a cat-only breed
classification split.

Source: https://www.robots.ox.ac.uk/~vgg/data/pets/
License: Creative Commons Attribution-ShareAlike 4.0 International
         (CC BY-SA 4.0) — both images and annotations. See
         ml/dataset/DATASET_LICENSE.md for the full notice.

The dataset contains 37 breeds (12 cat, 25 dog) split by the original
authors into "trainval" and "test". MeowVerse only classifies cats and
does its own train/val/test split, so this script combines both
official splits into one pool, filters to cat images using the
dataset's own binary cat/dog label (not breed-name casing — this
torchvision version Title-Cases every class name, so e.g. dog breed
"boxer" becomes "Boxer" and a casing heuristic would misclassify it),
and writes an ImageFolder-compatible directory structure:

    ml/dataset/processed/{train,val,test}/{breed_name}/*.jpg

Usage (from backend/, with the venv active):
    python -m ml.scripts.prepare_dataset
"""

import json
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from torchvision.datasets import OxfordIIITPet

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "dataset"
RAW_DIR = DATASET_DIR / "raw"
PROCESSED_DIR = DATASET_DIR / "processed"

SPLIT_RATIOS = {"train": 0.7, "val": 0.15, "test": 0.15}
SEED = 42
CAT_BIN_LABEL = 0  # dataset.bin_classes == ["Cat", "Dog"]


def main() -> None:
    random.seed(SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Oxford-IIIT Pet dataset to {RAW_DIR} (skipped if cached)...")
    trainval = OxfordIIITPet(root=str(RAW_DIR), split="trainval", download=True)
    test = OxfordIIITPet(root=str(RAW_DIR), split="test", download=True)
    assert trainval.classes == test.classes, "trainval/test class ordering mismatch"
    classes = trainval.classes

    all_images = list(trainval._images) + list(test._images)
    all_labels = list(trainval._labels) + list(test._labels)
    all_bin_labels = list(trainval._bin_labels) + list(test._bin_labels)
    print(f"Combined pool: {len(all_images)} images across both official splits.")

    cat_label_indices = {
        label for label, bin_label in zip(all_labels, all_bin_labels, strict=True)
        if bin_label == CAT_BIN_LABEL
    }
    cat_breeds = sorted(classes[i] for i in cat_label_indices)
    print(f"Found {len(classes)} total breeds, {len(cat_breeds)} are cats:")
    for breed in cat_breeds:
        print(f"  - {breed}")

    images_by_breed: dict[str, list[Path]] = {breed: [] for breed in cat_breeds}
    per_image = zip(all_images, all_labels, all_bin_labels, strict=True)
    for image_path, label_idx, bin_label in per_image:
        if bin_label == CAT_BIN_LABEL:
            images_by_breed[classes[label_idx]].append(Path(image_path))

    if PROCESSED_DIR.exists():
        shutil.rmtree(PROCESSED_DIR)

    split_counts = {split: 0 for split in SPLIT_RATIOS}
    class_distribution: dict[str, dict[str, int]] = {}
    for breed, paths in images_by_breed.items():
        random.shuffle(paths)
        n = len(paths)
        n_train = int(n * SPLIT_RATIOS["train"])
        n_val = int(n * SPLIT_RATIOS["val"])
        splits = {
            "train": paths[:n_train],
            "val": paths[n_train : n_train + n_val],
            "test": paths[n_train + n_val :],
        }
        class_distribution[breed] = {split: len(p) for split, p in splits.items()}
        for split, split_paths in splits.items():
            out_dir = PROCESSED_DIR / split / breed
            out_dir.mkdir(parents=True, exist_ok=True)
            for src in split_paths:
                shutil.copy2(src, out_dir / src.name)
            split_counts[split] += len(split_paths)

    info = {
        "source": "https://www.robots.ox.ac.uk/~vgg/data/pets/",
        "license": "CC BY-SA 4.0",
        "classes": cat_breeds,
        "num_classes": len(cat_breeds),
        "total_images": sum(split_counts.values()),
        "split_ratios": SPLIT_RATIOS,
        "split_counts": split_counts,
        "class_distribution": class_distribution,
        "seed": SEED,
        "prepared_at": datetime.now(UTC).isoformat(),
    }
    (PROCESSED_DIR / "dataset_info.json").write_text(json.dumps(info, indent=2))

    print(f"\nDone. Split counts: {split_counts}")
    print(f"Wrote {PROCESSED_DIR / 'dataset_info.json'}")


if __name__ == "__main__":
    main()
