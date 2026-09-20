"""KOHLER AquaGuard AI — Multi-Airport Portfolio & Fleet Benchmarking Engine.

Consolidates facility health, water conservation accounting, and SLA performance
across multiple international aviation hubs in India.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone
from app import views

PORTFOLIO_AIRPORTS = {
    "PNQ": {
        "airport_code": "PNQ",
        "airport_name": "Pune International Airport",
        "terminal_focus": "New Integrated Terminal (T1, T2, T3, Arrivals)",
        "city": "Pune, Maharashtra",
        "is_active_twin": True,
        "fixtures_monitored": 97,
        "restrooms_count": 12,
        "pax_per_day": 32_000,
        "established_date": "2024",
    },
    "BOM": {
        "airport_code": "BOM",
        "airport_name": "Mumbai Chhatrapati Shivaji Maharaj International Airport",
        "terminal_focus": "Terminal 2 (International & Domestic Hub)",
        "city": "Mumbai, Maharashtra",
        "is_active_twin": False,
        "fixtures_monitored": 184,
        "restrooms_count": 24,
        "pax_per_day": 85_000,
        "established_date": "2023",
        "fixed_stats": {
            "facility_health": 89,
            "saved_liters_today": 92_400,
            "tariff_savings_monthly_inr": 1_247_400,
            "sla_compliance_pct": 99.1,
            "active_incidents": 2,
        }
    },
    "DEL": {
        "airport_code": "DEL",
        "airport_name": "Delhi Indira Gandhi International Airport",
        "terminal_focus": "Terminal 3 (Mega Hub)",
        "city": "New Delhi",
        "is_active_twin": False,
        "fixtures_monitored": 312,
        "restrooms_count": 42,
        "pax_per_day": 140_000,
        "established_date": "2023",
        "fixed_stats": {
            "facility_health": 91,
            "saved_liters_today": 168_500,
            "tariff_savings_monthly_inr": 2_274_750,
            "sla_compliance_pct": 98.7,
            "active_incidents": 3,
        }
    }
}


def get_airport_list(store) -> List[Dict[str, Any]]:
    """Returns the list of monitored airport facilities with live and federated metrics."""
    pnq_health = views.facility_health_hierarchy(store)
    pnq_saved = getattr(store, "saved_month_liters", 38420.0)

    out = []
    # PNQ (Live Twin)
    pnq_data = PORTFOLIO_AIRPORTS["PNQ"].copy()
    pnq_data["facility_health"] = pnq_health["composite_score"]
    pnq_data["saved_liters_today"] = round(pnq_saved / 30.0, 1)
    pnq_data["tariff_savings_monthly_inr"] = round((pnq_saved / 1000.0) * 45.0, 0)
    pnq_data["sla_compliance_pct"] = 98.4
    pnq_data["active_incidents"] = len([a for a in store.alerts if a.status == "OPEN"])
    out.append(pnq_data)

    # BOM & DEL (Federated)
    for code in ("BOM", "DEL"):
        base = PORTFOLIO_AIRPORTS[code].copy()
        stats = base.pop("fixed_stats")
        base.update(stats)
        out.append(base)

    return out


def get_portfolio_summary(store) -> Dict[str, Any]:
    """Computes national portfolio aggregates across all connected airport facilities."""
    airports = get_airport_list(store)

    total_fixtures = sum(a["fixtures_monitored"] for a in airports)
    total_restrooms = sum(a["restrooms_count"] for a in airports)
    total_pax = sum(a["pax_per_day"] for a in airports)
    total_daily_saved = sum(a["saved_liters_today"] for a in airports)
    total_monthly_inr = sum(a["tariff_savings_monthly_inr"] for a in airports)
    avg_health = round(sum(a["facility_health"] for a in airports) / len(airports), 1)

    # Sort rankings by composite health score
    ranked = sorted(airports, key=lambda a: a["facility_health"], reverse=True)
    for rank, ap in enumerate(ranked, 1):
        ap["national_sustainability_rank"] = rank

    return {
        "portfolio_name": "Airports Authority of India (AAI) & GMR Hubs — KOHLER Smart Restroom Fleet",
        "airports_count": len(airports),
        "total_monitored_fixtures": total_fixtures,
        "total_smart_restrooms": total_restrooms,
        "total_daily_passengers": total_pax,
        "consolidated_daily_water_saved_liters": round(total_daily_saved, 1),
        "consolidated_monthly_tariff_savings_inr": round(total_monthly_inr, 0),
        "portfolio_average_health": avg_health,
        "airports": ranked,
    }
