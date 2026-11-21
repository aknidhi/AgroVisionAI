"""Streamlit page for live crop, plant and insect image analysis."""
import streamlit as st

from core.ui import render_page_header, render_section_header
from services.kindwise_service import (
    CropHealthAPIError,
    get_provider_status,
    identify_image,
)


def crop_health_lab():
    render_page_header(
        "Crop Health Lab",
        "Analyse real plant, crop and insect images using external AI identification services.",
        "LIVE AI DIAGNOSTICS",
        "🔬",
    )

    st.info(
        "Upload a clear photo of one plant, crop symptom or insect. "
        "Results are AI predictions, not a confirmed laboratory diagnosis."
    )

    render_section_header("Choose an analysis", "Select what you want AgroVision AI to examine.")
    mode = st.radio(
        "Analysis type",
        ["Plant identification", "Crop disease analysis", "Insect identification"],
        horizontal=True,
        key="crop_health_mode",
    )

    uploaded = st.file_uploader(
        "Upload an image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Use a clear, well-lit close-up. For disease analysis, include the affected leaf or crop area.",
        key="crop_health_image",
    )

    if uploaded:
        st.image(uploaded, caption=uploaded.name, width=360)

    with st.expander("API connection status"):
        status = get_provider_status()
        cols = st.columns(2)
        for index, (provider, configured) in enumerate(status.items()):
            with cols[index % 2]:
                st.write(("🟢 " if configured else "🔴 ") + provider)
                st.caption("Key configured" if configured else "Key missing in .env")

    if st.button("Analyse image", type="primary", disabled=uploaded is None, use_container_width=True):
        image_bytes = uploaded.getvalue()
        with st.spinner("Sending image securely to the selected AI provider..."):
            try:
                result = identify_image(mode, image_bytes, uploaded.name)
            except CropHealthAPIError as exc:
                st.error(str(exc))
                st.stop()
            except Exception as exc:
                st.error(f"Unexpected analysis error: {exc}")
                st.stop()

        st.success(f"Analysis completed using {result.get('provider', 'AI provider')}.")
        if result.get("fallback_reason"):
            st.warning(
                "The primary provider was unavailable, so the backup provider was used. "
                "Reason: " + result["fallback_reason"]
            )
        if result.get("coverage_note"):
            st.caption(result["coverage_note"])

        if mode == "Crop disease analysis" and result.get("crop_suggestions"):
            st.subheader("Crop identification")
            _show_suggestions(result["crop_suggestions"])

        if result.get("suggestions"):
            st.subheader(
                "Possible matches" if mode != "Crop disease analysis"
                else "Possible diseases, pests or health issues"
            )
            _show_suggestions(result["suggestions"])
        else:
            st.warning(
                "The provider did not return a likely match. Try a clearer close-up photo "
                "with better lighting."
            )

        if result.get("health"):
            st.subheader("Plant health assessment")
            _show_suggestions(result["health"])

        st.caption(
            "Confidence is the provider's model score, not a guarantee. "
            "Verify serious crop problems with a qualified local agricultural expert."
        )


def _show_suggestions(items):
    for index, item in enumerate(items[:5], start=1):
        name = item.get("name", "Unknown")
        probability = item.get("probability", item.get("score"))
        try:
            confidence = float(probability)
            confidence_text = f"{confidence * 100:.1f}%"
        except (TypeError, ValueError):
            confidence_text = "Not provided"

        with st.container(border=True):
            st.markdown(f"**{index}. {name}**")
            st.caption(f"Model confidence: {confidence_text}")
            details = item.get("details", {})
            if isinstance(details, dict):
                common = details.get("common_names") or details.get("commonNames")
                if isinstance(common, list) and common:
                    st.write("Common names: " + ", ".join(str(x) for x in common[:5]))
                family = details.get("family")
                if isinstance(family, str) and family:
                    st.write("Family: " + family)
                description = details.get("description")
                if isinstance(description, dict):
                    description = description.get("value") or description.get("text")
                if isinstance(description, str) and description:
                    st.write(description)
                treatment = details.get("treatment")
                if isinstance(treatment, dict):
                    treatment = treatment.get("value") or treatment.get("text")
                if isinstance(treatment, str) and treatment:
                    st.write("**Treatment information:** " + treatment)
