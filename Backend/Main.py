import json
import os
import shutil
import datetime
import traceback
from typing import Literal, Optional
import uuid
import math # Added for ArcFace
import scipy.ndimage # Added for Daugman normalization
import numpy as np # Already present, but explicitly for iris processing
import cv2 # Added for image processing (OpenCV)
import base64 # Added for image decoding
from PIL import Image # Added for image decoding
import io # Added for image decoding

from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, BackgroundTasks, Body # Added Body for JSON requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from scipy.spatial.distance import cosine # Already present

import httpx

from postgrest.exceptions import APIError as PostgrestAPIError
from utils.email_utils import send_authentication_report_email


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
    user_id: str | None = None # Claimed user_id
    is_authenticated: bool | None = None
    similarity: float | None = None # Similarity to claimed user_id
    matched_user_id: str | None = None # Best matched user_id in open-set
    best_similarity: float | None = None # Best similarity in open-set
    detail: str | None = None

# Authentication threshold (cosine similarity for iris)
AUTHENTICATION_THRESHOLD = 0.30 # Adjust this value based on your desired security level


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

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL and Key must be set in .env file or environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

UPLOAD_FOLDER = "uploads"
ASSET_FOLDER = "asset"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSET_FOLDER, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/assets", StaticFiles(directory=ASSET_FOLDER), name="asset")

DISTANCE_THRESHOLD = 0.50
BIOMETRIC_BUCKET = os.getenv("BIOMETRIC_BUCKET")

@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

@app.post("/register-biometric") # Use router.post if you define a router
async def register_biometric(
    national_id: str = Form(...),
    face_image: UploadFile = File(...),
    iris_image: UploadFile = File(None) # Optional
):
    # Check if deepface server is available
    if not DeepFace:
        raise HTTPException(status_code=503, detail="Facial recognition service is not available.")

    face_filename = f"face_{uuid.uuid4()}.{face_image.filename.split('.')[-1]}"
    face_image_path = os.path.join(UPLOAD_FOLDER, face_filename)

    face_image_url = None # Initialize to None
    face_embedding = None # Initialize to None

    try:
        with open(face_image_path, "wb") as buffer:
            shutil.copyfileobj(face_image.file, buffer)

        # embedding the upload image 
        embedding_objs = DeepFace.represent(img_path=face_image_path, model_name="VGG-Face", enforce_detection=False)
        if not embedding_objs or 'embedding' not in embedding_objs[0]:
            raise HTTPException(status_code=400, detail="Could not generate a face embedding. Ensure the image contains a clear face.")
        face_embedding = embedding_objs[0]['embedding']

        # Upload face image to Supabase storage
        with open(face_image_path, "rb") as f:
            supabase.storage.from_(BIOMETRIC_BUCKET).upload(file=f, path=face_filename)
        
        # Get public URL
        face_image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(face_filename)

    except Exception as e:
        traceback.print_exc() # Log the full traceback
        raise HTTPException(status_code=500, detail=f"Error processing face image or uploading to storage: {e}")
    finally:
        if os.path.exists(face_image_path):
            print(f"Removing temporary face image file: {face_image_path}")
            os.remove(face_image_path)

    IRIS_API_URL = "http://localhost:8081"

    iris_image_url = None
    iris_embedding = None # This line is correct and should remain here

    if iris_image:
        iris_filename = f"iris_{uuid.uuid4()}.{iris_image.filename.split('.')[-1]}"
        temp_iris_image_path = os.path.join(UPLOAD_FOLDER, iris_filename)
        try:
            with open(temp_iris_image_path, "wb") as buffer:
                shutil.copyfileobj(iris_image.file, buffer)

            # --- Prepare image for sending to Iris API ---
            with open(temp_iris_image_path, "rb") as f_read:
                iris_bytes = f_read.read()
            iris_b64 = base64.b64encode(iris_bytes).decode('utf-8')

            # Make HTTP request to iris_model_apis.py to get embedding
            async with httpx.AsyncClient() as client:
                iris_embedding_response = await client.post(
                    f"{IRIS_API_URL}/get-iris-embedding",
                    json={"image_data": iris_b64},
                    timeout=30.0 # Adjust timeout as needed
                )
                iris_embedding_response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                iris_embedding_data = iris_embedding_response.json()
                iris_embedding = iris_embedding_data.get("embedding")

                if not iris_embedding:
                    raise ValueError("Iris API returned no embedding.")

            # Upload iris image to Supabase storage (still happens from Main.py)
            with open(temp_iris_image_path, "rb") as f_upload:
                supabase.storage.from_(BIOMETRIC_BUCKET).upload(file=f_upload, path=iris_filename)

            iris_image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(iris_filename)

        except httpx.HTTPStatusError as e:
            print(f"Error calling Iris API: {e.response.status_code} - {e.response.text}")
            traceback.print_exc()
            iris_embedding = None
            iris_image_url = None
            # Consider raising HTTPException here if iris embedding is mandatory
            # raise HTTPException(status_code=500, detail=f"Failed to get iris embedding from service: {e.response.text}")
        except Exception as e:
            print(f"Warning: Could not process optional iris image: {e}")
            traceback.print_exc()
            iris_embedding = None
            iris_image_url = None
        finally:
            if os.path.exists(temp_iris_image_path):
                print(f"Removing temporary iris image file: {temp_iris_image_path}")
                os.remove(temp_iris_image_path)

    # --- Database Insertion ---
    try:
        payload = {
            "National_ID": int(national_id),
            "face_image_url": face_image_url,
            "face_embedding": json.dumps(face_embedding), # Store as JSON string for PostgreSQL JSONB/Text
            "iris_image_url": iris_image_url,
            "iris_embedding": json.dumps(iris_embedding) if iris_embedding is not None else None # Store as JSON string if exists
        }
        
        # In newer Supabase client, .execute() will raise an exception on error.
        # It will not return an object with an .error attribute.
        supabase.table("Biometric").upsert(payload, on_conflict="National_ID").execute()

        return {"message": f"Biometric data registered successfully for ID {national_id}."}

    except PostgrestAPIError as e:
        # Catch specific Supabase API errors
        print(f"Supabase API Error during biometric data insertion: {e}")
        traceback.print_exc() # Print full traceback
        raise HTTPException(status_code=500, detail=f"Failed to save biometric data: {e.message if hasattr(e, 'message') else str(e)}")
        
    except Exception as e:
        # Catch any other unexpected errors during database insertion
        print(f"An unexpected error occurred during database insertion: {e}")
        traceback.print_exc() # Print full traceback for unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during database insertion: {e}")


@app.get("/customers")
def get_all_customers():
    try:
        response = supabase.table('Customer').select('National_ID, Name, SurName').execute()
        if response.data:
            for customer in response.data:
                customer['displayName'] = f"{customer['Name']} {customer['SurName']}"
            return response.data
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not fetch customer list.")

# In Main.py

# In Main.py

@app.post("/verify")
async def verify_customer_identity(
    background_tasks: BackgroundTasks, # Inject BackgroundTasks
    image: UploadFile = File(...),
    customer_id: int = Form(...)
):
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    
    is_match = False
    details = {} 
    try:
        # Step 1: Save the Uploaded Image
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Step 2: Generate Embedding from the Image
        try:
            embedding_objs = DeepFace.represent(
                img_path=image_path, 
                model_name="VGG-Face", 
                enforce_detection=True
            )
            uploaded_embedding = embedding_objs[0]['embedding']
        except ValueError as e:
            details["message"] = f"Could not process image: No face detected. ({str(e)})"
            details["detail"] = str(e)
            raise HTTPException(status_code=400, detail=details["message"])

        # Step 3: Fetch Stored Biometric Data from Database
        db_response = supabase.table('Biometric').select('face_embedding, face_image_url').eq('National_ID', customer_id).single().execute()
        
        # Step 4: Validate the Database Response
        if not db_response.data:
            details["message"] = f"Biometric data not found for customer ID: {customer_id}"
            raise HTTPException(status_code=404, detail=details["message"])
        
        stored_embedding_str = db_response.data.get('face_embedding')
        match_image_url = db_response.data.get('face_image_url')

        if not stored_embedding_str:
            details["message"] = "Stored face embedding not found for this customer."
            raise HTTPException(status_code=404, detail=details["message"])

        # Correctly parse the string from the DB into a list of numbers
        parsed_list = json.loads(stored_embedding_str)
        stored_embedding = [float(x) for x in parsed_list]

        # Step 5: Compare the Faces
        distance = cosine(uploaded_embedding, stored_embedding)
        is_match = bool(distance < DISTANCE_THRESHOLD)

        details["verified"] = is_match
        details["message"] = "Verified Successfully" if is_match else "Verification Failed: Faces do not match."
        details["distance"] = float(distance)
        details["image_url"] = match_image_url

        # Step 6: Return the Final Result (before logging and email in finally)
        return {
            "verified": is_match,
            "message": details["message"],
            "distance": details["distance"],
            "image_url": details["image_url"]
        }

    except HTTPException as e:
        # Re-raise known HTTP errors directly, but capture their details for logging/email
        details["status"] = "failure"
        details["message"] = e.detail # Capture the detail of HTTPException
        details["verified"] = False # Ensure verified is False on exception
        raise # Re-raise the exception to send the appropriate HTTP status code
    except Exception as e:
        # Catch any other unexpected errors and report them
        details["status"] = "failure"
        details["message"] = f"An unexpected server error occurred during face verification: {e}"
        details["detail"] = str(e)
        details["verified"] = False # Ensure verified is False on exception
        print(f"An unexpected server error occurred: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=details["message"])
            
    finally:
        # This block always runs, whether successful or an exception occurred.
        # Log authentication attempt and send email in the background.
        attempt_status = "success" if is_match else "failure" # is_match reflects the outcome before any exceptions

        # Fetch customer email for the report (needed for email_utils)
        customer_email = None
        customer_name = "Customer"
        try:
            customer_response = supabase.table("Customer").select("Name, SurName, Email").eq("National_ID", customer_id).single().execute()
            if customer_response.data:
                customer_data = customer_response.data
                customer_email = customer_data.get('Email')
                customer_name = f"{customer_data.get('Name', '')} {customer_data.get('SurName', '')}".strip() or "Customer"
        except Exception as e:
            print(f"Warning: Could not fetch customer email for ID {customer_id}: {e}")
            
        # Log to the new AuthenticationAttempts table
        log_payload = {
            "customer_id": customer_id,
            "biometric_type": "face",
            "status": attempt_status,
            "details": details # Store the captured details
        }
        try:
            supabase.table("AuthenticationAttempts").insert([log_payload]).execute()
            print(f"Logged face authentication attempt for {customer_id}: {attempt_status}")
        except Exception as e:
            print(f"ERROR: Failed to log authentication attempt to Supabase: {e}")
            traceback.print_exc()

        # Send email in background if email is available
        if customer_email:
            background_tasks.add_task(send_authentication_report_email, customer_email, customer_name, "face", is_match, details)

        # Clean up the uploaded image file
        if os.path.exists(image_path):
            os.remove(image_path)


# In Main.py

@app.get("/customer-details/{customer_id}")
async def get_customer_details(customer_id: int):
    """
    Fetches detailed information for a single customer, including their
    biometric face image URL and their recent transaction history with employee names.
    """
    try:
        # Step 1 & 2: Fetch customer and biometric data (same as before)
        customer_response = supabase.table("Customer").select("*").eq("National_ID", customer_id).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer_data = customer_response.data
        
        try:
            biometric_response = supabase.table("Biometric").select("face_image_url").eq("National_ID", customer_id).single().execute()
            customer_data['face_image_url'] = biometric_response.data['face_image_url'] if biometric_response.data else None
        except Exception:
            customer_data['face_image_url'] = None
        
        # Step 3: Fetch recent transactions for the customer
        transactions_response = supabase.table("Transactions") \
            .select("id, created_at, transaction_type, amount, note, employee_id") \
            .eq("customer_id", customer_id) \
            .order("created_at", desc=True) \
            .limit(15) \
            .execute()

        enriched_transactions = []
        if transactions_response.data:
            for tx in transactions_response.data:
                employee_name = "System" # Default name
                if tx.get("employee_id"):
                    try:
                        # Fetch the employee's name for each transaction
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

    except Exception as e:
        print(f"Error fetching customer details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customer details.")

@app.post("/register-employee")
async def register_employee(employee_data: EmployeeCreate):
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        hashed_password = pwd_context.hash(employee_data.password)
        payload = {
            "EmID": employee_data.employeeId,
            "EmName": employee_data.name,
            "EmSurName": employee_data.surname,
            "IsAdmin": employee_data.isAdmin,
            "FDW": now_utc.isoformat(),
            "EmPass": hashed_password
        }
        response = supabase.table("Employees").insert([payload]).execute()
        if getattr(response, 'error', None):
            raise HTTPException(status_code=500, detail=f"Failed to register employee: {getattr(response.error, 'message', str(response.error))}")
        return {"message": "Employee registered successfully!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# In Main.py
@app.post("/login-employee")
async def login_employee(employee_login_data: EmployeeLogin):
    employee = None  # Define employee outside the try block
    try:
        response = supabase.table("Employees").select("EmID, EmPass, IsAdmin, EmName, EmSurName").eq("EmID", employee_login_data.emId).single().execute()
        
        log_payload = {
            "Employee_ID": employee_login_data.emId,
            "EmResult": "Failure", # Default to failure
        }

        if not response.data:
            supabase.table("EmployeeLogs").insert(log_payload).execute()
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        
        employee = response.data
        # Add employee name to the log payload
        log_payload["EmName"] = employee.get("EmName")
        log_payload["EmSurName"] = employee.get("EmSurName")

        if not pwd_context.verify(employee_login_data.password, employee["EmPass"]):
            supabase.table("EmployeeLogs").insert(log_payload).execute()
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        
        # If successful, update result and log it
        log_payload["EmResult"] = "Success"
        supabase.table("EmployeeLogs").insert(log_payload).execute()
        
        return {
            "success": True, "message": "Login successful!", "emId": employee["EmID"],
            "isAdmin": employee["IsAdmin"], "name": employee["EmName"], "surname": employee["EmSurName"]
        }
    except Exception as e:
        # Log failure on any other exception too
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
            "PhoneNo": int(user_data.get("phoneNo")) if user_data.get("phoneNo") else None,
            "Gender": user_data.get("gender"), "DOR": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Email": user_data.get("email") or None, "Balance": balance_value,
        }
        response = supabase.table("Customer").insert([payload]).execute()
        if getattr(response, 'error', None):
            raise HTTPException(status_code=500, detail=f"Failed to save data: {getattr(response.error, 'message', str(response.error))}")
        return {"message": "User registered successfully!", "data": response.data or []}
    except (ValueError, TypeError) as ve:
        raise HTTPException(status_code=400, detail=f"Invalid data format: {ve}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
# In Main.py
@app.post("/transaction")
async def create_transaction(transaction: TransactionCreate):
    try:
        # Finding the customer balance in db
        customer_response = supabase.table("Customer").select("Balance").eq("National_ID", transaction.customer_id).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        current_balance = customer_response.data.get('Balance') or 0
        
        # Chose transaction type
        if transaction.transaction_type == 'withdrawal':
            if current_balance < transaction.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds for withdrawal.")
            new_balance = current_balance - transaction.amount
        else: # Deposit
            new_balance = current_balance + transaction.amount

        # Update the balance of the chosen customer
        supabase.table("Customer").update({"Balance": new_balance}).eq("National_ID", transaction.customer_id).execute()

        # update with transaction record
        transaction_record = {
            "customer_id": transaction.customer_id,
            "employee_id": transaction.employee_id,  # NEW
            "transaction_type": transaction.transaction_type,
            "amount": transaction.amount,
            "note": transaction.note,
            "balance_after": new_balance
        }
        supabase.table("Transactions").insert(transaction_record).execute()

        return {
            "message": f"{transaction.transaction_type.capitalize()} successful!",
            "new_balance": new_balance
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"An error occurred during the transaction: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during the transaction.")

@app.get("/registration-records")
async def get_registration_records():
    try:
        response = supabase.table("Customer").select("National_ID, Name, SurName, DOR, Balance").order("DOR", desc=True).execute()
        if getattr(response, 'error', None):
            raise HTTPException(status_code=500, detail=f"Failed to fetch registration records: {getattr(response.error, 'message', str(response.error))}")
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
async def get_customer_logs():
    try:
        response = supabase.table("CustomerLogs") \
            .select("*") \
            .order("Transaction_Timestamp", desc=True) \
            .limit(10) \
            .execute() # Added limit(10)
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch customer logs: {str(e)}")

@app.get("/employee-logs")
async def get_employee_logs():
    """
    Fetches a list of the 10 most recent successful employee logins.
    """
    try:
        response = supabase.table("EmployeeLogs") \
            .select("*") \
            .eq("EmResult", "Success") \
            .order("Log_Timestamp", desc=True) \
            .limit(10) \
            .execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employee logs: {str(e)}")
    
