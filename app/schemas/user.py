from pydantic import BaseModel
from typing import Literal

class UserOut(BaseModel):
    id: str
    role: Literal["passenger", "driver", "admin"]
    full_name: str
    phone_e164: str
    is_active: bool

    class Config:
        from_attributes = True
