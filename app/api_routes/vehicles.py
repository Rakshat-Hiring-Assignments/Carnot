import logging

from fastapi import APIRouter, HTTPException

from app.utils.vehicle_utils import Vehicles

router = APIRouter()
vehicles = Vehicles()
logger = logging.getLogger(__name__)


@router.get("/vehicles/{device_id}/usage")
async def get_vehicle_usage(device_id: str):
    logger.info("Request received for vehicle usage: %s", device_id)
    usage_data = vehicles.compute_vehicle_usage(device_id)
    if not usage_data:
        logger.warning("Vehicle usage not found for device_id=%s", device_id)
        raise HTTPException(status_code=404, detail=f"Vehicle with device_id {device_id} not found.")

    logger.info("Vehicle usage returned for device_id=%s", device_id)
    return usage_data
