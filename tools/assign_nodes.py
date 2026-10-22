#!/usr/bin/env python3
"""Assign unique derived scenes to the fixed grid and write static world data."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


def distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def king_adjacent(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1


def shared_sources(left: dict, right: dict) -> bool:
    return bool(set(left["sources"]) & set(right["sources"]))


def score(assignment: dict[tuple[int, int], dict]) -> tuple[int, int, int]:
    positions = list(assignment)
    minimum = 999
    adjacent_shared = 0
    preset_conflicts = 0
    for left, right in itertools.combinations(positions, 2):
        if shared_sources(assignment[left], assignment[right]):
            minimum = min(minimum, distance(left, right))
            if king_adjacent(left, right):
                adjacent_shared += 1
        if king_adjacent(left, right) and assignment[left]["preset"] == assignment[right]["preset"]:
            preset_conflicts += 1
    return (minimum if minimum != 999 else 999, -adjacent_shared, -preset_conflicts)


def best_two_source_pattern(positions: list[tuple[int, int]], start: tuple[int, int], source_ids: list[str]) -> dict[tuple[int, int], str]:
    best = None
    best_assignment = None
    for bits in itertools.product(source_ids, repeat=len(positions)):
        candidate = {start: source_ids[1]}
        candidate.update(dict(zip(positions, bits)))
        minimum = 999
        adjacent_shared = 0
        for left, right in itertools.combinations(candidate, 2):
            if candidate[left] == candidate[right]:
                minimum = min(minimum, distance(left, right))
                if king_adjacent(left, right):
                    adjacent_shared += 1
        value = (minimum if minimum != 999 else 999, -adjacent_shared)
        if best is None or value > best:
            best = value
            best_assignment = candidate
    return best_assignment


def choose_candidates(positions: list[tuple[int, int]], source_pattern: dict[tuple[int, int], str], candidates: list[dict]) -> dict[tuple[int, int], dict]:
    by_source = {}
    for candidate in candidates:
        if len(candidate["sources"]) == 1:
            by_source.setdefault(candidate["sources"][0], []).append(candidate)
    for values in by_source.values():
        values.sort(key=lambda item: item["file"])
    order = sorted(positions, key=lambda p: sum(king_adjacent(p, q) for q in positions), reverse=True)
    selected = {}
    used = set()

    def visit(index: int) -> bool:
        if index == len(order):
            return True
        position = order[index]
        options = by_source.get(source_pattern[position], [])
        for candidate in options:
            if candidate["file"] in used:
                continue
            if any(king_adjacent(position, other) and selected[other]["preset"] == candidate["preset"] for other in selected):
                continue
            selected[position] = candidate
            used.add(candidate["file"])
            if visit(index + 1):
                return True
            used.remove(candidate["file"])
            del selected[position]
        return False

    if not visit(0):
        raise RuntimeError("could not assign unique scenes with different neighbouring colour grades")
    return selected


def assign(root: Path, metadata_path: Path, world_path: Path) -> dict:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_ids = sorted(metadata["sources"])
    variants = []
    for filename, value in sorted(metadata["variants"].items()):
        variants.append({"file": f"assets/panoramas/derived/{filename}", "sources": value["sources"], "recipe": value["recipe"], "preset": value["recipe"]["preset"]})
    width = height = 4
    start = (1, 3)
    positions = [(x, y) for y in range(height) for x in range(width) if (x, y) != start]
    if len(source_ids) == 2:
        source_pattern = best_two_source_pattern(positions, start, source_ids)
    else:
        source_pattern = {position: source_ids[(position[0] + position[1]) % len(source_ids)] for position in positions}
    selected = choose_candidates(positions, source_pattern, variants)

    nodes = {}
    for y in range(height):
        for x in range(width):
            position = (x, y)
            if position == start:
                nodes[f"{x}:{y}"] = {
                    "x": x, "y": y, "image": "assets/panoramas/martian_panorama_seamless.png",
                    "source": "real", "sources": ["martian_panorama_seamless"], "preset": "real", "sourceDimensions": "2048x512",
                }
            else:
                candidate = selected[position]
                nodes[f"{x}:{y}"] = {"x": x, "y": y, "image": candidate["file"], "source": "derived", "sources": candidate["sources"], "preset": candidate["preset"], "recipe": candidate["recipe"]}
    source_count = len(set(source_ids + ["martian_panorama_seamless"]))
    achieved = score({position: selected[position] for position in positions} | {start: {"sources": ["martian_panorama_seamless"], "preset": "real"}})[0]
    world_data = {
        "width": width, "height": height, "spanDegrees": 360, "fovDegrees": 90,
        "start": {"x": start[0], "y": start[1], "heading": 0}, "nodes": nodes,
        "variety": {
            "sourceIds": sorted(set(source_ids + ["martian_panorama_seamless"])),
            "sourceBudget": source_count,
            "minimumSourcesForNeighbourConstraint": 4,
            "requiredMinSourceDistance": 3,
            "achievedMinSourceDistance": achieved,
            "constraintStatus": "source-budget-limited" if source_count < 4 else "satisfied",
        },
    }
    text = world_path.read_text(encoding="utf-8")
    start_marker = "  var WORLD = {"
    end_marker = "\n\n  function key"
    start_index = text.index(start_marker)
    end_index = text.index(end_marker, start_index)
    replacement = "  var WORLD = " + json.dumps(world_data, indent=4) + ";"
    world_path.write_text(text[:start_index] + replacement + text[end_index:], encoding="utf-8")
    return world_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=Path("assets/panoramas/variants.json"))
    parser.add_argument("--world", type=Path, default=Path("world.js"))
    args = parser.parse_args()
    data = assign(Path.cwd(), args.metadata, args.world)
    print(f"assigned {data['width'] * data['height']} nodes; minimum same-source distance={data['variety']['achievedMinSourceDistance']}; status={data['variety']['constraintStatus']}")


if __name__ == "__main__":
    main()
