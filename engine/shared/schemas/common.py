from pydantic import BaseModel
from datetime import datetime

class ErrorResponse(BaseModel):
    success: bool
    status_code: int
    error_code: str
    message: str
    timestamp: datetime
