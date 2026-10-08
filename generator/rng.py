"""Independent random streams derived from the root seed."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

STREAM_NAMES = ("units", "supplies", "companies", "purchases", "orphans", "faker")


@dataclass(frozen=True)
class Streams:
    units: np.random.Generator
    supplies: np.random.Generator
    companies: np.random.Generator
    purchases: np.random.Generator
    orphans: np.random.Generator
    faker_seed: int


def make_streams(seed: str) -> Streams:
    """Spawn one child per component, always in the order of STREAM_NAMES."""
    children = np.random.SeedSequence(int(seed, 16)).spawn(len(STREAM_NAMES))
    by_name = dict(zip(STREAM_NAMES, children, strict=True))
    return Streams(
        units=np.random.default_rng(by_name["units"]),
        supplies=np.random.default_rng(by_name["supplies"]),
        companies=np.random.default_rng(by_name["companies"]),
        purchases=np.random.default_rng(by_name["purchases"]),
        orphans=np.random.default_rng(by_name["orphans"]),
        faker_seed=int(by_name["faker"].generate_state(1, dtype=np.uint64)[0]),
    )
