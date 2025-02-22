from fastapi import APIRouter
from . import validate

router = APIRouter()

router.include_router(validate.router)