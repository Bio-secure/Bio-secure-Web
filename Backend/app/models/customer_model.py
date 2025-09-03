from typing import Optional
from supabase_auth import BaseModel


class CustomerUpdate(BaseModel):
    Name: Optional[str] = None
    SurName: Optional[str] = None
    BirthDate: Optional[str] = None
    phone_no: Optional[int] = None