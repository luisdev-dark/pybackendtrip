from pydantic import BaseModel, field_serializer
from typing import Optional, Literal
from uuid import UUID

class TripCreate(BaseModel):
    route_id: str
    pickup_stop_id: Optional[str] = None
    dropoff_stop_id: Optional[str] = None
    payment_method: Literal["cash", "yape", "plin"]


class TripOut(BaseModel):
    id: UUID
    route_id: UUID
    passenger_id: UUID
    pickup_stop_id: Optional[UUID]
    dropoff_stop_id: Optional[UUID]
    status: str
    payment_method: str
    price_cents: int
    currency: str

    class Config:
        from_attributes = True
    
    @field_serializer('id', 'route_id', 'passenger_id', 'pickup_stop_id', 'dropoff_stop_id')
    def serialize_uuid(self, v: Optional[UUID]) -> Optional[str]:
        return str(v) if v else None
