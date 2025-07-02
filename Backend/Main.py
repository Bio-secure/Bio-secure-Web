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
import requests

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
    user_id: str | None = None # Claimed user_id
    is_authenticated: bool | None = None
    similarity: float | None = None # Similarity to claimed user_id
    matched_user_id: str | None = None # Best matched user_id in open-set
    best_similarity: float | None = None # Best similarity in open-set
    detail: str | None = None

# Authentication threshold (cosine similarity for iris)
AUTHENTICATION_THRESHOLD = 0.30 # Adjust this value based on your desired security level

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

async def authenticate_iris_from_api(user_id: str, image_data_b64: str) -> dict:
    # This is a client function residing in Main.py to call the Iris Model API.
    headers = {"Content-Type": "application/json"}
    payload = {
        "user_id": user_id,
        "image_data": image_data_b64
    }
    response = None
    try:
        response = requests.post(f"{IRIS_MODEL_API_URL}/authenticate-iris", headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Iris Model API's /authenticate-iris: {e}")
        # Attempt to get error detail from response if available
        if response is not None and response.text:
            try:
                error_detail = response.json().get("detail", response.text)
            except json.JSONDecodeError:
                error_detail = response.text
            raise HTTPException(status_code=response.status_code, detail=f"Iris API error: {error_detail}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to communicate with Iris API: {e}")

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

# For only face authentication
async def authenticate_face_from_api(customer_id: int, face_image_path: str):
    try:
        embedding_objs = DeepFace.represent(
            img_path=face_image_path,
            model_name="VGG-Face",
            enforce_detection=True
        )
        uploaded_face_embedding = embedding_objs[0]['embedding']

        db_response = supabase.table('Biometric').select('face_embedding, face_image_url').eq('National_ID', customer_id).single().execute()

        if not db_response.data or not db_response.data.get('face_embedding'):
            return {
                "is_authenticated": False,
                "message": "No registered face biometric data found for this customer."
            }

        stored_face_embedding_str = db_response.data.get('face_embedding')
        match_face_image_url = db_response.data.get('face_image_url')
        parsed_list = json.loads(stored_face_embedding_str)
        stored_face_embedding = [float(x) for x in parsed_list]

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


@app.post("/verify")
async def verify_customer_identity(
    background_tasks: BackgroundTasks,
    face_image: UploadFile = File(None), # Made optional
    iris_image: UploadFile = File(None), # Added optional iris image
    customer_id: int = Form(...)
):
    """
    Verifies a customer's identity using facial recognition (if face_image is provided),
    iris authentication (if iris_image is provided), or both.
    Logs the attempt and sends an email report.
    """
    if not face_image and not iris_image:
        raise HTTPException(status_code=400, detail="At least one of face_image or iris_image must be provided.")

    face_image_path = None
    iris_image_path = None

    face_is_match = False
    iris_is_match = False
    
    face_details = {}
    iris_details = {}
    
    combined_details = {
        "customer_id": customer_id,
        "biometric_types_attempted": [],
        "overall_status": "failure",
        "face_verification": {},
        "iris_authentication": {}
    }

    # --- Process Face Image (if provided) ---
    if face_image:
        combined_details["biometric_types_attempted"].append("face")
        face_image_path = os.path.join(UPLOAD_FOLDER, f"{customer_id}_face_query_{uuid.uuid4()}.{face_image.filename.split('.')[-1]}")
        try:
            with open(face_image_path, "wb") as buffer:
                shutil.copyfileobj(face_image.file, buffer)

            face_auth_response = await authenticate_face_from_api(customer_id, face_image_path)
            face_is_match = face_auth_response.get("is_authenticated", False)

            face_details["message"] = face_auth_response.get("message")
            face_details["distance"] = face_auth_response.get("distance")
            face_details["image_url"] = face_auth_response.get("image_url")
            face_details["detail"] = face_auth_response.get("detail")

        except Exception as e:
            face_details["message"] = f"Unexpected face verification error: {e}"
            face_details["detail"] = str(e)
            face_is_match = False
            print(f"Face verification error: {e}")
            traceback.print_exc()
        finally:
            face_details["status"] = "success" if face_is_match else "failure"
            face_details["is_authenticated"] = face_is_match 
            combined_details["face_verification"] = face_details
            if face_image_path and os.path.exists(face_image_path):
                os.remove(face_image_path)
    # --- Process Iris Image (if provided) ---
    if iris_image:
        combined_details["biometric_types_attempted"].append("iris")
        iris_image_path = os.path.join(UPLOAD_FOLDER, f"{customer_id}_iris_query_{uuid.uuid4()}.{iris_image.filename.split('.')[-1]}")
        try:
            with open(iris_image_path, "wb") as buffer:
                shutil.copyfileobj(iris_image.file, buffer)
            
            with open(iris_image_path, "rb") as f:
                iris_image_bytes = f.read()
            iris_image_b64 = base64.b64encode(iris_image_bytes).decode('utf-8')
            
            # This is the line that calls the helper function defined in this very file
            iris_auth_response = await authenticate_iris_from_api(str(customer_id), iris_image_b64) 
            
            iris_is_match = iris_auth_response.get("is_authenticated", False)
            iris_details["message"] = "Iris Authenticated Successfully" if iris_is_match else "Iris Authentication Failed"
            iris_details["similarity"] = iris_auth_response.get("similarity") or iris_auth_response.get("best_similarity")
            iris_details["matched_user_id"] = iris_auth_response.get("matched_user_id")
            iris_details["detail"] = iris_auth_response.get("detail")
            
        except HTTPException as e: # Catch HTTP errors from iris API call
            iris_details["message"] = f"Iris API error: {e.detail}"
            iris_details["detail"] = str(e.detail)
            iris_is_match = False
        except Exception as e:
            iris_details["message"] = f"Unexpected iris authentication error: {e}"
            iris_details["detail"] = str(e)
            iris_is_match = False
            print(f"Iris authentication error: {e}")
            traceback.print_exc()
        finally:
            iris_details["status"] = "success" if iris_is_match else "failure"
            iris_details["is_authenticated"] = iris_is_match  
            combined_details["iris_authentication"] = iris_details
            if iris_image_path and os.path.exists(iris_image_path):
                os.remove(iris_image_path)

    # --- Determine Overall Result and Construct Response ---
    overall_verified = False
    response_message = "Verification Result:"
    
    if face_image and iris_image:
        overall_verified = face_is_match and iris_is_match
        response_message += f" Face: {face_details.get('message', 'N/A')}. Iris: {iris_details.get('message', 'N/A')}."
        combined_details["overall_status"] = "success" if overall_verified else "failure"
        combined_details["message"] = response_message
    elif face_image:
        overall_verified = face_is_match
        response_message += f" Face: {face_details.get('message', 'N/A')}."
        combined_details["overall_status"] = "success" if overall_verified else "failure"
        combined_details["message"] = response_message
    elif iris_image:
        overall_verified = iris_is_match
        response_message += f" Iris: {iris_details.get('message', 'N/A')}."
        combined_details["overall_status"] = "success" if overall_verified else "failure"
        combined_details["message"] = response_message

    # Final response to frontend
    return_payload = {
        "verified": overall_verified,
        "message": response_message,
        "face_distance": face_details.get("distance"),
        "face_image_url": face_details.get("image_url"),
        "iris_similarity": iris_details.get("similarity"),
        "iris_matched_user_id": iris_details.get("matched_user_id"),
        "biometric_types_attempted": combined_details["biometric_types_attempted"],
        "details": {
            "face": face_details,
            "iris": iris_details
        }
    }

    # --- Log and Email (in finally block for consistency and cleanup) ---
    # Prepare details for logging and email based on the combined process
    final_log_details = {
        "face_verification": combined_details["face_verification"],
        "iris_authentication": combined_details["iris_authentication"],
        "overall_message": response_message,
        "overall_verified": overall_verified,
        "types_attempted": combined_details["biometric_types_attempted"],
        "face_distance": face_details.get("distance"),
        "iris_simiarity": iris_details.get("matched_user_id")
    }
    
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
        
    log_payload = {
        "customer_id": customer_id,
        "biometric_type": "combined" if len(combined_details["biometric_types_attempted"]) > 1 else combined_details["biometric_types_attempted"][0],
        "status": "success" if overall_verified else "failure",
        "details": json.dumps(final_log_details)  # Convert nested dict to JSON string
    }
    try:
        supabase.table("AuthenticationAttempts").insert([log_payload]).execute()
        print(f"Logged {'combined' if len(combined_details['biometric_types_attempted']) > 1 else combined_details['biometric_types_attempted'][0]} authentication attempt for {customer_id}: {log_payload['status']}")
    except Exception as e:
        print(f"ERROR: Failed to log authentication attempt to Supabase: {e}")
        traceback.print_exc()

    if customer_email:
        background_tasks.add_task(send_authentication_report_email, customer_email, customer_name, log_payload["biometric_type"], overall_verified, final_log_details)
    
    return return_payload

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
    print(employee_login_data)
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
    
