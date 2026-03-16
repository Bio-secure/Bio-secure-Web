from typing import Literal
from pydantic import Field
from supabase_auth import BaseModel, Optional


class TransactionCreate(BaseModel):
    customer_id: int
    employee_id: int
    transaction_type: Literal['deposit', 'withdrawal'] 
    amount: float = Field(..., gt=0) 
    note: Optional[str] = None