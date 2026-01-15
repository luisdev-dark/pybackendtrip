from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base

class Route(Base):
    __tablename__ = "routes"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    origin_name = Column(String, nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    destination_name = Column(String, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lon = Column(Float, nullable=False)
    base_price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="PEN")
    is_active = Column(Boolean, nullable=False, default=True)

    stops = relationship("RouteStop", back_populates="route", order_by="RouteStop.stop_order")


class RouteStop(Base):
    __tablename__ = "route_stops"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("app.routes.id"), nullable=False)
    stop_order = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    route = relationship("Route", back_populates="stops")
