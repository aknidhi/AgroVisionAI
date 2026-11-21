
# ==========================================================
# AGROVISION AI - FARM SIMULATOR SERVICE
# ==========================================================

from typing import Dict, List


# ----------------------------------------------------------
# DEFAULT COST CATEGORIES
# ----------------------------------------------------------

COST_CATEGORIES = [
    "seed",
    "fertilizer",
    "pesticides",
    "irrigation",
    "labour",
    "machinery",
    "transport",
    "other"
]


# ----------------------------------------------------------
# INPUT VALIDATION
# ----------------------------------------------------------

def validate_farm_inputs(
    area_acres,
    expected_yield_per_acre,
    selling_price_per_quintal,
    costs_per_acre
):
    """
    Validate all farm simulation inputs.
    """

    if area_acres <= 0:
        raise ValueError(
            "Farm area must be greater than zero."
        )

    if expected_yield_per_acre < 0:
        raise ValueError(
            "Expected yield cannot be negative."
        )

    if selling_price_per_quintal < 0:
        raise ValueError(
            "Selling price cannot be negative."
        )

    for category, amount in costs_per_acre.items():

        if amount < 0:
            raise ValueError(
                f"{category} cost cannot be negative."
            )


# ----------------------------------------------------------
# FARM FINANCIAL SIMULATION
# ----------------------------------------------------------

def simulate_farm(
    crop,
    area_acres,
    expected_yield_per_acre,
    selling_price_per_quintal,
    costs_per_acre
):
    """
    Calculate estimated farm production,
    cultivation expenses, revenue and profit.

    Yield is measured in quintals per acre.
    Selling price and costs are in INR.
    """

    costs_per_acre = {
        category: float(
            costs_per_acre.get(category, 0)
        )
        for category in COST_CATEGORIES
    }

    area_acres = float(area_acres)

    expected_yield_per_acre = float(
        expected_yield_per_acre
    )

    selling_price_per_quintal = float(
        selling_price_per_quintal
    )

    validate_farm_inputs(
        area_acres,
        expected_yield_per_acre,
        selling_price_per_quintal,
        costs_per_acre
    )

    # Total production

    total_production = (
        area_acres * expected_yield_per_acre
    )

    # Total cultivation expenses

    total_cost_per_acre = sum(
        costs_per_acre.values()
    )

    total_cultivation_cost = (
        total_cost_per_acre * area_acres
    )

    # Revenue estimation

    gross_revenue = (
        total_production * selling_price_per_quintal
    )

    # Profit or loss

    net_profit = (
        gross_revenue - total_cultivation_cost
    )

    # Return on investment

    roi = (
        (net_profit / total_cultivation_cost) * 100
        if total_cultivation_cost > 0
        else None
    )

    # Break-even selling price

    break_even_price = (
        total_cultivation_cost / total_production
        if total_production > 0
        else None
    )

    # Cost per quintal

    cost_per_quintal = (
        total_cultivation_cost / total_production
        if total_production > 0
        else None
    )

    # Profit per acre

    profit_per_acre = (
        net_profit / area_acres
    )

    # Cost breakdown

    cost_breakdown = {
        category: round(amount * area_acres, 2)
        for category, amount in costs_per_acre.items()
    }

    return {
        "crop": str(crop),
        "area_acres": round(area_acres, 2),

        "expected_yield_per_acre": round(
            expected_yield_per_acre, 2
        ),

        "total_production_quintals": round(
            total_production, 2
        ),

        "selling_price_per_quintal": round(
            selling_price_per_quintal, 2
        ),

        "total_cultivation_cost": round(
            total_cultivation_cost, 2
        ),

        "gross_revenue": round(
            gross_revenue, 2
        ),

        "net_profit": round(
            net_profit, 2
        ),

        "profit_per_acre": round(
            profit_per_acre, 2
        ),

        "roi_percentage": (
            round(roi, 2)
            if roi is not None
            else None
        ),

        "break_even_price": (
            round(break_even_price, 2)
            if break_even_price is not None
            else None
        ),

        "cost_per_quintal": (
            round(cost_per_quintal, 2)
            if cost_per_quintal is not None
            else None
        ),

        "cost_breakdown": cost_breakdown,

        "financial_status": (
            "Profit" if net_profit > 0
            else "Break-even" if net_profit == 0
            else "Loss"
        ),

        "currency": "INR",
        "yield_unit": "quintals",
        "method": "User-input-based financial estimation"
    }


# ----------------------------------------------------------
# MULTI-CROP SCENARIO COMPARISON
# ----------------------------------------------------------

def compare_farm_scenarios(
    scenarios: List[Dict]
):
    """
    Compare multiple crop cultivation scenarios.
    """

    if not scenarios:
        raise ValueError(
            "At least one farm scenario is required."
        )

    results = []

    for scenario in scenarios:

        result = simulate_farm(
            crop=scenario["crop"],
            area_acres=scenario["area_acres"],
            expected_yield_per_acre=(
                scenario["expected_yield_per_acre"]
            ),
            selling_price_per_quintal=(
                scenario["selling_price_per_quintal"]
            ),
            costs_per_acre=scenario["costs_per_acre"]
        )

        results.append(result)

    return sorted(
        results,
        key=lambda item: item["net_profit"],
        reverse=True
    )


# ----------------------------------------------------------
# FINANCIAL SUMMARY
# ----------------------------------------------------------

def get_financial_summary(result):
    """
    Generate a readable financial summary.
    """

    return {
        "Crop": result["crop"],
        "Farm Area": f"{result['area_acres']} acres",

        "Production": (
            f"{result['total_production_quintals']} quintals"
        ),

        "Total Investment": (
            f"₹{result['total_cultivation_cost']:,.2f}"
        ),

        "Expected Revenue": (
            f"₹{result['gross_revenue']:,.2f}"
        ),

        "Estimated Profit/Loss": (
            f"₹{result['net_profit']:,.2f}"
        ),

        "ROI": (
            f"{result['roi_percentage']}%"
            if result["roi_percentage"] is not None
            else "Not available"
        ),

        "Financial Status": result["financial_status"]
    }
