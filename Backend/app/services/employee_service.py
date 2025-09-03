import datetime
from fastapi import HTTPException
from configs.settings import supabase, pwd_context
from models.employee_models import EmployeeCreate, EmployeeLogin, VerifyPasswordRequest

def list_employees_service():
    try:
        response = supabase.table("Employees").select("*").execute()
        return response.data or []
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch Employees.")


def register_employee_service(employee_data: EmployeeCreate):
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        hashed_password = pwd_context.hash(employee_data.password)
        payload = {
            "EmID": employee_data.employeeId, "EmName": employee_data.name,
            "EmSurName": employee_data.surname, "IsAdmin": employee_data.isAdmin,
            "FDW": now_utc.isoformat(), "EmPass": hashed_password
        }
        response = supabase.table("Employees").insert([payload]).execute()
        return {"message": "Employee registered successfully!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def login_employee_service(employee_login_data: EmployeeLogin):
    try:
        response = supabase.table("Employees").select("EmID, EmPass, IsAdmin, EmName, EmSurName").eq("EmID", employee_login_data.emId).single().execute()
        log_payload = {"Employee_ID": employee_login_data.emId, "EmResult": "Failure"}

        if not response.data:
            supabase.table("EmployeeLogs").insert(log_payload).execute()
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        
        employee = response.data
        log_payload["EmName"] = employee.get("EmName")
        log_payload["EmSurName"] = employee.get("EmSurName")

        if not pwd_context.verify(employee_login_data.password, employee["EmPass"]):
            supabase.table("EmployeeLogs").insert(log_payload).execute()
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        
        log_payload["EmResult"] = "Success"
        supabase.table("EmployeeLogs").insert(log_payload).execute()
        
        return {
            "success": True, "message": "Login successful!", "emId": employee["EmID"],
            "isAdmin": employee["IsAdmin"], "name": employee["EmName"], "surname": employee["EmSurName"]
        }
    except Exception as e:
        if 'log_payload' in locals():
            supabase.table("EmployeeLogs").insert(log_payload).execute()
        raise HTTPException(status_code=500, detail=f"An unexpected error during login: {str(e)}")

def verify_password_service(payload: VerifyPasswordRequest):
    response = supabase.table("Employees").select("EmPass").eq("EmID", payload.emId).single().execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    hashed = response.data["EmPass"]
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    if not pwd_context.verify(payload.password, hashed):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    return {"valid": True}