import datetime
from fastapi import HTTPException
from configs.settings import supabase

def register_user_service(user_data: dict):
    try:
        balance_value = float(user_data.get("balance")) if str(user_data.get("balance", "")).strip() else None
        payload = {
            "National_ID": int(user_data.get("nationalId")) if user_data.get("nationalId") else None,
            "Name": user_data.get("firstName"), "SurName": user_data.get("lastName"),
            "BirthDate": user_data.get("birthDate"),
            "phone_no": int(user_data.get("phoneNo")) if user_data.get("phoneNo") else None,
            "Gender": user_data.get("gender"),
            "DOR": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Email": user_data.get("email") or None,
            "Balance": balance_value,
        }
        response = supabase.table("Customer").insert([payload]).execute()
        return {"message": "User registered successfully!", "data": response.data or []}
    except (ValueError, TypeError) as ve:
        raise HTTPException(status_code=400, detail=f"Invalid data format: {ve}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
