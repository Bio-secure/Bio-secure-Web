import datetime
from fastapi import HTTPException
from configs.settings import supabase, pwd_context
from models.employee_models import EmployeeCreate, EmployeeLogin, EmployeeUpdate, VerifyPasswordRequest

def list_employees_service(page: int = 1, page_size: int = 10):
    try:
        # Count total employees
        count_response = supabase.table("Employees").select("EmID", count="exact").execute()
        total = count_response.count or 0

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size - 1

        response = (
            supabase.table("Employees")
            .select("EmID, EmName, EmSurName, IsAdmin")
            .range(start, end)
            .execute()
        )

        return {
            "data": response.data or [],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        print(f"❌ Error fetching employees: {e}")
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
        # Query by Employee ID
        response = (
            supabase.table("Employees")
            .select("EmID, EmPass, IsAdmin, EmName, EmSurName")
            .eq("EmID", employee_login_data.emId)
            .single()
            .execute()
        )

        log_payload = {
            "Employee_ID": employee_login_data.emId,
            "EmResult": "Failure"
        }

        # Case 1: Employee ID not found
        if not response.data:
            log_payload["Error"] = "Employee ID not found"
            supabase.table("EmployeeLogs").insert(log_payload).execute()
            raise HTTPException(status_code=404, detail="Employee ID not found.")

        employee = response.data
        log_payload["EmName"] = employee.get("EmName")
        log_payload["EmSurName"] = employee.get("EmSurName")

        # Case 2: Wrong password
        if not pwd_context.verify(employee_login_data.password, employee["EmPass"]):
            log_payload["Error"] = "Wrong password"
            supabase.table("EmployeeLogs").insert(log_payload).execute()
            raise HTTPException(status_code=401, detail="Incorrect password.")

        # Case 3: Success
        log_payload["EmResult"] = "Success"
        supabase.table("EmployeeLogs").insert(log_payload).execute()

        return {
            "success": True,
            "message": "Login successful!",
            "emId": employee["EmID"],
            "isAdmin": employee["IsAdmin"],
            "name": employee["EmName"],
            "surname": employee["EmSurName"],
        }

    except HTTPException:
        raise  # re-raise clean HTTP errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during login: {str(e)}")


def verify_password_service(payload: VerifyPasswordRequest):
    response = supabase.table("Employees").select("EmPass").eq("EmID", payload.emId).single().execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    hashed = response.data["EmPass"]

    # use the existing module-level pwd_context
    if not pwd_context.verify(payload.password, hashed):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    return {"valid": True}

def update_employee_service(em_id: int, employee: EmployeeUpdate):
    # Build update payload (only non-null fields)
    update_data = {k: v for k, v in employee.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")
    
    if "EmPass" in update_data:
        # Hash password using the same pwd_context as registration
        update_data["EmPass"] = pwd_context.hash(update_data["EmPass"])

    # Update employee in Supabase
    response = supabase.table("Employees").update(update_data).eq("EmID", em_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {"message": "Employee updated successfully", "data": response.data}

def delete_employee_service(em_id: int):
    response = supabase.table("Employees").delete().eq("EmID", em_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Employees not found")
    
    return {"message": "Employees deleted successfully"}

