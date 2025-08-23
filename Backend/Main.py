import json
import os
import shutil
import datetime
import traceback
from typing import Literal, Optional
import uuid
import math
from rich import _console
import scipy.ndimage
import numpy as np
import cv2
import base64
from PIL import Image
import io
import requests

from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, BackgroundTasks, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from scipy.spatial.distance import cosine

import httpx

from postgrest.exceptions import APIError as PostgrestAPIError
from utils.email_utils import send_authentication_report_email
from iris_model_apis import authenticate_iris

# Define Pydantic models
class EmployeeCreate(BaseModel):
    employeeId: int
    name: str
    surname: str
    password: str
    isAdmin: bool

class EmployeeLogin(BaseModel):
    emId: int
    password: str

class IrisAuthentication(BaseModel): 
    user_id: str | None = None 
    image_data: str 

class IrisAuthResponse(BaseModel):
    message: str
    user_id: str | None = None
    is_authenticated: bool | None = None
    similarity: float | None = None
    matched_user_id: str | None = None
    best_similarity: float | None = None
    detail: str | None = None

# Authentication thresholds
FACE_DISTANCE_THRESHOLD = 0.50
IRIS_AUTHENTICATION_THRESHOLD = 0.65

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    from deepface import DeepFace
except ImportError:
    print("DeepFace not found. Facial recognition features will be unavailable.")
    DeepFace = None

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IRIS_MODEL_API_URL = os.getenv("IRIS_MODEL_API_URL", "http://localhost:8081")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL and Key must be set in .env file or environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

origins = [
    "http://localhost:5173", 
    "http://127.0.0.1:5173", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TransactionCreate(BaseModel):
    customer_id: int
    employee_id: int
    transaction_type: Literal['deposit', 'withdrawal'] 
    amount: float = Field(..., gt=0) 
    note: Optional[str] = None

BIOMETRIC_BUCKET = os.getenv("BIOMETRIC_BUCKET")

async def authenticate_iris_from_api(user_id: str, image_data_b64: str) -> dict:
    headers = {"Content-Type": "application/json"}
    payload = {"user_id": user_id, "image_data": image_data_b64}
    response = None
    try:
        response = requests.post(f"{IRIS_MODEL_API_URL}/authenticate-iris", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Iris Model API's /authenticate-iris: {e}")
        if response is not None and response.text:
            try:
                error_detail = response.json().get("detail", response.text)
            except json.JSONDecodeError:
                error_detail = response.text
            raise HTTPException(status_code=response.status_code, detail=f"Iris API error: {error_detail}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to communicate with Iris API: {e}")
        
async def authenticate_face_from_api(customer_id: int, face_image_path: str):
    try:
        embedding_objs = DeepFace.represent(
            img_path=face_image_path,
            model_name="VGG-Face",
            enforce_detection=True
        )
        if not embedding_objs:
             return {
                "is_authenticated": False,
                "message": "Could not find a face in the provided image."
            }
        uploaded_face_embedding = embedding_objs[0]['embedding']

        db_response = supabase.table('Biometric').select('face_embedding, face_image_url').eq('National_ID', customer_id).single().execute()

        if not db_response.data or not db_response.data.get('face_embedding'):
            return {
                "is_authenticated": False,
                "message": "No registered face biometric data found for this customer."
            }

        stored_face_embedding_data = db_response.data.get('face_embedding')
        match_face_image_url = db_response.data.get('face_image_url')

        # --- THIS IS THE ROBUST CHANGE ---
        # It handles data stored as a string (old) or as a list/jsonb (new)
        if isinstance(stored_face_embedding_data, str):
            stored_face_embedding = json.loads(stored_face_embedding_data)
        else:
            stored_face_embedding = stored_face_embedding_data

        distance = cosine(uploaded_face_embedding, stored_face_embedding)
        is_match = bool(distance < FACE_DISTANCE_THRESHOLD)

        return {
            "is_authenticated": is_match,
            "distance": float(distance) if distance is not None else None,
            "image_url": match_face_image_url,
            "message": "Face Verified Successfully" if is_match else "Face Verification Failed"
        }

    except Exception as e:
        return {
            "is_authenticated": False,
            "message": f"Face verification error: {e}",
            "detail": str(e)
        }

@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

@app.post("/register-biometric")
async def register_biometric(
    national_id: str = Form(...),
    face_image: UploadFile = File(...),
    iris_image: UploadFile = File(None)
):
    if not DeepFace:
        raise HTTPException(status_code=503, detail="Facial recognition service is not available.")

    # --- NEW: Fetch customer name from the database first ---
    try:
        customer_response = supabase.table("Customer").select("Name, SurName").eq("National_ID", int(national_id)).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail=f"Customer with National ID {national_id} not found.")
        
        customer_name = customer_response.data.get("Name", "")
        customer_surname = customer_response.data.get("SurName", "")
        # Create a clean, URL-safe version of the name for the filename
        sanitized_full_name = f"{customer_name}_{customer_surname}".replace(" ", "_")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching customer details: {e}")

    # --- FILENAME LOGIC UPDATED ---
    face_ext = face_image.filename.split('.')[-1]
    face_filename = f"face/{national_id}_{sanitized_full_name}.{face_ext}" # <-- UPDATED
    face_image_path = os.path.join(f"{national_id}_face_temp.{face_ext}")

    face_image_url = None
    face_embedding = None

    try:
        with open(face_image_path, "wb") as buffer:
            shutil.copyfileobj(face_image.file, buffer)
        
        embedding_objs = DeepFace.represent(img_path=face_image_path, model_name="VGG-Face", enforce_detection=False)
        if not embedding_objs or 'embedding' not in embedding_objs[0]:
            raise HTTPException(status_code=400, detail="Could not generate a face embedding.")
        face_embedding = embedding_objs[0]['embedding']

        with open(face_image_path, "rb") as f:
            supabase.storage.from_(BIOMETRIC_BUCKET).upload(file=f, path=face_filename, file_options={"upsert": "true"})
        
        face_image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(face_filename)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing face image or uploading to storage: {e}")
    finally:
        if os.path.exists(face_image_path):
            os.remove(face_image_path)

    iris_image_url = None
    iris_embedding = None

    if iris_image:
        # --- FILENAME LOGIC UPDATED ---
        iris_ext = iris_image.filename.split('.')[-1]
        iris_filename = f"iris/{national_id}_{sanitized_full_name}.{iris_ext}" # <-- UPDATED
        temp_iris_image_path = os.path.join(f"{national_id}_iris_temp.{iris_ext}")
        
        try:
            with open(temp_iris_image_path, "wb") as buffer:
                shutil.copyfileobj(iris_image.file, buffer)

            with open(temp_iris_image_path, "rb") as f_read:
                iris_b64 = base64.b64encode(f_read.read()).decode('utf-8')

            async with httpx.AsyncClient() as client:
                iris_embedding_response = await client.post(
                    f"{IRIS_MODEL_API_URL}/get-iris-embedding",
                    json={"image_data": iris_b64},
                    timeout=30.0
                )
                iris_embedding_response.raise_for_status()
                iris_embedding_data = iris_embedding_response.json()
                iris_embedding = iris_embedding_data.get("embedding")
                if not iris_embedding:
                    raise ValueError("Iris API returned no embedding.")

            with open(temp_iris_image_path, "rb") as f_upload:
                supabase.storage.from_(BIOMETRIC_BUCKET).upload(file=f_upload, path=iris_filename, file_options={"upsert": "true"})
            iris_image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(iris_filename)
        except Exception as e:
            traceback.print_exc()
        finally:
            if os.path.exists(temp_iris_image_path):
                os.remove(temp_iris_image_path)
    
    try:
        payload = {
            "National_ID": int(national_id),
            "face_image_url": face_image_url,
            "face_embedding": json.dumps(face_embedding),
            "iris_image_url": iris_image_url,
            "iris_embedding": json.dumps(iris_embedding) if iris_embedding is not None else None
        }
        supabase.table("Biometric").upsert(payload, on_conflict="National_ID").execute()
        return {"message": f"Biometric data registered successfully for ID {national_id}."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during database insertion: {e}")

@app.post("/verify")
async def verify_customer_identity(
    background_tasks: BackgroundTasks,
    face_image: UploadFile = File(None),
    iris_image: UploadFile = File(None),
    customer_id: int = Form(...)
):
    """
    Verifies a customer's identity and ONLY LOGS FAILURES.
    Successful verifications are logged by the subsequent transaction.
    """
    if not face_image and not iris_image:
        raise HTTPException(status_code=400, detail="At least one of face_image or iris_image must be provided.")

    # --- Step 1: Find the customer FIRST ---
    customer_name = "Unknown"
    customer_surname = "Customer"
    customer_email = None
    try:
        customer_response = supabase.table("Customer").select("Name, SurName, Email").eq("National_ID", customer_id).single().execute()
        if not customer_response.data:
            log_payload = {
                "Customer_National_ID": customer_id, "Name": "Biometric Auth Failure",
                "SurName": "Customer Not Found", "Result": False,
                "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            supabase.table("CustomerLogs").insert([log_payload]).execute()
            raise HTTPException(status_code=404, detail="Customer not found for verification.")
        
        customer_data = customer_response.data
        customer_email = customer_data.get('Email')
        customer_name = customer_data.get('Name') or "Unknown"
        customer_surname = customer_data.get('SurName') or "Customer"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error while finding customer: {e}")

    # (Biometric processing logic is unchanged)
    # --- Step 2: Proceed with biometric verification ---
    face_is_match = False
    iris_is_match = False
    face_details = {}
    iris_details = {}
    if face_image:
        face_image_path = os.path.join(f"{customer_id}_face_query.jpg")
        try:
            with open(face_image_path, "wb") as buffer:
                shutil.copyfileobj(face_image.file, buffer)
            face_auth_response = await authenticate_face_from_api(customer_id, face_image_path)
            face_is_match = face_auth_response.get("is_authenticated", False)
            face_details = face_auth_response
        finally:
            if os.path.exists(face_image_path): os.remove(face_image_path)
    if iris_image:
        iris_image_path = os.path.join(f"{customer_id}_iris_query.jpg")
        try:
            with open(iris_image_path, "rb") as f:
                iris_image_b64 = base64.b64encode(f.read()).decode('utf-8')
            iris_auth_response = await authenticate_iris_from_api(str(customer_id), iris_image_b64)
            iris_is_match = iris_auth_response.get("is_authenticated", False)
            iris_details = iris_auth_response
        finally:
            if os.path.exists(iris_image_path): os.remove(iris_image_path)

    # --- Step 3: Determine Overall Result ---
    overall_verified = False
    if face_image and iris_image:
        overall_verified = face_is_match and iris_is_match
    elif face_image:
        overall_verified = face_is_match
    elif iris_image:
        overall_verified = iris_is_match

    # --- Step 4: Log the result ONLY IF verification FAILED ---
    if not overall_verified:
        log_payload_for_db = {
            "Customer_National_ID": customer_id, "Name": customer_name,
            "SurName": customer_surname, "Result": False,
            "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        supabase.table("CustomerLogs").insert([log_payload_for_db]).execute()

    # --- Step 5: Send email and return response ---
    if customer_email:
        # --- THIS LINE IS NOW RE-ENABLED ---
        final_log_details = {"face_verification": face_details, "iris_authentication": iris_details}
        biometric_type = " and ".join(filter(None, [face_image and "face", iris_image and "iris"]))
        background_tasks.add_task(send_authentication_report_email, customer_email, f"{customer_name} {customer_surname}".strip(), biometric_type, overall_verified, final_log_details)
    
    response_message = "Verification " + ("Succeeded" if overall_verified else "Failed")
    return { "verified": overall_verified, "message": response_message, "details": { "face": face_details, "iris": iris_details } }

@app.get("/customer-details/{customer_id}")
async def get_customer_details(customer_id: int):
    try:
        customer_response = supabase.table("Customer").select("*").eq("National_ID", customer_id).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer_data = customer_response.data
        
        try:
            biometric_response = supabase.table("Biometric").select("face_image_url").eq("National_ID", customer_id).single().execute()
            customer_data['face_image_url'] = biometric_response.data['face_image_url'] if biometric_response.data else None
        except Exception:
            customer_data['face_image_url'] = None
        
        transactions_response = supabase.table("Transactions") \
            .select("id, created_at, transaction_type, amount, note, employee_id") \
            .eq("customer_id", customer_id) \
            .order("created_at", desc=True) \
            .limit(15) \
            .execute()

        enriched_transactions = []
        if transactions_response.data:
            for tx in transactions_response.data:
                employee_name = "System"
                if tx.get("employee_id"):
                    try:
                        employee_response = supabase.table("Employees").select("EmName, EmSurName").eq("EmID", tx["employee_id"]).single().execute()
                        if employee_response.data:
                            emp = employee_response.data
                            employee_name = f"{emp['EmName']} {emp['EmSurName']}"
                    except Exception:
                        employee_name = "Unknown Employee"
                tx["employee_name"] = employee_name
                enriched_transactions.append(tx)

        customer_data['transactions'] = enriched_transactions
        return customer_data
    except Exception as e:
        print(f"Error fetching customer details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customer details.")

@app.get("/customers")
async def list_customers():
    try:
        response = supabase.table("Customer").select("National_ID, Name, SurName, phone_no, Email").execute()
        if not response.data:
            return []
        return response.data
    except Exception as e:
        print(f"❌ Error fetching customers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customers.")
    
@app.get("/employees")
async def list_employees():
    try: 
        response = supabase.table("Employees").select("*").execute()
        if not response.data:
            return []
        return response.data
    except Exception as e: 
        raise HTTPException(status_code=500, detail="Failed to fetch Employees.") 

@app.post("/register-employee")
async def register_employee(employee_data: EmployeeCreate):
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

@app.post("/login-employee")
async def login_employee(employee_login_data: EmployeeLogin):
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

@app.post("/register-user")
async def register_user(user_data: dict):
    try:
        balance_value = float(user_data.get("balance")) if str(user_data.get("balance", "")).strip() else None
        payload = {
            "National_ID": int(user_data.get("nationalId")) if user_data.get("nationalId") else None,
            "Name": user_data.get("firstName"), "SurName": user_data.get("lastName"),
            "BirthDate": user_data.get("birthDate"),
            "phone_no": int(user_data.get("phoneNo")) if user_data.get("phoneNo") else None,
            "Gender": user_data.get("gender"), "DOR": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Email": user_data.get("email") or None, "Balance": balance_value,
        }
        response = supabase.table("Customer").insert([payload]).execute()
        return {"message": "User registered successfully!", "data": response.data or []}
    except (ValueError, TypeError) as ve:
        raise HTTPException(status_code=400, detail=f"Invalid data format: {ve}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.post("/transaction")
async def create_transaction(transaction: TransactionCreate):
    is_successful = True
    failure_reason = ""
    http_status_code = 200

    customer_response = supabase.table("Customer") \
        .select("Name", "SurName", "Balance") \
        .eq("National_ID", transaction.customer_id) \
        .single().execute()

    if not customer_response.data:
        is_successful = False
        failure_reason = "Customer Not Found"
        http_status_code = 404
    else:
        current_balance = customer_response.data.get('Balance') or 0
        if transaction.transaction_type == 'withdrawal' and current_balance < transaction.amount:
            is_successful = False
            failure_reason = "Insufficient Funds"
            http_status_code = 400

    if is_successful:
        customer_data = customer_response.data
        customer_name = customer_data.get("Name", "N/A")
        customer_surname = customer_data.get("SurName", "N/A")
        current_balance = customer_data.get('Balance') or 0

        new_balance = (current_balance - transaction.amount) if transaction.transaction_type == 'withdrawal' else (current_balance + transaction.amount)

        supabase.table("Customer").update({"Balance": new_balance}).eq("National_ID", transaction.customer_id).execute()
        
        transaction_record = {
            "customer_id": transaction.customer_id, "employee_id": transaction.employee_id,
            "transaction_type": transaction.transaction_type, "amount": transaction.amount,
            "note": transaction.note, "balance_after": new_balance
        }
        supabase.table("Transactions").insert(transaction_record).execute()

        supabase.table("CustomerLogs").insert([{"Customer_National_ID": transaction.customer_id, "Name": customer_name, "SurName": customer_surname, "Result": True, "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}]).execute()
        
        return JSONResponse(status_code=200, content={"message": f"{transaction.transaction_type.capitalize()} successful!", "new_balance": new_balance})
    
    else:
        log_payload = {"Customer_National_ID": transaction.customer_id, "Result": False, "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if failure_reason == "Customer Not Found":
            log_payload["Name"] = "Unknown"
            log_payload["SurName"] = "Customer"
        elif failure_reason == "Insufficient Funds":
            log_payload["Name"] = customer_response.data.get("Name", "N/A")
            log_payload["SurName"] = customer_response.data.get("SurName", "N/A")
        supabase.table("CustomerLogs").insert([log_payload]).execute()
        return JSONResponse(status_code=http_status_code, content={"message": failure_reason})

@app.get("/registration-records")
async def get_registration_records():
    try:
        response = supabase.table("Customer").select("National_ID, Name, SurName, DOR, Balance").order("DOR", desc=True).execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/registration-stats")
async def get_registration_stats():
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - datetime.timedelta(days=today_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        today_count = supabase.table("Customer").select("*", count="exact").gte("DOR", today_start.isoformat()).execute().count
        week_count = supabase.table("Customer").select("*", count="exact").gte("DOR", week_start.isoformat()).execute().count
        month_count = supabase.table("Customer").select("*", count="exact").gte("DOR", month_start.isoformat()).execute().count

        return {"today": today_count, "week": week_count, "month": month_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch registration stats: {e}")

@app.get("/customer-logs")
async def get_customer_logs(show_all: Optional[bool] = Query(False), period: Optional[str] = Query(None)):
    try:
        query = supabase.table("CustomerLogs").select("*").order("Transaction_Timestamp", desc=True)

        # Handle time period filtering
        if period:
            now = datetime.datetime.now(datetime.timezone.utc)
            start_date = None
            if period == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'week':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=now.weekday())
            elif period == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if start_date:
                query = query.gte("Transaction_Timestamp", start_date.isoformat())
        
        # Handle default limit unless show_all is requested
        elif not show_all:
            query = query.limit(15)
            
        response = query.execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch customer logs: {str(e)}")

@app.get("/employee-logs")
async def get_employee_logs(period: Optional[str] = Query(None)):
    try:
        query = supabase.table("EmployeeLogs").select("*").order("Log_Timestamp", desc=True)

        # Handle time period filtering
        if period:
            now = datetime.datetime.now(datetime.timezone.utc)
            start_date = None
            if period == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'week':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=now.weekday())
            elif period == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if start_date:
                # Filter using the 'Log_Timestamp' column
                query = query.gte("Log_Timestamp", start_date.isoformat())
        else:
            # Default to the 10 most recent logs if no period is specified
            query = query.limit(10)

        response = query.execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employee logs: {str(e)}")
    
@app.get("/debug")
async def debug():
    response = supabase.table("Customer").select("*").limit(2).execute()
    print("DEBUG DATA:", response.data)
    return response.data

## Supabase CRUD Utility Endpoints
class CustomerUpdate(BaseModel):
    Name: Optional[str] = None
    SurName: Optional[str] = None
    BirthDate: Optional[str] = None
    phone_no: Optional[int] = None

@app.put("/customers/{customer_id}")
def update_customer(customer_id: int, customer: CustomerUpdate):
    # Build update payload (only non-null fields)
    update_data = {k: v for k, v in customer.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    # Update customer in Supabase
    response = supabase.table("Customer").update(update_data).eq("National_ID", customer_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"message": "Customer updated successfully", "data": response.data}

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int):
    response = supabase.table("Customer").delete().eq("National_ID", customer_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {"message": "Customer deleted successfully"}