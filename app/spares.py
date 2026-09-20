"""KOHLER AquaGuard AI — Genuine OEM Spares & Maintenance Inventory Engine.

Maps physical root-cause classifications to authentic Kohler commercial parts,
tracks depot stock levels across airport terminals, and manages one-click
replacement requisitions.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# Genuine Kohler Commercial Parts Catalog
KOHLER_OEM_CATALOG = {
    "KOHLER-GP1138930": {
        "part_number": "KOHLER-GP1138930",
        "name": "Diaphragm Assembly Repair Kit (Tripoint Flushometer)",
        "category": "Flush Valve",
        "fits_models": ["K-10673", "K-10674", "Wave Flushometer"],
        "unit_cost_inr": 1850.0,
        "description": "High-durability EPDM rubber diaphragm with integrated brass bypass filter orifice. Solves slow leaks and continuous flush cycles.",
        "image_url": "/ui/assets/diaphragm.png",
    },
    "KOHLER-10673-SOL": {
        "part_number": "KOHLER-10673-SOL",
        "name": "24V DC Bi-Stable Pulse Solenoid Actuator",
        "category": "Solenoid Valve",
        "fits_models": ["K-10673", "K-10958", "Touchless Flushometers"],
        "unit_cost_inr": 3450.0,
        "description": "Low-power latching solenoid with encapsulated magnetic core. Solves phantom self-triggering and valve cycling faults.",
        "image_url": "/ui/assets/solenoid.png",
    },
    "KOHLER-K-13688": {
        "part_number": "KOHLER-K-13688",
        "name": "Commercial Infrared Proximity Sensor Eye Module",
        "category": "Sensor Module",
        "fits_models": ["ModernLife Touchless", "Insight Faucets", "K-13460"],
        "unit_cost_inr": 4200.0,
        "description": "Dual-beam adaptive optical sensor eye with conformal anti-moisture coating. Solves false phantom triggers and frozen telemetry.",
        "image_url": "/ui/assets/sensor_eye.png",
    },
    "KOHLER-GP1044432": {
        "part_number": "KOHLER-GP1044432",
        "name": "Dynamic Supply-Line Pressure Regulator & Damper",
        "category": "Pressure Control",
        "fits_models": ["Commercial Restroom Riser System", "Fleet Supply"],
        "unit_cost_inr": 2900.0,
        "description": "Cavitation-resistant brass cartridge regulator stabilizing water hammer and supply surges to 3.0 bar nominal.",
        "image_url": "/ui/assets/regulator.png",
    },
    "KOHLER-GP85160": {
        "part_number": "KOHLER-GP85160",
        "name": "Vandal-Resistant 1.9 LPM Laminar Flow Restrictor",
        "category": "Faucets & Outlets",
        "fits_models": ["K-13460", "K-13461", "Commercial Deck Mount"],
        "unit_cost_inr": 650.0,
        "description": "Multi-mesh laminar flow insert designed for high-traffic public washrooms with limescale resistant silicone face.",
        "image_url": "/ui/assets/aerator.png",
    },
}

# Root-cause to OEM Part Mapping
ROOT_CAUSE_PART_MAPPING = {
    "Flush Valve Diaphragm Tear": "KOHLER-GP1138930",
    "Solenoid Auto-Cycle Leakage": "KOHLER-10673-SOL",
    "Supply-Line Fracture": "KOHLER-GP1044432",
    "Inlet Seal Mechanical Wear": "KOHLER-GP1138930",
    "Telemetry Packet Drop / Frozen": "KOHLER-K-13688",
    "High-Frequency Phantom Cycle": "KOHLER-10673-SOL",
    "Passenger Surge": "KOHLER-GP85160",
}

# Initial Inventory State at Pune Airport Depots
DEPOT_INVENTORY = {
    "Terminal 2 Central Maintenance Depot": {
        "KOHLER-GP1138930": {"in_stock": 18, "min_threshold": 5, "shelf": "Rack B-04"},
        "KOHLER-10673-SOL": {"in_stock": 12, "min_threshold": 4, "shelf": "Rack B-08"},
        "KOHLER-K-13688": {"in_stock": 8, "min_threshold": 3, "shelf": "Electronics Cabinet E-01"},
        "KOHLER-GP1044432": {"in_stock": 6, "min_threshold": 2, "shelf": "Plumbing Bay P-02"},
        "KOHLER-GP85160": {"in_stock": 35, "min_threshold": 10, "shelf": "Consumables Bin C-12"},
    },
    "Terminal 1 Satellite Depot": {
        "KOHLER-GP1138930": {"in_stock": 6, "min_threshold": 3, "shelf": "T1-Cabinet 2"},
        "KOHLER-10673-SOL": {"in_stock": 4, "min_threshold": 2, "shelf": "T1-Cabinet 3"},
        "KOHLER-K-13688": {"in_stock": 3, "min_threshold": 2, "shelf": "T1-Electronics"},
        "KOHLER-GP1044432": {"in_stock": 2, "min_threshold": 1, "shelf": "T1-Heavy Spares"},
        "KOHLER-GP85160": {"in_stock": 15, "min_threshold": 5, "shelf": "T1-Consumables"},
    },
}

# In-memory requisitions ledger
REQUISITIONS: List[Dict[str, Any]] = []


class RequisitionRequest(BaseModel):
    incident_id: str
    device_id: str
    part_number: str
    quantity: int = 1
    depot: str = "Terminal 2 Central Maintenance Depot"
    technician: str = "Priya Sharma"
    urgency: str = "P1 Urgent"


def get_part_for_incident(root_cause: str) -> Dict[str, Any]:
    """Resolves genuine Kohler part information and availability for an incident root cause."""
    part_num = ROOT_CAUSE_PART_MAPPING.get(root_cause, "KOHLER-GP1138930")
    part = KOHLER_OEM_CATALOG.get(part_num, KOHLER_OEM_CATALOG["KOHLER-GP1138930"]).copy()

    # Query depot availability
    depot_stock = DEPOT_INVENTORY["Terminal 2 Central Maintenance Depot"].get(part_num, {"in_stock": 0, "shelf": "General Bay"})
    part["in_stock"] = depot_stock["in_stock"]
    part["shelf_location"] = depot_stock["shelf"]
    part["depot_name"] = "Terminal 2 Central Maintenance Depot"
    part["availability_status"] = "IN_STOCK" if depot_stock["in_stock"] > 0 else "BACKORDER"

    return part


def create_requisition(req: RequisitionRequest) -> Dict[str, Any]:
    """Generates an official maintenance parts requisition and reserves inventory."""
    part = KOHLER_OEM_CATALOG.get(req.part_number)
    if not part:
        raise ValueError(f"Unknown Kohler part number: {req.part_number}")

    depot = DEPOT_INVENTORY.get(req.depot, DEPOT_INVENTORY["Terminal 2 Central Maintenance Depot"])
    stock_entry = depot.get(req.part_number)

    if stock_entry and stock_entry["in_stock"] >= req.quantity:
        stock_entry["in_stock"] -= req.quantity
        status = "ALLOCATED"
    else:
        status = "PENDING_SUPPLIER_DELIVERY"

    req_record = {
        "requisition_id": f"REQ-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        "incident_id": req.incident_id,
        "device_id": req.device_id,
        "part_number": req.part_number,
        "part_name": part["name"],
        "quantity": req.quantity,
        "unit_cost_inr": part["unit_cost_inr"],
        "total_cost_inr": part["unit_cost_inr"] * req.quantity,
        "depot": req.depot,
        "shelf_location": stock_entry.get("shelf", "Bay 1") if stock_entry else "N/A",
        "remaining_depot_stock": stock_entry.get("in_stock", 0) if stock_entry else 0,
        "technician": req.technician,
        "urgency": req.urgency,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    REQUISITIONS.append(req_record)
    return req_record


def get_all_inventory() -> Dict[str, Any]:
    """Returns complete depot inventory snapshot and active requisitions."""
    return {
        "depots": DEPOT_INVENTORY,
        "catalog": KOHLER_OEM_CATALOG,
        "requisitions": REQUISITIONS,
    }
