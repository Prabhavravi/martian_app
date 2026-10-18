"""Conditional GAN for Martian terrain texture generation."""

from __future__ import annotations

import torch
from torch import nn


class ConditionalGenerator(nn.Module):
    """Generator: latent vector z + biome label -> texture image."""

    def __init__(
        self,
        latent_dim: int = 100,
        num_biomes: int = 5,
        img_channels: int = 3,
        img_size: int = 256,
    ) -> None:
        super().__init__()
        self.latent_dim = latent_dim
        self.num_biomes = num_biomes
        self.img_channels = img_channels
        self.img_size = img_size

        self.label_emb = nn.Embedding(num_biomes, latent_dim)

        self.init_size = img_size // 4
        self.l1 = nn.Sequential(nn.Linear(latent_dim * 2, 128 * self.init_size**2))

        self.conv_blocks = nn.Sequential(
            nn.BatchNorm2d(128),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(128, 128, 3, stride=1, padding=1),
            nn.BatchNorm2d(128, 0.8),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Upsample(scale_factor=2),
            nn.Conv2d(128, 64, 3, stride=1, padding=1),
            nn.BatchNorm2d(64, 0.8),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(64, img_channels, 3, stride=1, padding=1),
            nn.Tanh(),
        )

    def forward(self, noise: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        label_emb = self.label_emb(labels)
        gen_input = torch.cat((noise, label_emb), -1)
        out = self.l1(gen_input)
        out = out.view(out.shape[0], 128, self.init_size, self.init_size)
        img = self.conv_blocks(out)
        return img


class ConditionalDiscriminator(nn.Module):
    """Discriminator: image + biome label -> real/fake score."""

    def __init__(
        self,
        num_biomes: int = 5,
        img_channels: int = 3,
        img_size: int = 256,
    ) -> None:
        super().__init__()
        self.num_biomes = num_biomes
        self.img_channels = img_channels
        self.img_size = img_size

        self.label_emb = nn.Embedding(num_biomes, img_size * img_size)

        def discriminator_block(in_filters: int, out_filters: int, bn: bool = True):
            block = [nn.Conv2d(in_filters, out_filters, 3, 2, 1), nn.LeakyReLU(0.2, inplace=True), nn.Dropout2d(0.25)]
            if bn:
                block.append(nn.BatchNorm2d(out_filters, 0.8))
            return block

        self.model = nn.Sequential(
            *discriminator_block(img_channels + 1, 64, bn=False),
            *discriminator_block(64, 128),
            *discriminator_block(128, 256),
            *discriminator_block(256, 512),
        )

        ds_size = img_size // 2**4
        self.adv_layer = nn.Sequential(nn.Linear(512 * ds_size**2, 1))

    def forward(self, img: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        label_emb = self.label_emb(labels).view(img.shape[0], 1, self.img_size, self.img_size)
        d_in = torch.cat((img, label_emb), 1)
        out = self.model(d_in)
        out = out.view(out.shape[0], -1)
        validity = self.adv_layer(out)
        return validity
