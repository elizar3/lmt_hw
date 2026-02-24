# reads data from db and converts into simple Python dicts

from sqlalchemy.orm import Session
from app.models import DefenseBase, Interceptor, BaseInventory

def load_bases(db: Session):
    base_rows = db.query(DefenseBase).all()

    bases = []
    for base in base_rows:
        bases.append({
            "name": base.name,
            "latitude": base.latitude,
            "longitude": base.longitude,
        })
    return bases

def load_inventory_by_base(db: Session):
    inventory = {}

    base_rows = db.query(DefenseBase).all()
    for base in base_rows:
        inventory[base.name] = []
    
    # join base_inventory -> bases -> interceptors
    rows = (
        db.query(DefenseBase.name, Interceptor)
        .join(BaseInventory, BaseInventory.base_id == DefenseBase.id)
        .join(Interceptor, BaseInventory.interceptor_id == Interceptor.id)
        .all()
    )

    for base_name, interceptor in rows:
        inventory[base_name].append({
            "name": interceptor.name,
            "speed_ms": interceptor.speed_ms,
            "range_m": interceptor.range_m,
            "max_altitude_m": interceptor.max_altitude_m,
            "cost_model": interceptor.cost_model,
            "cost_value_eur": interceptor.cost_value_eur,
        })
    return inventory

# convenience function to load in one call
def load_bases_and_inventory(db: Session):
    bases = load_bases(db)
    inventory = load_inventory_by_base(db)
    return bases, inventory