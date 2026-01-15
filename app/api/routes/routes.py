from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_db_session
from app.models.route import Route, RouteStop
from app.schemas.route import RouteSummary, RouteDetail, RouteStopOut

router = APIRouter()

@router.get("", response_model=List[RouteSummary])
async def list_routes(db: AsyncSession = Depends(get_db_session)):
    stmt = select(Route).where(Route.is_active == True)
    result = await db.execute(stmt)
    routes = result.scalars().all()
    return routes

@router.get("/{route_id}", response_model=RouteDetail)
async def get_route_detail(route_id: str, db: AsyncSession = Depends(get_db_session)):
    route_stmt = select(Route).where(Route.id == route_id)
    route_result = await db.execute(route_stmt)
    route = route_result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    stops_stmt = (
        select(RouteStop)
        .where(RouteStop.route_id == route_id, RouteStop.is_active == True)
        .order_by(RouteStop.stop_order)
    )
    stops_result = await db.execute(stops_stmt)
    stops = stops_result.scalars().all()

    return RouteDetail(
        route=route,
        stops=stops,
    )
