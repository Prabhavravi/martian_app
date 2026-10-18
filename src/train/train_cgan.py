"""Training loop for fine-tuning the conditional GAN on desert terrain."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import torch
from torch import nn, optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.datasets import ImageFolder
from tqdm import tqdm

from .cgan import ConditionalDiscriminator, ConditionalGenerator
from .losses import bce_with_label_smoothing, hinge_d_loss, hinge_g_loss

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TerrainDataset(Dataset):
    """Dataset over preprocessed terrain tiles with biome labels."""

    def __init__(self, root: str | Path, transform=None) -> None:
        self.folder = ImageFolder(root=root, transform=transform)
        self.classes = self.folder.classes

    def __len__(self) -> int:
        return len(self.folder)

    def __getitem__(self, idx: int):
        return self.folder[idx]


def load_pretrained_desert_checkpoint(
    checkpoint_path: str | Path,
    generator: ConditionalGenerator,
    discriminator: ConditionalDiscriminator,
) -> None:
    """Load weights from a pretrained SingleTerrainGAN_desert.pkl checkpoint.

    The checkpoint may be a raw state_dict, a pickled StyleGAN2-style dict, or
    a dict containing 'generator'/'discriminator' keys. This function attempts
    to load compatible layers and leaves non-matching layers initialized.
    """
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    state = torch.load(checkpoint_path, map_location=DEVICE)

    # Normalize to a dict of sub-module state dicts
    gen_state = None
    disc_state = None
    if isinstance(state, dict):
        if "generator" in state and "discriminator" in state:
            gen_state = state["generator"]
            disc_state = state["discriminator"]
        elif "G_ema" in state and "D" in state:
            gen_state = state["G_ema"]
            disc_state = state["D"]
        elif "G" in state and "D" in state:
            gen_state = state["G"]
            disc_state = state["D"]
        else:
            # Assume the whole dict is the generator state
            gen_state = state

    def _load_into(module: nn.Module, state_dict: dict | None, tag: str) -> None:
        if state_dict is None:
            return
        own_state = module.state_dict()
        matched = 0
        for name, param in state_dict.items():
            if name in own_state:
                if own_state[name].shape == param.shape:
                    own_state[name].copy_(param)
                    matched += 1
        print(f"[fine-tune] {tag}: loaded {matched}/{len(own_state)} tensors")

    _load_into(generator, gen_state, "generator")
    _load_into(discriminator, disc_state, "discriminator")


def train_one_epoch(
    generator: ConditionalGenerator,
    discriminator: ConditionalDiscriminator,
    dataloader: DataLoader,
    g_optimizer: optim.Optimizer,
    d_optimizer: optim.Optimizer,
    latent_dim: int,
    num_biomes: int,
    device: torch.device,
    label_smoothing: float = 0.1,
) -> Dict[str, float]:
    generator.train()
    discriminator.train()

    d_losses: List[float] = []
    g_losses: List[float] = []

    for imgs, labels in tqdm(dataloader, desc="training", leave=False):
        batch_size = imgs.shape[0]
        imgs = imgs.to(device)
        labels = labels.to(device)

        # ---------------------
        # Train Discriminator
        # ---------------------
        d_optimizer.zero_grad()

        z = torch.randn(batch_size, latent_dim, device=device)
        gen_labels = torch.randint(0, num_biomes, (batch_size,), device=device)

        real_pred = discriminator(imgs, labels)
        fake_imgs = generator(z, gen_labels).detach()
        fake_pred = discriminator(fake_imgs, gen_labels)

        d_loss = hinge_d_loss(real_pred, fake_pred)
        d_loss.backward()
        d_optimizer.step()

        # ---------------------
        # Train Generator
        # ---------------------
        g_optimizer.zero_grad()

        z = torch.randn(batch_size, latent_dim, device=device)
        gen_labels = torch.randint(0, num_biomes, (batch_size,), device=device)

        fake_imgs = generator(z, gen_labels)
        fake_pred = discriminator(fake_imgs, gen_labels)

        g_loss = hinge_g_loss(fake_pred)
        g_loss.backward()
        g_optimizer.step()

        d_losses.append(d_loss.item())
        g_losses.append(g_loss.item())

    return {
        "d_loss": sum(d_losses) / max(len(d_losses), 1),
        "g_loss": sum(g_losses) / max(len(g_losses), 1),
    }


def fine_tune(
    data_dir: str | Path,
    checkpoint_path: str | Path | None,
    output_dir: str | Path,
    epochs: int = 20,
    batch_size: int = 16,
    latent_dim: int = 100,
    lr: float = 1e-4,
    img_size: int = 256,
    label_smoothing: float = 0.1,
    num_biomes: int = 5,
) -> None:
    """Fine-tune the conditional GAN from a pretrained desert checkpoint.

    Args:
        data_dir: directory of preprocessed tiles (ImageFolder format).
        checkpoint_path: path to SingleTerrainGAN_desert.pkl (or None to init randomly).
        output_dir: directory to save fine-tuned checkpoints.
        epochs: number of fine-tuning epochs (kept modest to avoid overfitting).
        batch_size: training batch size.
        latent_dim: generator latent dimension.
        lr: learning rate.
        img_size: tile resolution (power of two).
        label_smoothing: BCE label smoothing factor.
        num_biomes: number of biome classes.
    """
    device = DEVICE
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    transform = transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),
        ]
    )

    dataset = TerrainDataset(root=data_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=2)

    generator = ConditionalGenerator(
        latent_dim=latent_dim, num_biomes=num_biomes, img_channels=3, img_size=img_size
    ).to(device)
    discriminator = ConditionalDiscriminator(
        num_biomes=num_biomes, img_channels=3, img_size=img_size
    ).to(device)

    if checkpoint_path is not None:
        load_pretrained_desert_checkpoint(checkpoint_path, generator, discriminator)

    g_optimizer = optim.Adam(generator.parameters(), lr=lr, betas=(0.5, 0.999))
    d_optimizer = optim.Adam(discriminator.parameters(), lr=lr, betas=(0.5, 0.999))

    for epoch in range(1, epochs + 1):
        metrics = train_one_epoch(
            generator,
            discriminator,
            dataloader,
            g_optimizer,
            d_optimizer,
            latent_dim,
            num_biomes,
            device,
            label_smoothing,
        )
        print(
            f"Epoch {epoch}/{epochs} - "
            f"d_loss: {metrics['d_loss']:.4f} - g_loss: {metrics['g_loss']:.4f}"
        )

        # Monitor for mode collapse: if d_loss collapses to ~0, generator is winning too easily
        if metrics["d_loss"] < 0.05:
            print(
                f"[warn] discriminator loss very low ({metrics['d_loss']:.4f}) at epoch {epoch}; "
                "possible mode collapse — consider early stopping or reducing epochs."
            )

        # Save checkpoint each epoch (tracked via Git LFS)
        torch.save(
            {
                "epoch": epoch,
                "generator": generator.state_dict(),
                "discriminator": discriminator.state_dict(),
                "g_optimizer": g_optimizer.state_dict(),
                "d_optimizer": d_optimizer.state_dict(),
                "d_loss": metrics["d_loss"],
                "g_loss": metrics["g_loss"],
            },
            output_dir / f"cgan_epoch_{epoch}.pt",
        )

    print(f"[fine-tune] complete. Checkpoints saved to {output_dir}")
