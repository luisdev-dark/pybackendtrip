from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db_session
from app.models.trip import Trip, TripStatus, PaymentMethod
from app.schemas.trip import TripCreate, TripOut

router = APIRouter()

HARDCODED_PASSENGER_ID = "11111111-1111-1111-1111-111111111111"

@router.post("", response_model=TripOut)
async def create_trip(payload: TripCreate, db: AsyncSession = Depends(get_db_session)):
    if payload.pickup_stop_id and payload.dropoff_stop_id and payload.pickup_stop_id == payload.dropoff_stop_id:
        raise HTTPException(status_code=400, detail="pickup_stop_id and dropoff_stop_id must be different")

    trip = Trip(
        route_id=payload.route_id,
        passenger_id=HARDCODED_PASSENGER_ID,
        pickup_stop_id=payload.pickup_stop_id,
        dropoff_stop_id=payload.dropoff_stop_id,
        status=TripStatus.requested,
        payment_method=PaymentMethod(payload.payment_method),
    )

    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip

@router.get("/{trip_id}", response_model=TripOut)
async def get_trip(trip_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip
