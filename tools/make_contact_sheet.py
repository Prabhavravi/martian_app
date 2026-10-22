#!/usr/bin/env python3
"""Make a labelled node contact sheet using the system image codecs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("contact_sheet.jpg"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    node_script = "const W=require('./world.js'); console.log(JSON.stringify(Object.values(W.WORLD.nodes).sort((a,b)=>a.y-b.y||a.x-b.x)));"
    result = subprocess.run(["node", "-e", node_script], cwd=root, check=True, capture_output=True, text=True)
    nodes = json.loads(result.stdout)
    with tempfile.NamedTemporaryFile("w", suffix=".manifest", delete=False) as manifest_file:
        manifest_path = Path(manifest_file.name)
        for node in nodes:
            source_label = "+".join(node.get("sources", [node.get("source", "unknown")]))
            manifest_file.write(f"{node['x']}|{node['y']}|{source_label}|{(root / node['image']).resolve()}\n")
    try:
        binary = Path(tempfile.mktemp(prefix="martian-contact-sheet-"))
        subprocess.run(
            ["clang", "-framework", "CoreFoundation", "-framework", "CoreGraphics", "-framework", "CoreText", "-framework", "ImageIO", str(root / "tools/make_contact_sheet.c"), "-o", str(binary)],
            cwd=root,
            check=True,
        )
        subprocess.run(
            [str(binary), "--manifest", str(manifest_path), "--output", str((root / args.output).resolve())],
            cwd=root,
            check=True,
        )
    finally:
        manifest_path.unlink(missing_ok=True)
        if "binary" in locals(): binary.unlink(missing_ok=True)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
