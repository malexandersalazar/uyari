"""The demo's look: Meta "Astryx" tokens (light / dark) mapped onto Gradio's theme variables. Gradio-free:
CI installs no Gradio, so this pins the stylesheet text and the launch wiring, not rendered pixels."""

from __future__ import annotations

import inspect
import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "demo"))
from app import CSS, _theme, launch  # noqa: E402  demo/app.py

LIGHT = {"#F2F4F6": "page background", "#FFFFFF": "surface", "#111112": "text primary",
         "#666A72": "text secondary", "#0064E0": "accent", "#DFE2E5": "border"}
DARK = {"#111112": "page background", "#1F1F22": "surface", "#F2F4F6": "text primary",
        "#9FA4AB": "text secondary", "#2694FE": "accent", "#3E9EFB": "links", "#494D53": "border"}


def _blocks() -> tuple[str, str]:
    light, _, dark = CSS.partition(":root.dark")
    assert dark, "CSS must carry a dark block riding on Gradio's .dark class"
    return light, dark


def test_light_tokens():
    light, _ = _blocks()
    for hex_, role in LIGHT.items():
        assert hex_ in light, f"light {role} ({hex_})"


def test_dark_tokens():
    _, dark = _blocks()
    for hex_, role in DARK.items():
        assert hex_ in dark, f"dark {role} ({hex_})"


def test_shape_motion_and_links():
    for needle in ("9999px", "--block-radius: 12px", "--input-radius: 8px", "prefers-reduced-motion",
                   "text-decoration: none", ":focus-visible", "--uy-ring-selected", "overflow-wrap: anywhere",
                   ".uy-pairs table"):
        assert needle in CSS, needle


def test_launch_uses_the_theme_and_stylesheet():
    assert callable(_theme)
    src = inspect.getsource(launch)
    assert "theme=_theme()" in src and "css=CSS" in src


def test_footer_credits_designer_and_builder():
    from app import HF_NLLB_URL, LINKEDIN_URL, HF_GLMmer30B_URL  # noqa: E402

    assert LINKEDIN_URL == "https://www.linkedin.com/in/malexandersalazar/"
    assert HF_GLMmer30B_URL == "https://huggingface.co/malexandersalazar/uyari-mt-cbt-glimmer30b-qlora"
    assert HF_NLLB_URL == "https://huggingface.co/malexandersalazar/uyari-mt-cbt-nllb1.3b"
    src = inspect.getsource(launch)
    assert "Designed by Muse Spark 1.3 Contributor" in src
    assert "LINKEDIN_URL" in src and "@malexandersalazar" in src
    assert ">GitHub</a>" in src  # short link text, so nothing overflows the footer
    assert "HF_GLMmer30B_URL" in src and "HF_NLLB_URL" in src
    assert src.count('elem_classes="uy-pairs"') == 2
