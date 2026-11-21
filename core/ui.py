
from pathlib import Path
from html import escape
from textwrap import dedent

import streamlit as st


def load_global_styles():
    """Load AgroVision's global CSS."""

    css_path = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "styles"
        / "main.css"
    )

    if not css_path.exists():
        st.error(f"Stylesheet not found: {css_path}")
        return

    css = css_path.read_text(encoding="utf-8")

    # Inject CSS directly without Markdown parsing.
    st.html(f"<style>\n{css}\n</style>")


def render_page_header(
    title,
    subtitle,
    eyebrow="AGROVISION AI",
    icon=None
):
    """Render a reusable HTML page header."""

    safe_title = escape(str(title))
    safe_subtitle = escape(str(subtitle))
    safe_eyebrow = escape(str(eyebrow))
    safe_icon = escape(str(icon)) if icon else ""

    html = dedent(f"""
        <div class="av-page-header">

            <div class="av-page-eyebrow">
                <span>{safe_icon}</span>
                <span>{safe_eyebrow}</span>
            </div>

            <h1 class="av-page-title">
                {safe_title}
            </h1>

            <p class="av-page-subtitle">
                {safe_subtitle}
            </p>

        </div>
    """)

    # IMPORTANT: Use st.html, NOT st.markdown.
    st.html(html)


def render_section_header(title, subtitle=None):
    """Render a reusable section heading."""

    safe_title = escape(str(title))

    description = ""

    if subtitle:
        description = (
            f'<p class="av-section-subtitle">'
            f'{escape(str(subtitle))}'
            f'</p>'
        )

    html = dedent(f"""
        <div class="av-section-header">
            <h2>{safe_title}</h2>
            {description}
        </div>
    """)

    st.html(html)
