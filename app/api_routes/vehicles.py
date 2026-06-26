from fastapi import APIRouter, HTTPException

from app.utils.vehicle_usage import VehicleNotFoundError, compute_vehicle_usage

router = APIRouter()

@router.get("/vehicles/{device_id}/usage")
async def get_vehicle_usage(device_id: str):
    try:
        return compute_vehicle_usage(device_id)
    except VehicleNotFoundError:
        raise HTTPException(status_code=404, detail=f"Vehicle {device_id} not found")
