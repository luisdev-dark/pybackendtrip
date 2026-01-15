from pydantic import BaseModel, field_serializer
from typing import List
from uuid import UUID

class RouteSummary(BaseModel):
    id: UUID
    name: str
    origin_name: str
    destination_name: str
    base_price_cents: int
    currency: str

    class Config:
        from_attributes = True
    
    @field_serializer('id')
    def serialize_id(self, v: UUID) -> str:
        return str(v)


class RouteStopOut(BaseModel):
    id: UUID
    name: str
    stop_order: int

    class Config:
        from_attributes = True
    
    @field_serializer('id')
    def serialize_id(self, v: UUID) -> str:
        return str(v)


class RouteDetail(BaseModel):
    route: RouteSummary
    stops: List[RouteStopOut]
