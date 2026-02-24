# SQLAlchemy ORM models

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# base locations
class DefenseBase(Base):
    __tablename__ = "bases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

# interceptor data
class Interceptor(Base):
    __tablename__ = "interceptors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    speed_ms = Column(Integer, nullable=False)
    range_m = Column(Integer, nullable=False)
    max_altitude_m = Column(Integer, nullable=False)
    cost_model = Column(String(20), nullable=False)  # "fixed", "per_minute", "per_shot"
    cost_value_eur = Column(Integer, nullable=False)

# inventory of interceptors at each base
class BaseInventory(Base):
    __tablename__ = "base_inventory"

    base_id = Column(Integer, ForeignKey("bases.id"), primary_key=True)
    interceptor_id = Column(Integer, ForeignKey("interceptors.id"), primary_key=True)