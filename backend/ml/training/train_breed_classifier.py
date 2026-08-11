"""Train the cat breed classifier via transfer learning.

Backbone: MobileNetV3-Small, pretrained on ImageNet (torchvision).
Chosen for inference speed and small model size over raw accuracy —
appropriate for a synchronous API endpoint with no GPU guaranteed in
production. Only the classifier head is trained from scratch; the
backbone is fine-tuned at a lower learning rate.

Usage (from backend/, with the venv active):
    python -m ml.training.train_breed_classifier [--epochs 15] [--batch-size 32]

Requires ml/dataset/processed/{train,val,test}/ to exist — run
`python -m ml.scripts.prepare_dataset` first.
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import torch
from torch import nn, optim
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

SCRIPT_DIR = Path(__file__).resolve().parent
ML_DIR = SCRIPT_DIR.parent
PROCESSED_DIR = ML_DIR / "dataset" / "processed"
MODELS_DIR = ML_DIR / "models"

IMAGE_SIZE = 224
MODEL_NAME = "breed_classifier"
MODEL_VERSION = "0.1.0"

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_transforms() -> tuple[transforms.Compose, transforms.Compose]:
    train_tf = transforms.Compose(
        [
            transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    eval_tf = transforms.Compose(
        [
            transforms.Resize(int(IMAGE_SIZE * 1.14)),
            transforms.CenterCrop(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    return train_tf, eval_tf


def build_model(num_classes: int) -> nn.Module:
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model


def run_epoch(model, loader, criterion, optimizer, device, train: bool) -> tuple[float, float]:
    model.train(train)
    total_loss, correct, total = 0.0, 0, 0

    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)

            if train:
                optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            if train:
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * images.size(0)
            correct += (outputs.argmax(dim=1) == labels).sum().item()
            total += images.size(0)

    return total_loss / total, correct / total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    args = parser.parse_args()

    if not PROCESSED_DIR.exists():
        raise SystemExit(
            f"{PROCESSED_DIR} not found — run ml/scripts/prepare_dataset.py first."
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    train_tf, eval_tf = build_transforms()
    train_ds = ImageFolder(PROCESSED_DIR / "train", transform=train_tf)
    val_ds = ImageFolder(PROCESSED_DIR / "val", transform=eval_tf)

    assert train_ds.classes == val_ds.classes, "train/val class mismatch"
    class_names = train_ds.classes
    print(f"{len(class_names)} classes: {class_names}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)

    model = build_model(len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = 0.0
    history = []
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer, device, True)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, optimizer, device, False)
        scheduler.step()

        print(
            f"Epoch {epoch}/{args.epochs} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
            }
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODELS_DIR / f"{MODEL_NAME}.pt")

    elapsed = time.time() - start
    (MODELS_DIR / "class_names.json").write_text(json.dumps(class_names, indent=2))

    model_card = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "architecture": "mobilenet_v3_small (ImageNet-pretrained, fine-tuned)",
        "dataset": "Oxford-IIIT Pet (cat breeds only, 12 classes)",
        "dataset_version": json.loads((PROCESSED_DIR / "dataset_info.json").read_text())[
            "prepared_at"
        ],
        "training_params": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "image_size": IMAGE_SIZE,
            "optimizer": "AdamW",
            "scheduler": "CosineAnnealingLR",
        },
        "best_val_accuracy": best_val_acc,
        "training_time_seconds": elapsed,
        "trained_at": datetime.now(UTC).isoformat(),
        "history": history,
    }
    (MODELS_DIR / "model_card.json").write_text(json.dumps(model_card, indent=2))

    print(f"\nBest val accuracy: {best_val_acc:.4f}")
    print(f"Saved weights to {MODELS_DIR / f'{MODEL_NAME}.pt'}")
    print(f"Saved model card to {MODELS_DIR / 'model_card.json'}")


if __name__ == "__main__":
    main()
