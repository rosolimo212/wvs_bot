# coding: utf-8
"""
PNG для соцсетей: квадрат 1080×1080, прозрачный фон.

«Найти страну»: scatter + QR + профиль страны.
«Понять своё место»: две гистограммы + QR + сравнение с выборкой.
"""

from __future__ import annotations

import io
import re
import textwrap
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from core.country_profiles import format_country_profile
from core.messages import message
from ui.country_plot import build_country_plot
from ui.mini_qr import qr_to_rgb
from ui.own_place_plot import build_index_histogram_matplotlib

DEFAULT_LANDING_URL = "https://worldvaluessurveybot.info"
CANVAS_INCH = 10.8
CANVAS_DPI = 100
_INK = "#1a1a1a"
_MUTED = "#4a5568"
_ACCENT = "#0c6b58"


def plain_text(text: str) -> str:
    """Убирает markdown (**bold**) для текста на картинке."""
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", str(text)).strip()


def _channel(channel: str | None) -> str:
    return channel or "streamlit"


def _figure_to_rgba(fig: Figure, *, dpi: int = CANVAS_DPI) -> np.ndarray:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return plt.imread(buf)


def _save_canvas(fig: Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=CANVAS_DPI,
        transparent=True,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="none",
    )
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _stack_images(images: list[np.ndarray]) -> np.ndarray:
    if not images:
        raise ValueError("Нет изображений для сборки")
    if len(images) == 1:
        return images[0]
    widths = [img.shape[1] for img in images]
    target_w = max(widths)
    resized: list[np.ndarray] = []
    for img in images:
        if img.shape[1] != target_w:
            scale = target_w / img.shape[1]
            new_h = max(1, int(img.shape[0] * scale))
            y_idx = (np.linspace(0, img.shape[0] - 1, new_h)).astype(int)
            x_idx = (np.linspace(0, img.shape[1] - 1, target_w)).astype(int)
            img = img[y_idx][:, x_idx]
        resized.append(img)
    return np.vstack(resized)


def _wrap_block(text: str, *, width: int) -> str:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return "\n".join(textwrap.fill(p, width=width) for p in paragraphs)


def _draw_wrapped(ax: plt.Axes, text: str, *, fontsize: float, color: str = _INK) -> None:
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    y = 1.0
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            y -= 0.04
            continue
        wrapped = textwrap.fill(paragraph.strip(), width=52)
        line_count = wrapped.count("\n") + 1
        ax.text(0, y, wrapped, va="top", ha="left", fontsize=fontsize, color=color, linespacing=1.25)
        y -= 0.038 * line_count + 0.02
        if y < 0:
            break


def _share_texts(channel: str | None) -> dict[str, str]:
    ch = _channel(channel)
    return {
        "title": message("share_image_title", ch),
        "qr_cta": message("share_image_qr_cta", ch),
        "footer_url": message("share_image_footer_url", ch) or DEFAULT_LANDING_URL,
        "footer_cta": message("share_image_footer_cta", ch),
    }


def _compose_share_canvas(
    *,
    channel: str | None,
    result_headline: str,
    left_image: np.ndarray,
    body_text: str,
    landing_url: str | None = None,
) -> bytes:
    texts = _share_texts(channel)
    url = landing_url or texts["footer_url"]

    fig = plt.figure(figsize=(CANVAS_INCH, CANVAS_INCH), dpi=CANVAS_DPI)
    fig.patch.set_alpha(0)

    fig.text(0.5, 0.975, texts["title"], ha="center", va="top", fontsize=13, color=_INK, wrap=True)
    fig.text(
        0.5,
        0.905,
        plain_text(result_headline),
        ha="center",
        va="top",
        fontsize=22,
        fontweight="bold",
        color=_INK,
    )

    ax_plot = fig.add_axes([0.05, 0.36, 0.56, 0.50])
    ax_plot.imshow(left_image)
    ax_plot.axis("off")

    ax_qr = fig.add_axes([0.66, 0.48, 0.29, 0.29])
    ax_qr.imshow(qr_to_rgb(url, box_size=5, border=2))
    ax_qr.axis("off")
    ax_qr.text(0.5, -0.08, texts["qr_cta"], transform=ax_qr.transAxes, ha="center", va="top", fontsize=11, color=_INK)

    ax_body = fig.add_axes([0.05, 0.12, 0.90, 0.20])
    _draw_wrapped(ax_body, _wrap_block(body_text, width=56), fontsize=9)

    fig.text(0.5, 0.075, url, ha="center", va="top", fontsize=11, color=_ACCENT, fontweight="bold")
    fig.text(0.5, 0.035, texts["footer_cta"], ha="center", va="top", fontsize=10, color=_MUTED)

    return _save_canvas(fig)


def build_country_share_png(
    *,
    user_rv: float,
    user_sv: float,
    country_code: str,
    country_rv: float | None = None,
    country_sv: float | None = None,
    logging_config: dict[str, Any] | None = None,
    reference_schema: str = "wvs",
    landing_url: str | None = None,
    country_df: Any = None,
    channel: str | None = "streamlit",
) -> bytes:
    if logging_config is None:
        raise RuntimeError("logging_config required")

    plot_fig, _timings = build_country_plot(
        float(user_sv),
        float(user_rv),
        logging_config,
        reference_schema=reference_schema,
        country_df=country_df,
    )
    if plot_fig is None:
        raise RuntimeError("Не удалось построить график стран")

    plot_img = _figure_to_rgba(plot_fig)

    ch = _channel(channel)
    headline = message(
        "share_image_result",
        ch,
        user_rv=int(round(float(user_rv))),
        user_sv=int(round(float(user_sv))),
    )
    profile = plain_text(format_country_profile(str(country_code).upper(), ch))
    if not profile:
        profile = message("country_profile_missing", ch, country_code=str(country_code).upper())
    if country_rv is not None and country_sv is not None:
        nearest = plain_text(
            message(
                "find_country_result",
                ch,
                country_code=str(country_code).upper(),
                country_rv=f"{float(country_rv):.1f}",
                country_sv=f"{float(country_sv):.1f}",
            )
        )
        profile = f"{nearest}\n\n{profile}".strip()

    return _compose_share_canvas(
        channel=ch,
        result_headline=headline,
        left_image=plot_img,
        body_text=profile,
        landing_url=landing_url,
    )


def build_own_place_share_png(
    *,
    user_rv: float,
    user_sv: float,
    own_place_charts: list[dict[str, Any]],
    share_body_lines: list[str] | None = None,
    landing_url: str | None = None,
    channel: str | None = "streamlit",
) -> bytes:
    hist_images: list[np.ndarray] = []
    for chart in own_place_charts[:2]:
        fig = build_index_histogram_matplotlib(
            list(chart["peer_values"]),
            float(chart["user_value"]),
            title=str(chart["title"]),
            x_label=str(chart["x_label"]),
        )
        if fig is not None:
            hist_images.append(_figure_to_rgba(fig))

    if not hist_images:
        raise RuntimeError("Нет гистограмм для карточки")

    left_image = _stack_images(hist_images)

    ch = _channel(channel)
    headline = message(
        "share_image_result",
        ch,
        user_rv=int(round(float(user_rv))),
        user_sv=int(round(float(user_sv))),
    )
    body = "\n".join(plain_text(line) for line in (share_body_lines or []) if plain_text(line))

    return _compose_share_canvas(
        channel=ch,
        result_headline=headline,
        left_image=left_image,
        body_text=body,
        landing_url=landing_url,
    )
