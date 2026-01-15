from sqlalchemy import Column, String, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.models.base import Base

class TripStatus(str, enum.Enum):
    requested = "requested"
    confirmed = "confirmed"
    started = "started"
    finished = "finished"
    cancelled = "cancelled"

class PaymentMethod(str, enum.Enum):
    cash = "cash"
    yape = "yape"
    plin = "plin"

class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("app.routes.id"), nullable=False)
    passenger_id = Column(UUID(as_uuid=True), ForeignKey("app.users.id"), nullable=False)
    pickup_stop_id = Column(UUID(as_uuid=True), ForeignKey("app.route_stops.id"), nullable=True)
    dropoff_stop_id = Column(UUID(as_uuid=True), ForeignKey("app.route_stops.id"), nullable=True)

    status = Column(Enum(TripStatus, name="trip_status", schema="app"), nullable=False, default=TripStatus.requested)
    payment_method = Column(Enum(PaymentMethod, name="payment_method", schema="app"), nullable=False, default=PaymentMethod.cash)
    price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="PEN")
