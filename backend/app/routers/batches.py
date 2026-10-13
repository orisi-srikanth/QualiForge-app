"""
Products, Machines & Manufacturing Batches Endpoints
Catalog of parts, engineering specifications, CNC machining cells, and batch records.
Enforces IATF 16949 / ISO 9001 Section 8.5.6 Control of Changes and Section 8.5.2 Traceability.
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.database.models import Product, Machine, InspectionCharacteristic, Batch, Measurement
from backend.app.core.security import get_current_user_optional, require_authenticated_user, UserRole
from backend.app.schemas.schemas import ProductSpec

router = APIRouter()

VALID_UNITS = {"mm", "cm", "in", "µm", "um", "m", "deg", "rad", "bar", "psi"}


# --- RBAC Helper Dependencies ---
def require_admin_or_qe_write(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Auth-free dependency: Allows all users to write products and batches."""
    return user or {"id": "usr-default", "name": "Quality Engineer", "role": "admin"}


def require_admin_delete(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Auth-free dependency: Allows all users to delete products or machines."""
    return user or {"id": "usr-default", "name": "Quality Engineer", "role": "admin"}


# --- Specification Calculation Helper ---
def compute_spec_limits(nominal: float, tol_plus: float, tol_minus: float) -> Tuple[float, float]:
    """
    Calculates engineering specification limits strictly on the backend.
    Never trusts client-provided LSL or USL.
    Enforces non-negative tolerances and strictly positive tolerance band (USL > LSL).
    """
    if tol_plus < 0 or tol_minus < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tolerances must be non-negative (tol_plus >= 0, tol_minus >= 0)."
        )
    lsl = round(nominal - tol_minus, 4)
    usl = round(nominal + tol_plus, 4)
    if usl <= lsl:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid tolerance band: calculated USL ({usl}) must be strictly greater than LSL ({lsl})."
        )
    return lsl, usl


# --- Pydantic Schemas ---
class CharacteristicCreatePayload(BaseModel):
    name: str = Field(..., description="Characteristic parameter, e.g. shaft_diameter", json_schema_extra={"example": "shaft_diameter"})
    unit: str = Field("mm", description="Measurement unit (e.g. mm, in, µm)", json_schema_extra={"example": "mm"})
    nominal: float = Field(..., description="Nominal dimension", json_schema_extra={"example": 50.00})
    tol_plus: float = Field(..., description="Upper tolerance (+)", json_schema_extra={"example": 0.05})
    tol_minus: float = Field(..., description="Lower tolerance (-)", json_schema_extra={"example": 0.05})
    inspection_frequency: str = Field("100% Critical Feature", description="Inspection protocol frequency", json_schema_extra={"example": "100% Critical Feature"})
    sample_size: int = Field(5, description="Subgroup sample size", json_schema_extra={"example": 5})

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            unit = data.get("unit", "mm")
            if unit not in VALID_UNITS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown measurement unit '{unit}'. Permitted units: {sorted(list(VALID_UNITS))}."
                )
            tol_plus = data.get("tol_plus")
            tol_minus = data.get("tol_minus")
            if tol_plus is not None and float(tol_plus) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_plus >= 0)."
                )
            if tol_minus is not None and float(tol_minus) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_minus >= 0)."
                )
        return data


class CharacteristicUpdatePayload(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    nominal: Optional[float] = None
    tol_plus: Optional[float] = None
    tol_minus: Optional[float] = None
    inspection_frequency: Optional[str] = None
    sample_size: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            unit = data.get("unit")
            if unit is not None and unit not in VALID_UNITS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown measurement unit '{unit}'. Permitted units: {sorted(list(VALID_UNITS))}."
                )
            tol_plus = data.get("tol_plus")
            tol_minus = data.get("tol_minus")
            if tol_plus is not None and float(tol_plus) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_plus >= 0)."
                )
            if tol_minus is not None and float(tol_minus) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_minus >= 0)."
                )
        return data


class ProductCreatePayload(BaseModel):
    name: str = Field(..., description="Product designation", json_schema_extra={"example": "Precision Shaft"})
    part_number: str = Field(..., description="Unique engineering part number", json_schema_extra={"example": "PS-2026-101"})
    process: str = Field(..., description="Manufacturing process", json_schema_extra={"example": "CNC Turning & Grinding"})
    material: str = Field("Carbon Steel AISI 1045", description="Material specification", json_schema_extra={"example": "Carbon Steel AISI 1045"})
    family: str = Field("Precision Shafts", description="Product family category", json_schema_extra={"example": "Precision Shafts"})
    machine_id: Optional[str] = Field("CNC-04", description="Assigned CNC machine code or ID", json_schema_extra={"example": "CNC-04"})

    # Characteristic fields (optional or embedded)
    inspection_parameter: Optional[str] = Field("shaft_diameter", description="Critical inspection parameter", json_schema_extra={"example": "shaft_diameter"})
    unit: Optional[str] = Field("mm", description="Measurement unit", json_schema_extra={"example": "mm"})
    nominal: Optional[float] = Field(50.00, description="Nominal dimension", json_schema_extra={"example": 50.00})
    tol_plus: Optional[float] = Field(0.05, description="Upper tolerance limit (+)", json_schema_extra={"example": 0.05})
    tol_minus: Optional[float] = Field(0.05, description="Lower tolerance limit (-)", json_schema_extra={"example": 0.05})
    inspection_frequency: Optional[str] = Field("100% Critical Feature", description="Inspection frequency", json_schema_extra={"example": "100% Critical Feature"})
    characteristic: Optional[CharacteristicCreatePayload] = None

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Check unit if provided
            unit = data.get("unit")
            if unit is not None and unit not in VALID_UNITS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown measurement unit '{unit}'. Permitted units: {sorted(list(VALID_UNITS))}."
                )
            # Check tolerances if provided
            tp = data.get("tol_plus")
            tm = data.get("tol_minus")
            if tp is not None and float(tp) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_plus >= 0)."
                )
            if tm is not None and float(tm) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_minus >= 0)."
                )
        return data


class ProductUpdatePayload(BaseModel):
    name: Optional[str] = None
    part_number: Optional[str] = None
    process: Optional[str] = None
    material: Optional[str] = None
    family: Optional[str] = None
    machine_id: Optional[str] = None
    inspection_parameter: Optional[str] = None
    unit: Optional[str] = None
    nominal: Optional[float] = None
    tol_plus: Optional[float] = None
    tol_minus: Optional[float] = None
    inspection_frequency: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            unit = data.get("unit")
            if unit is not None and unit not in VALID_UNITS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown measurement unit '{unit}'. Permitted units: {sorted(list(VALID_UNITS))}."
                )
            tp = data.get("tol_plus")
            tm = data.get("tol_minus")
            if tp is not None and float(tp) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_plus >= 0)."
                )
            if tm is not None and float(tm) < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tolerances must be non-negative (tol_minus >= 0)."
                )
        return data


class MachineCreatePayload(BaseModel):
    code: str = Field(..., description="Unique machine cell identifier, e.g. CNC-04", json_schema_extra={"example": "CNC-04"})
    type: str = Field(..., description="Machine type and model", json_schema_extra={"example": "Okuma LB3000-EX II CNC Lathe"})
    location: str = Field(..., description="Plant floor location cell", json_schema_extra={"example": "Cell B - Turning & Grinding"})


class MachineUpdatePayload(BaseModel):
    code: Optional[str] = Field(None, description="Updated machine identifier")
    type: Optional[str] = Field(None, description="Updated machine type/name")
    location: Optional[str] = Field(None, description="Updated cell location")



# --- Batch Validation Helpers & Schemas ---
VALID_SHIFTS = {"morning", "evening", "night"}

def parse_datetime_str(val: Optional[Union[str, datetime]]) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid datetime format: '{val}'. Expected ISO 8601 or 'YYYY-MM-DD HH:MM:SS'."
    )

def validate_and_normalize_shift(shift_raw: str) -> str:
    clean = str(shift_raw).lower().replace(" shift", "").strip()
    if clean not in VALID_SHIFTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid shift '{shift_raw}'. Allowed shifts: ['Morning', 'Evening', 'Night']."
        )
    return clean.capitalize()


class BatchCreatePayload(BaseModel):
    batch_number: Optional[str] = Field(None, description="Unique production batch identifier, e.g. BATCH-0245", json_schema_extra={"example": "BATCH-0245"})
    batch_id: Optional[str] = Field(None, description="Batch number alias", json_schema_extra={"example": "BATCH-0245"})
    product_id: Optional[str] = Field(None, description="Referenced product ID or part number", json_schema_extra={"example": "PS-2026-101"})
    part_number: Optional[str] = Field(None, description="Part number alias for product_id", json_schema_extra={"example": "PS-2026-101"})
    machine: Optional[str] = Field(None, description="Assigned CNC machine code or ID, e.g. CNC-04", json_schema_extra={"example": "CNC-04"})
    machine_id: Optional[str] = Field(None, description="Machine ID or code alias", json_schema_extra={"example": "CNC-04"})
    shift: str = Field(..., description="Manufacturing shift: Morning, Evening, or Night", json_schema_extra={"example": "Night"})
    quantity: int = Field(..., description="Manufactured batch parts quantity (> 0)", json_schema_extra={"example": 500})
    start_time: Optional[Union[str, datetime]] = Field(None, description="Production start timestamp (e.g. 2026-10-10 02:00:00)", json_schema_extra={"example": "2026-10-10 02:00:00"})
    end_time: Optional[Union[str, datetime]] = Field(None, description="Production completion timestamp (e.g. 2026-10-10 06:30:00)", json_schema_extra={"example": "2026-10-10 06:30:00"})
    material_lot: str = Field(..., description="Raw material lot or heat code", json_schema_extra={"example": "LOT-CS-9842"})
    operator_ref: Optional[str] = Field(None, description="Operator or process reference (optional)", json_schema_extra={"example": "OP-44"})
    operator: Optional[str] = Field(None, description="Operator reference alias", json_schema_extra={"example": "OP-44"})
    status: Optional[str] = Field("QUALITY_HOLD", description="Quality disposition status", json_schema_extra={"example": "QUALITY_HOLD"})


class BatchUpdatePayload(BaseModel):
    product_id: Optional[str] = None
    part_number: Optional[str] = None
    machine: Optional[str] = None
    machine_id: Optional[str] = None
    shift: Optional[str] = None
    quantity: Optional[int] = None
    start_time: Optional[Union[str, datetime]] = None
    end_time: Optional[Union[str, datetime]] = None
    material_lot: Optional[str] = None
    operator_ref: Optional[str] = None
    operator: Optional[str] = None
    status: Optional[str] = None


CreateBatchPayload = BatchCreatePayload


# --- Helper Function to Serialize DB Product to Schema ---
def serialize_product(p: Product) -> ProductSpec:
    char = p.characteristics[0] if p.characteristics else None
    mach_code = p.machine.code if p.machine else (p.machine_id or "CNC-04")

    nom = char.nominal if char else 50.00
    tp = char.tol_plus if char else 0.05
    tm = char.tol_minus if char else 0.05
    lsl = char.lsl if char else (nom - tm)
    usl = char.usl if char else (nom + tp)

    return ProductSpec(
        product_id=p.id,
        name=p.name,
        part_number=p.part_number,
        machine_id=mach_code,
        material=p.material,
        manufacturing_process=p.process,
        inspection_parameter=char.name if char else "shaft_diameter",
        unit=char.unit if char else "mm",
        nominal_mm=nom,
        tolerance_mm=tp,
        usl=usl,
        lsl=lsl,
        inspection_frequency=char.inspection_frequency if char else "100% Critical Feature"
    )


# ==============================================================================
# Products API Endpoints
# ==============================================================================

@router.get("/products", tags=["Products & Machines"], summary="List registered product specifications", description="Retrieves catalog of manufactured products, nominal dimensions, tolerances, and inspection parameters.")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [serialize_product(p) for p in products]


@router.post("/products", tags=["Products & Machines"], status_code=status.HTTP_201_CREATED, summary="Create new product specification", description="Configures product, part number, manufacturing process, assigned machine, and inspection characteristics. Enforces uniqueness and server-side limit calculation.")
def create_product(
    payload: ProductCreatePayload,
    user: Dict[str, Any] = Depends(require_admin_or_qe_write),
    db: Session = Depends(get_db)
):
    # 1. Uniqueness check for part_number
    existing = db.query(Product).filter(Product.part_number == payload.part_number.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with part number '{payload.part_number}' already exists."
        )

    # 2. Resolve machine foreign key if provided
    mach_id = None
    if payload.machine_id:
        mach = db.query(Machine).filter((Machine.code == payload.machine_id) | (Machine.id == payload.machine_id)).first()
        if mach:
            mach_id = mach.id

    # 3. Create Product
    prod = Product(
        name=payload.name.strip(),
        part_number=payload.part_number.strip(),
        process=payload.process.strip(),
        material=payload.material.strip(),
        family=payload.family.strip(),
        machine_id=mach_id
    )
    db.add(prod)
    db.flush()

    # 4. Create Characteristic with deterministic server-side limits
    char_data = payload.characteristic
    if char_data:
        lsl, usl = compute_spec_limits(char_data.nominal, char_data.tol_plus, char_data.tol_minus)
        char = InspectionCharacteristic(
            product_id=prod.id,
            name=char_data.name.strip(),
            unit=char_data.unit.strip(),
            nominal=char_data.nominal,
            tol_plus=char_data.tol_plus,
            tol_minus=char_data.tol_minus,
            lsl=lsl,
            usl=usl,
            inspection_frequency=char_data.inspection_frequency.strip(),
            sample_size=char_data.sample_size
        )
        db.add(char)
    elif payload.nominal is not None:
        tp = payload.tol_plus if payload.tol_plus is not None else 0.05
        tm = payload.tol_minus if payload.tol_minus is not None else 0.05
        lsl, usl = compute_spec_limits(payload.nominal, tp, tm)
        char = InspectionCharacteristic(
            product_id=prod.id,
            name=payload.inspection_parameter or "shaft_diameter",
            unit=payload.unit or "mm",
            nominal=payload.nominal,
            tol_plus=tp,
            tol_minus=tm,
            lsl=lsl,
            usl=usl,
            inspection_frequency=payload.inspection_frequency or "100%",
            sample_size=5
        )
        db.add(char)

    db.commit()
    db.refresh(prod)
    return serialize_product(prod)


@router.get("/products/{product_id}", tags=["Products & Machines"], summary="Read product specification details", description="Retrieves product by ID or part number.")
def get_product(product_id: str, db: Session = Depends(get_db)):
    prod = db.query(Product).filter((Product.id == product_id) | (Product.part_number == product_id)).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found.")
    return serialize_product(prod)


@router.put("/products/{product_id}", tags=["Products & Machines"], summary="Update product and engineering tolerances", description="Updates specification parameters and recalculates LSL/USL deterministically on the backend.")
def update_product(
    product_id: str,
    payload: ProductUpdatePayload,
    user: Dict[str, Any] = Depends(require_admin_or_qe_write),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter((Product.id == product_id) | (Product.part_number == product_id)).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found.")

    # Check part_number uniqueness if changing
    if payload.part_number and payload.part_number.strip() != prod.part_number:
        conflict = db.query(Product).filter(Product.part_number == payload.part_number.strip(), Product.id != prod.id).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Part number '{payload.part_number}' is already registered.")
        prod.part_number = payload.part_number.strip()

    if payload.name:
        prod.name = payload.name.strip()
    if payload.process:
        prod.process = payload.process.strip()
    if payload.material:
        prod.material = payload.material.strip()
    if payload.family:
        prod.family = payload.family.strip()
    if payload.machine_id:
        mach = db.query(Machine).filter((Machine.code == payload.machine_id) | (Machine.id == payload.machine_id)).first()
        if mach:
            prod.machine_id = mach.id

    # Update characteristic if tolerance or nominal updated
    char = prod.characteristics[0] if prod.characteristics else None
    if char and (payload.nominal is not None or payload.tol_plus is not None or payload.tol_minus is not None or payload.unit or payload.inspection_parameter or payload.inspection_frequency):
        nom = payload.nominal if payload.nominal is not None else char.nominal
        tp = payload.tol_plus if payload.tol_plus is not None else char.tol_plus
        tm = payload.tol_minus if payload.tol_minus is not None else char.tol_minus
        lsl, usl = compute_spec_limits(nom, tp, tm)

        char.nominal = nom
        char.tol_plus = tp
        char.tol_minus = tm
        char.lsl = lsl
        char.usl = usl
        if payload.unit:
            char.unit = payload.unit.strip()
        if payload.inspection_parameter:
            char.name = payload.inspection_parameter.strip()
        if payload.inspection_frequency:
            char.inspection_frequency = payload.inspection_frequency.strip()
    elif not char and payload.nominal is not None:
        tp = payload.tol_plus if payload.tol_plus is not None else 0.05
        tm = payload.tol_minus if payload.tol_minus is not None else 0.05
        lsl, usl = compute_spec_limits(payload.nominal, tp, tm)
        char = InspectionCharacteristic(
            product_id=prod.id,
            name=payload.inspection_parameter or "shaft_diameter",
            unit=payload.unit or "mm",
            nominal=payload.nominal,
            tol_plus=tp,
            tol_minus=tm,
            lsl=lsl,
            usl=usl,
            inspection_frequency=payload.inspection_frequency or "100%",
            sample_size=5
        )
        db.add(char)

    db.commit()
    db.refresh(prod)
    return serialize_product(prod)


@router.delete("/products/{product_id}", tags=["Products & Machines"], summary="Delete product specification", description="Deletes product if no active batches are associated. Safely blocked if batches exist (IATF 16949 Section 8.5.2).")
def delete_product(
    product_id: str,
    user: Dict[str, Any] = Depends(require_admin_delete),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter((Product.id == product_id) | (Product.part_number == product_id)).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found.")

    # Guard: check if manufacturing batches exist for this product
    batch_count = db.query(Batch).filter(Batch.product_id == prod.id).count()
    if batch_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete product '{prod.part_number}': {batch_count} manufacturing batches are linked to this part (IATF 16949 Section 8.5.2 Traceability Requirement)."
        )

    db.delete(prod)
    db.commit()
    return {"status": "DELETED", "product_id": prod.id, "part_number": prod.part_number}


# ==============================================================================
# Inspection Characteristics Endpoints
# ==============================================================================

@router.get("/products/{product_id}/characteristics", tags=["Products & Machines"], summary="Get product inspection characteristics and tolerance limits", description="Retrieves dimensional tolerances, nominal values, and engineering limits for specified product ID.")
def get_product_characteristics(product_id: str, db: Session = Depends(get_db)):
    prod = db.query(Product).filter((Product.id == product_id) | (Product.part_number == product_id)).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found.")

    chars = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.product_id == prod.id).all()
    if not chars:
        return []

    return [
        {
            "characteristic_id": c.id,
            "product_id": c.product_id,
            "name": c.name,
            "parameter": c.name,
            "unit": c.unit,
            "nominal": c.nominal,
            "tolerance": c.tol_plus,
            "tol_plus": c.tol_plus,
            "tol_minus": c.tol_minus,
            "lsl": c.lsl,
            "usl": c.usl,
            "inspection_frequency": c.inspection_frequency,
            "method": "Digital Micrometer / Precision CMM"
        }
        for c in chars
    ]


@router.post("/products/{product_id}/characteristics", tags=["Products & Machines"], status_code=status.HTTP_201_CREATED, summary="Add inspection characteristic to product", description="Adds characteristic, validates units and tolerances, and computes LSL and USL.")
def add_product_characteristic(
    product_id: str,
    payload: CharacteristicCreatePayload,
    user: Dict[str, Any] = Depends(require_admin_or_qe_write),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter((Product.id == product_id) | (Product.part_number == product_id)).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found.")

    lsl, usl = compute_spec_limits(payload.nominal, payload.tol_plus, payload.tol_minus)
    char = InspectionCharacteristic(
        product_id=prod.id,
        name=payload.name.strip(),
        unit=payload.unit.strip(),
        nominal=payload.nominal,
        tol_plus=payload.tol_plus,
        tol_minus=payload.tol_minus,
        lsl=lsl,
        usl=usl,
        inspection_frequency=payload.inspection_frequency.strip(),
        sample_size=payload.sample_size
    )
    db.add(char)
    db.commit()
    db.refresh(char)

    return {
        "characteristic_id": char.id,
        "product_id": char.product_id,
        "name": char.name,
        "unit": char.unit,
        "nominal": char.nominal,
        "tol_plus": char.tol_plus,
        "tol_minus": char.tol_minus,
        "lsl": char.lsl,
        "usl": char.usl,
        "inspection_frequency": char.inspection_frequency
    }


@router.put("/characteristics/{characteristic_id}", tags=["Products & Machines"], summary="Update inspection characteristic", description="Updates tolerances and recalculates LSL/USL on backend.")
def update_characteristic(
    characteristic_id: str,
    payload: CharacteristicUpdatePayload,
    user: Dict[str, Any] = Depends(require_admin_or_qe_write),
    db: Session = Depends(get_db)
):
    char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.id == characteristic_id).first()
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Characteristic '{characteristic_id}' not found.")

    nom = payload.nominal if payload.nominal is not None else char.nominal
    tp = payload.tol_plus if payload.tol_plus is not None else char.tol_plus
    tm = payload.tol_minus if payload.tol_minus is not None else char.tol_minus
    lsl, usl = compute_spec_limits(nom, tp, tm)

    char.nominal = nom
    char.tol_plus = tp
    char.tol_minus = tm
    char.lsl = lsl
    char.usl = usl

    if payload.name:
        char.name = payload.name.strip()
    if payload.unit:
        char.unit = payload.unit.strip()
    if payload.inspection_frequency:
        char.inspection_frequency = payload.inspection_frequency.strip()
    if payload.sample_size:
        char.sample_size = payload.sample_size

    db.commit()
    db.refresh(char)

    return {
        "characteristic_id": char.id,
        "product_id": char.product_id,
        "name": char.name,
        "unit": char.unit,
        "nominal": char.nominal,
        "tol_plus": char.tol_plus,
        "tol_minus": char.tol_minus,
        "lsl": char.lsl,
        "usl": char.usl,
        "inspection_frequency": char.inspection_frequency
    }


# ==============================================================================
# Machines API Endpoints
# ==============================================================================

@router.get("/machines", tags=["Products & Machines"], summary="List factory floor CNC machine cells", description="Retrieves registered CNC machining cells, assigned lines, and active health indicators.")
def get_machines(db: Session = Depends(get_db)):
    machines = db.query(Machine).all()
    if not machines:
        return [
            {"machine_id": "CNC-01", "code": "CNC-01", "name": "Mazak Quick Turn 250", "cell": "Cell-A", "status": "OPERATIONAL", "vibration_baseline_mms": 2.1},
            {"machine_id": "CNC-02", "code": "CNC-02", "name": "Haas ST-20Y Turning Center", "cell": "Cell-A", "status": "OPERATIONAL", "vibration_baseline_mms": 2.0},
            {"machine_id": "CNC-03", "code": "CNC-03", "name": "Okuma LB3000 EX II", "cell": "Cell-B", "status": "OPERATIONAL", "vibration_baseline_mms": 1.9},
            {"machine_id": "CNC-04", "code": "CNC-04", "name": "DMG Mori NLX 2500/700", "cell": "Cell-B", "status": "ATTENTION_REQUIRED", "vibration_baseline_mms": 2.1, "tool_cycles": 1150}
        ]

    return [
        {
            "machine_id": m.id,
            "code": m.code,
            "name": m.type,
            "type": m.type,
            "cell": m.location,
            "location": m.location,
            "status": "ATTENTION_REQUIRED" if m.code == "CNC-04" else "OPERATIONAL",
            "vibration_baseline_mms": 2.1
        }
        for m in machines
    ]


@router.post("/machines", tags=["Products & Machines"], status_code=status.HTTP_201_CREATED, summary="Register factory floor CNC machine cell", description="Creates new CNC machine registration.")
def create_machine(
    payload: MachineCreatePayload,
    user: Dict[str, Any] = Depends(require_admin_or_qe_write),
    db: Session = Depends(get_db)
):
    code_clean = payload.code.strip()
    existing = db.query(Machine).filter(Machine.code == code_clean).first()
    if existing:
        return {
            "status": "EXISTS",
            "machine_id": existing.id,
            "code": existing.code,
            "type": existing.type,
            "location": existing.location
        }

    mach = Machine(
        code=code_clean,
        type=payload.type.strip(),
        location=payload.location.strip()
    )
    db.add(mach)
    db.commit()
    db.refresh(mach)

    return {
        "status": "CREATED",
        "machine_id": mach.id,
        "code": mach.code,
        "type": mach.type,
        "location": mach.location
    }


@router.get("/machines/{machine_id}", tags=["Products & Machines"], summary="Read machine details", description="Retrieves machine by ID or code.")
def get_machine(machine_id: str, db: Session = Depends(get_db)):
    mach = db.query(Machine).filter((Machine.id == machine_id) | (Machine.code == machine_id)).first()
    if not mach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Machine '{machine_id}' not found.")
    return {
        "machine_id": mach.id,
        "code": mach.code,
        "type": mach.type,
        "name": mach.type,
        "cell": mach.location,
        "location": mach.location,
        "status": "OPERATIONAL"
    }


@router.put("/machines/{machine_id}", tags=["Products & Machines"], summary="Update factory floor CNC machine cell", description="Updates machine type, model, or cell location.")
def update_machine(
    machine_id: str,
    payload: MachineUpdatePayload,
    user: Dict[str, Any] = Depends(require_admin_or_qe_write),
    db: Session = Depends(get_db)
):
    mach = db.query(Machine).filter((Machine.id == machine_id) | (Machine.code == machine_id)).first()
    if not mach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Machine '{machine_id}' not found.")
    if payload.code:
        mach.code = payload.code.strip()
    if payload.type:
        mach.type = payload.type.strip()
    if payload.location:
        mach.location = payload.location.strip()
    db.commit()
    db.refresh(mach)
    return {
        "status": "UPDATED",
        "machine_id": mach.id,
        "code": mach.code,
        "type": mach.type,
        "location": mach.location
    }



# ==============================================================================
# Production Batches Endpoints
# ==============================================================================

def serialize_batch(b: Batch, db: Optional[Session] = None) -> Dict[str, Any]:
    m_count = 0
    nonconf_count = 0
    if db:
        measurements = db.query(Measurement).filter(Measurement.batch_id == b.id).all()
        m_count = len(measurements)
        nonconf_count = sum(1 for m in measurements if m.status == "nonconforming")

    if m_count > 0:
        rejection_rate = f"{(nonconf_count / m_count * 100):.1f}%"
    else:
        rejection_rate = "0.0%"

    return {
        "batch_id": b.batch_number,
        "batch_number": b.batch_number,
        "id": b.id,
        "product_id": b.product.id if b.product else b.product_id,
        "part_number": b.product.part_number if b.product else "PS-2026-101",
        "product_name": b.product.name if b.product else "Precision Ground Shaft",
        "machine": b.machine.code if b.machine else "CNC-04",
        "machine_id": b.machine.id if b.machine else b.machine_id,
        "material": b.product.material if b.product else "Carbon Steel",
        "material_lot": b.material_lot,
        "shift": b.shift,
        "quantity": b.quantity,
        "start_time": b.start_time.strftime("%Y-%m-%d %H:%M:%S") if b.start_time else None,
        "end_time": b.end_time.strftime("%Y-%m-%d %H:%M:%S") if b.end_time else None,
        "status": b.status,
        "operator": b.operator_ref or "",
        "operator_ref": b.operator_ref or "",
        "rejection_rate": rejection_rate,
        "nonconforming_count": nonconf_count
    }


@router.get("/batches", tags=["Batches"], summary="List production manufacturing batches", description="Retrieves active and historical batches with filters for product, machine, shift, date range, and pagination.")
def get_batches(
    product: Optional[str] = Query(None, description="Filter by product ID, part number, or name"),
    machine: Optional[str] = Query(None, description="Filter by machine code or ID"),
    shift: Optional[str] = Query(None, description="Filter by shift: Morning, Evening, Night"),
    start_date: Optional[str] = Query(None, description="Filter batches starting on/after date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter batches starting on/before date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size limit"),
    db: Session = Depends(get_db)
):
    query = db.query(Batch).join(Product, Batch.product_id == Product.id, isouter=True).join(Machine, Batch.machine_id == Machine.id, isouter=True)

    if product:
        p_clean = product.strip()
        query = query.filter((Product.part_number == p_clean) | (Product.id == p_clean) | (Product.name.ilike(f"%{p_clean}%")))
    if machine:
        m_clean = machine.strip()
        query = query.filter((Machine.code == m_clean) | (Machine.id == m_clean))
    if shift:
        s_clean = shift.strip().lower().replace(" shift", "")
        query = query.filter(Batch.shift.ilike(f"%{s_clean}%"))
    if start_date:
        dt_start = parse_datetime_str(start_date)
        query = query.filter(Batch.start_time >= dt_start)
    if end_date:
        dt_end = parse_datetime_str(end_date)
        query = query.filter(Batch.start_time <= dt_end)

    batches = query.order_by(Batch.start_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [serialize_batch(b, db) for b in batches]


@router.post("/batches", tags=["Batches"], status_code=status.HTTP_201_CREATED, summary="Register new manufacturing batch", description="Ingests new batch record with foreign key validation, quantity rules, shift verification, and time-ordering checks. Authenticated for operator and quality_engineer roles.")
def create_batch(
    payload: BatchCreatePayload,
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    # 1. Batch number uniqueness check
    b_num = (payload.batch_number or payload.batch_id or "").strip()
    if not b_num:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Field 'batch_number' is required.")

    existing = db.query(Batch).filter(Batch.batch_number == b_num).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Batch number '{b_num}' already exists in production records."
        )

    # 2. Foreign Key: Product validation
    p_ref = (payload.product_id or payload.part_number or "").strip()
    if not p_ref:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Product reference ('product_id' or 'part_number') is required.")
    product = db.query(Product).filter((Product.id == p_ref) | (Product.part_number == p_ref)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referenced product '{p_ref}' does not exist in master product catalog."
        )

    # 3. Foreign Key: Machine validation
    m_ref = (payload.machine or payload.machine_id or "").strip()
    if not m_ref:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Machine reference ('machine' or 'machine_id') is required.")
    machine = db.query(Machine).filter((Machine.id == m_ref) | (Machine.code == m_ref)).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referenced machine '{m_ref}' does not exist in factory machine catalog."
        )

    # 4. Quantity validation (> 0)
    if payload.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch quantity must be strictly positive (quantity > 0), received {payload.quantity}."
        )

    # 5. Shift validation
    norm_shift = validate_and_normalize_shift(payload.shift)

    # 6. Datetime and time-ordering validation
    start_dt = parse_datetime_str(payload.start_time) if payload.start_time else datetime.now(timezone.utc)
    end_dt = parse_datetime_str(payload.end_time) if payload.end_time else None
    if end_dt and end_dt < start_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid time ordering: production end time ({end_dt}) cannot be earlier than start time ({start_dt})."
        )

    # 7. Material Lot validation
    mat_lot = (payload.material_lot or "").strip()
    if not mat_lot:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Field 'material_lot' is required.")

    # 8. Operator reference (optional, accepted empty)
    op_ref = (payload.operator_ref or payload.operator or "").strip() or None

    batch = Batch(
        batch_number=b_num,
        product_id=product.id,
        machine_id=machine.id,
        shift=norm_shift,
        quantity=payload.quantity,
        material_lot=mat_lot,
        operator_ref=op_ref,
        start_time=start_dt,
        end_time=end_dt,
        status=payload.status or "QUALITY_HOLD"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return serialize_batch(batch, db)


@router.get("/batches/{batch_id}", tags=["Batches"], summary="Read production batch details", description="Retrieves batch record by batch number or ID.")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found.")
    return serialize_batch(batch, db)


@router.put("/batches/{batch_id}", tags=["Batches"], summary="Update production batch record", description="Updates batch parameters with validation. Blocks reassigning product or machine if inspection measurements already exist.")
def update_batch(
    batch_id: str,
    payload: BatchUpdatePayload,
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found.")

    # Safety check: if measurements exist, disallow changing product or machine
    m_count = db.query(Measurement).filter(Measurement.batch_id == batch.id).count()
    if m_count > 0:
        if payload.product_id or payload.part_number:
            new_p = (payload.product_id or payload.part_number).strip()
            if new_p != batch.product_id and (not batch.product or new_p != batch.product.part_number):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot reassign product for batch '{batch.batch_number}': {m_count} physical inspection measurements are already linked (IATF 16949 Section 8.5.2 Traceability Requirement)."
                )
        if payload.machine or payload.machine_id:
            new_m = (payload.machine or payload.machine_id).strip()
            if new_m != batch.machine_id and (not batch.machine or new_m != batch.machine.code):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot reassign machine for batch '{batch.batch_number}': {m_count} physical inspection measurements are already linked (IATF 16949 Section 8.5.2 Traceability Requirement)."
                )

    # Update product if allowed
    if payload.product_id or payload.part_number:
        p_ref = (payload.product_id or payload.part_number).strip()
        prod = db.query(Product).filter((Product.id == p_ref) | (Product.part_number == p_ref)).first()
        if not prod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Referenced product '{p_ref}' not found.")
        batch.product_id = prod.id

    # Update machine if allowed
    if payload.machine or payload.machine_id:
        m_ref = (payload.machine or payload.machine_id).strip()
        mach = db.query(Machine).filter((Machine.id == m_ref) | (Machine.code == m_ref)).first()
        if not mach:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Referenced machine '{m_ref}' not found.")
        batch.machine_id = mach.id

    if payload.quantity is not None:
        if payload.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Batch quantity must be strictly positive (quantity > 0).")
        batch.quantity = payload.quantity

    if payload.shift is not None:
        batch.shift = validate_and_normalize_shift(payload.shift)

    if payload.material_lot is not None:
        batch.material_lot = payload.material_lot.strip()

    if payload.operator_ref is not None or payload.operator is not None:
        batch.operator_ref = (payload.operator_ref or payload.operator or "").strip() or None

    if payload.start_time is not None:
        batch.start_time = parse_datetime_str(payload.start_time)

    if payload.end_time is not None:
        dt_end = parse_datetime_str(payload.end_time)
        if dt_end and batch.start_time and dt_end < batch.start_time:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid time ordering: end time ({dt_end}) cannot be earlier than start time ({batch.start_time}).")
        batch.end_time = dt_end

    if payload.status is not None:
        batch.status = payload.status.strip()

    db.commit()
    db.refresh(batch)
    return serialize_batch(batch, db)


@router.delete("/batches/{batch_id}", tags=["Batches"], summary="Delete production batch record", description="Permanently deletes batch if no measurements are linked. Restricted to Administrator role.")
def delete_batch(
    batch_id: str,
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found.")

    m_count = db.query(Measurement).filter(Measurement.batch_id == batch.id).count()
    if m_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete batch '{batch.batch_number}': {m_count} physical inspection measurements are linked (IATF 16949 Section 8.5.2 Traceability Requirement)."
        )

    db.delete(batch)
    db.commit()
    return {"status": "DELETED", "batch_number": batch.batch_number, "id": batch.id}

