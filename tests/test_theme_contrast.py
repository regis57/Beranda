"""Every theme's text colours must stay readable on its own background, by day and by night.

The accessibility check in CI runs axe on one theme (the default) in whichever mode the clock
gives it, so a colour just under the line in another theme, or in the other mode, went unseen -
and the default theme's small grey labels failed only in daylight runs. This test reads the
colours straight from every theme file, so it covers all of them and does not depend on the hour.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

THEMES = Path(__file__).resolve().parent.parent / "src" / "beranda" / "web" / "themes"

# WCAG AA asks 4.5 for normal text, the line axe draws in CI.
MINIMUM = 4.5

BLOCKS = {"light": r':root\[data-mode="light"\]\s*\{([^}]*)\}', "night": r':root\[data-mode="night"\]\s*\{([^}]*)\}'}


def _rgb(text: str) -> tuple[tuple[float, float, float], float]:
    text = text.strip()
    if text.startswith("#"):
        return tuple(int(text[i:i + 2], 16) for i in (1, 3, 5)), 1.0
    numbers = [float(n) for n in re.findall(r"[\d.]+", text)]
    return tuple(numbers[:3]), numbers[3] if len(numbers) > 3 else 1.0


def _luminance(colour) -> float:
    def channel(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground: str, background: str) -> float:
    bg, _ = _rgb(background)
    fg, alpha = _rgb(foreground)
    # A see-through ink is seen mixed with the background behind it, and the browser rounds that
    # mix to whole numbers: Japan's grey was 4.50 on paper but 4.49 in Chrome, and failed there.
    seen = tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg, strict=True))
    light, dark = sorted((_luminance(seen), _luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _colours(theme: Path, mode: str) -> dict[str, str]:
    block = re.search(BLOCKS[mode], theme.read_text())
    assert block, f"{theme.stem} has no {mode} block"
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", block.group(1)))


CASES = [(t, m, ink) for t in sorted(THEMES.glob("*.css")) for m in BLOCKS for ink in ("ink", "ink-2", "ink-3")]


@pytest.mark.parametrize(("theme", "mode", "ink"), CASES, ids=[f"{t.stem}-{m}-{i}" for t, m, i in CASES])
def test_text_is_readable_on_the_background(theme: Path, mode: str, ink: str) -> None:
    colours = _colours(theme, mode)
    ratio = contrast(colours[ink], colours["bg"])
    assert ratio >= MINIMUM, f"{theme.stem}, {mode}: --{ink} is {ratio:.2f}:1 on --bg, needs {MINIMUM}"


def test_the_arithmetic_matches_axe() -> None:
    # The value axe reported in CI for Japan's grey labels by day, before the fix.
    assert round(contrast("rgba(35, 32, 29, 0.63)", "#f4efe4"), 2) == pytest.approx(4.49, abs=0.01)
