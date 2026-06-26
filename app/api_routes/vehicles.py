from fastapi import APIRouter, HTTPException

from app.utils.vehicle_utils import Vehicles

router = APIRouter()
vehicles = Vehicles()

@router.get("/vehicles/{device_id}/usage")
async def get_vehicle_usage(device_id: str):
    usage_data = vehicles.compute_vehicle_usage(device_id)
    if not usage_data:
        raise HTTPException(status_code=404, detail=f"Vehicle with device_id {device_id} not found.")
    return usage_data
