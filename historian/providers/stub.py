"""Deterministic fake provider — no external calls. Lets the whole async
pipeline be tested before a real model is wired in (Phase 5)."""


def analyze(prompt, cfg):
    return f"_(stub provider)_ received a {len(prompt)}-char prompt; no real analysis performed."
