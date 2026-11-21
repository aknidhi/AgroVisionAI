
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CROP_DATABASE = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "crop_requirements.csv"
)


# --------------------------------------------------
# LOAD CROP DATABASE
# --------------------------------------------------

def load_crop_requirements():
    """
    Load crop soil requirement information.
    """

    if not CROP_DATABASE.exists():
        raise FileNotFoundError(
            f"Crop database not found: {CROP_DATABASE}"
        )

    df = pd.read_csv(CROP_DATABASE)

    required_columns = [
        "crop",
        "min_ph",
        "max_ph",
        "source"
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing crop database columns: {missing}"
        )

    df["min_ph"] = pd.to_numeric(
        df["min_ph"], errors="coerce"
    )

    df["max_ph"] = pd.to_numeric(
        df["max_ph"], errors="coerce"
    )

    df = df.dropna(
        subset=["crop", "min_ph", "max_ph"]
    )

    df = df[
        (df["min_ph"] >= 0)
        & (df["max_ph"] <= 14)
        & (df["min_ph"] <= df["max_ph"])
    ]

    return df.reset_index(drop=True)


# --------------------------------------------------
# SOIL PH ANALYSIS
# --------------------------------------------------

def analyze_soil_ph(ph):
    """
    Classify soil according to its pH value.
    """

    ph = float(ph)

    if not 0 <= ph <= 14:
        raise ValueError(
            "Soil pH must be between 0 and 14."
        )

    if ph < 5.5:
        return {
            "category": "Strongly acidic",
            "description": "Soil acidity may limit nutrient availability."
        }

    elif ph < 6.5:
        return {
            "category": "Moderately acidic",
            "description": "Suitable pH range for many agricultural crops."
        }

    elif ph <= 7.5:
        return {
            "category": "Near neutral",
            "description": "Generally favorable pH for many crops."
        }

    elif ph <= 8.5:
        return {
            "category": "Moderately alkaline",
            "description": "Some nutrients may become less available."
        }

    else:
        return {
            "category": "Strongly alkaline",
            "description": "High alkalinity may restrict crop growth."
        }


# --------------------------------------------------
# CROP PH SUITABILITY
# --------------------------------------------------

def evaluate_crop_suitability(ph, crop_database=None):
    """
    Compare measured soil pH with crop reference ranges.

    The score is a pH-match score, not a prediction
    of actual yield or overall crop suitability.
    """

    ph = float(ph)

    if not 0 <= ph <= 14:
        raise ValueError(
            "Soil pH must be between 0 and 14."
        )

    if crop_database is None:
        crop_database = load_crop_requirements()

    results = []

    for _, crop in crop_database.iterrows():

        minimum = float(crop["min_ph"])
        maximum = float(crop["max_ph"])

        if minimum <= ph <= maximum:

            distance = 0
            status = "Within reference pH range"
            score = 100.0

        else:

            if ph < minimum:
                distance = minimum - ph
            else:
                distance = ph - maximum

            status = "Outside reference pH range"

            # A transparent distance-based comparison.
            score = max(
                0.0,
                100.0 - (distance * 20)
            )

        results.append({
            "crop": crop["crop"],
            "min_ph": minimum,
            "max_ph": maximum,
            "soil_ph": ph,
            "ph_match_score": round(score, 1),
            "distance_from_range": round(distance, 2),
            "status": status,
            "source": crop["source"]
        })

    return sorted(
        results,
        key=lambda item: (
            item["distance_from_range"],
            item["crop"]
        )
    )


# --------------------------------------------------
# CROP RECOMMENDATIONS
# --------------------------------------------------

def recommend_crops(ph, top_n=5):
    """
    Return crops ranked by their soil pH match.
    """

    if top_n < 1:
        raise ValueError(
            "top_n must be at least 1."
        )

    soil_analysis = analyze_soil_ph(ph)

    crop_results = evaluate_crop_suitability(ph)

    return {
        "soil_analysis": soil_analysis,
        "soil_ph": float(ph),
        "total_crops_evaluated": len(crop_results),
        "matching_crops": [
            crop for crop in crop_results
            if crop["status"] == "Within reference pH range"
        ],
        "recommendations": crop_results[:top_n],
        "method": "Soil pH reference-range comparison"
    }
