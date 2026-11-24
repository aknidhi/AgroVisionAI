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
    st.html(f"<style>\\n{css}\\n</style>")


# Each module receives its own visual identity while sharing the same
# AgroVision layout, spacing, typography and responsive behaviour.
_PAGE_THEMES = {
    "agricultural intelligence, reimagined.": {
        "theme": "home", "kicker": "SMART AGRICULTURE PLATFORM",
        "visual_title": "Data to decisions",
        "visual_text": "One connected place for smarter agriculture.",
        "tags": ("REAL-TIME DATA", "AI INSIGHTS", "FARMING")
    },
    "agricultural overview": {
        "theme": "dashboard", "kicker": "LIVE PLATFORM PULSE",
        "visual_title": "Your command centre",
        "visual_text": "Markets, weather and research at a glance.",
        "tags": ("MARKETS", "WEATHER", "RESEARCH")
    },
    "crop intelligence": {
        "theme": "crop", "kicker": "CROP & SOIL ANALYTICS",
        "visual_title": "Grow with insight",
        "visual_text": "Explore crop suitability with soil and weather context.",
        "tags": ("SOIL", "CROP SUITABILITY", "RECOMMENDATIONS")
    },
    "crop health lab": {
        "theme": "health", "kicker": "AI-POWERED DIAGNOSTICS",
        "visual_title": "A closer look at crop health",
        "visual_text": "Analyse plant, crop and insect images with AI services.",
        "tags": ("IMAGE ANALYSIS", "PLANT HEALTH", "DIAGNOSIS")
    },
    "farm decision simulator": {
        "theme": "farm", "kicker": "FARM PLANNING & ECONOMICS",
        "visual_title": "Plan before you plant",
        "visual_text": "Compare cultivation costs, returns and crop scenarios.",
        "tags": ("COSTS", "PROFITABILITY", "SCENARIOS")
    },
    "weather intelligence": {
        "theme": "weather", "kicker": "LIVE WEATHER & FORECASTS",
        "visual_title": "Prepare for the conditions",
        "visual_text": "Understand current weather, forecasts and farm risks.",
        "tags": ("LIVE CONDITIONS", "7-DAY FORECAST", "RISK")
    },
    "market intelligence": {
        "theme": "market", "kicker": "AGRICULTURAL MARKET WATCH",
        "visual_title": "Know the market",
        "visual_text": "Explore mandi prices, commodity movement and comparisons.",
        "tags": ("MANDI PRICES", "COMMODITIES", "TRENDS")
    },
    "agricultural research centre": {
        "theme": "research", "kicker": "EVIDENCE & DISCOVERY",
        "visual_title": "Research-backed insight",
        "visual_text": "Discover agricultural studies, publications and evidence.",
        "tags": ("OPEN RESEARCH", "PUBLICATIONS", "DISCOVERY")
    },
    "reports & insights": {
        "theme": "reports", "kicker": "AGRICULTURAL REPORTING CENTRE",
        "visual_title": "Turn information into a report",
        "visual_text": "Build useful reports from market, weather and farm estimates.",
        "tags": ("REPORTS", "MARKET DATA", "WEATHER")
    },
    "data sources & transparency": {
        "theme": "sources", "kicker": "TRUST & DATA TRANSPARENCY",
        "visual_title": "Know where the data comes from",
        "visual_text": "Explore providers, reference data and fallback pathways.",
        "tags": ("DATA PROVIDERS", "REFERENCE DATA", "FALLBACKS")
    },
}


def render_page_header(title, subtitle, eyebrow="AGROVISION AI", icon=None):
    """Render a distinctive, responsive hero header for each AgroVision page."""

    safe_title = escape(str(title))
    safe_subtitle = escape(str(subtitle))
    safe_eyebrow = escape(str(eyebrow))
    safe_icon = escape(str(icon)) if icon else "🌱"

    config = _PAGE_THEMES.get(
        str(title).strip().casefold(),
        {
            "theme": "default",
            "kicker": str(eyebrow),
            "visual_title": "AgroVision AI",
            "visual_text": "Agricultural intelligence for better decisions.",
            "tags": ("AGRICULTURE", "DATA", "INSIGHTS"),
        },
    )

    theme = escape(config["theme"])
    kicker = escape(config["kicker"])
    visual_title = escape(config["visual_title"])
    visual_text = escape(config["visual_text"])
    tags = "".join(
        f'<span class="av-hero-chip">{escape(tag)}</span>'
        for tag in config["tags"]
    )

    html = dedent(f"""
        <section class="av-page-hero av-theme-{theme}" aria-label="{safe_title}">
            <div class="av-hero-orb av-hero-orb-one"></div>
            <div class="av-hero-orb av-hero-orb-two"></div>

            <div class="av-hero-content">
                <div class="av-page-eyebrow">
                    <span class="av-eyebrow-icon">{safe_icon}</span>
                    <span>{safe_eyebrow}</span>
                </div>

                <div class="av-hero-copy">
                    <div class="av-hero-kicker">{kicker}</div>
                    <h1 class="av-page-title">{safe_title}</h1>
                    <p class="av-page-subtitle">{safe_subtitle}</p>
                    <div class="av-hero-chips">{tags}</div>
                </div>
            </div>

            <div class="av-hero-visual" aria-hidden="true">
                <div class="av-visual-ring av-visual-ring-one"></div>
                <div class="av-visual-ring av-visual-ring-two"></div>
                <div class="av-visual-icon">{safe_icon}</div>
                <div class="av-visual-caption">
                    <span class="av-visual-status-dot"></span>
                    <span class="av-visual-caption-label">{visual_title}</span>
                    <span class="av-visual-caption-text">{visual_text}</span>
                </div>
                <div class="av-visual-spark av-spark-one">✦</div>
                <div class="av-visual-spark av-spark-two">✧</div>
            </div>

            <div class="av-hero-bottom-line"></div>
        </section>
    """)

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
