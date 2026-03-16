from supabase_auth import BaseModel, Optional

class EmployeeCreate(BaseModel):
    employeeId: int
    name: str
    surname: str
    password: str
    isAdmin: bool

class EmployeeLogin(BaseModel):
    emId: int
    password: str

class VerifyPasswordRequest(BaseModel):
    emId: int
    password: str

class EmployeeUpdate(BaseModel):
    EmName: str
    EmSurName: str
    IsAdmin: bool
    EmPass: Optional[str] = None