"""Loss functions for conditional GAN training."""

from __future__ import annotations

import torch


def hinge_d_loss(real_pred: torch.Tensor, fake_pred: torch.Tensor) -> torch.Tensor:
    """Hinge loss for the discriminator."""
    loss_real = torch.mean(torch.nn.functional.relu(1.0 - real_pred))
    loss_fake = torch.mean(torch.nn.functional.relu(1.0 + fake_pred))
    return loss_real + loss_fake


def hinge_g_loss(fake_pred: torch.Tensor) -> torch.Tensor:
    """Hinge loss for the generator."""
    return -torch.mean(fake_pred)


def bce_with_label_smoothing(
    pred: torch.Tensor,
    target: torch.Tensor,
    smoothing: float = 0.1,
) -> torch.Tensor:
    """Binary cross-entropy with optional label smoothing applied to real targets."""
    if smoothing > 0.0 and torch.all(target == 1.0):
        target = target * (1.0 - smoothing) + smoothing * 0.5
    return torch.nn.functional.binary_cross_entropy_with_logits(pred, target)
