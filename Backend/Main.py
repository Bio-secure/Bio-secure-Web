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
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Body # Added Body for JSON requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from scipy.spatial.distance import cosine # Already present


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
AUTHENTICATION_THRESHOLD = 0.65 # Adjust this value based on your desired security level


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
    allow_origins=["*"],
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

@app.post("/register-biometric")
async def register_biometric(
    face_image: UploadFile = File(...),
    iris_image: UploadFile = File(None) # Optional
):
    # Check if deepface server is avalible 
    if not DeepFace:
        raise HTTPException(status_code=503, detail="Facial recognition service is not available.")
    

    face_filename = f"face_{uuid.uuid4()}.{face_image.filename.split('.')[-1]}" # for creating the registered image name
    face_image_path = os.path.join(UPLOAD_FOLDER, face_filename) # calling the image from the database

    try:
        with open(face_image_path, "wb") as buffer:
            shutil.copyfileobj(face_image.file, buffer)

        # embedding the upload image 
        embedding_objs = DeepFace.represent(img_path=face_image_path, model_name="VGG-Face", enforce_detection=False)
        if not embedding_objs or 'embedding' not in embedding_objs[0]:
            raise HTTPException(status_code=400, detail="Could not generate a face embedding. Ensure the image contains a clear face.")
        face_embedding = embedding_objs[0]['embedding']

        with open(face_image_path, "rb") as f:
            supabase.storage.from_(BIOMETRIC_BUCKET).upload(file=f, path=face_filename)
        
        # call a publc url from supabase
        face_image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(face_filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing face image: {e}")
    finally: #if the image path already exist remove the previous one
        if os.path.exists(face_image_path):
            print("Face image already exist in the ")
            os.remove(face_image_path)

    iris_image_url = None
    if iris_image:
        iris_filename = f"iris_{uuid.uuid4()}.{iris_image.filename.split('.')[-1]}"
        try:
            with open(os.path.join(UPLOAD_FOLDER, iris_filename), "wb") as buffer:
                shutil.copyfileobj(iris_image.file, buffer)
            
            with open(os.path.join(UPLOAD_FOLDER, iris_filename), "rb") as f:
                supabase.storage.from_(BIOMETRIC_BUCKET).upload(file=f, path=iris_filename)
            
            iris_image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(iris_filename)
        except Exception as e:
            print(f"Could not process optional iris image: {e}")
        finally:
            if os.path.exists(os.path.join(UPLOAD_FOLDER, iris_filename)):
                os.remove(os.path.join(UPLOAD_FOLDER, iris_filename))

    try:
        payload = {
            "id": str(uuid.uuid4()),
            "face_image_url": face_image_url,
            "face_embedding": face_embedding,
            "iris_image_url": iris_image_url
        }
        
        supabase.table("Biometric").upsert(payload, on_conflict="National_ID").execute()

        return {"message": f"Biometric data registered successfully for ID {id}."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during database insertion: {str(e)}")


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

@app.post("/verify")
async def verify_customer_identity(
    image: UploadFile = File(...),
    customer_id: int = Form(...)
):
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    
    try:
        # Step 1: Save the Uploaded Image
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Step 2: Generate Embedding from the Image
        try:
            # Enforce_detection=True makes sure a face is found
            embedding_objs = DeepFace.represent(
                img_path=image_path, 
                model_name="VGG-Face", 
                enforce_detection=True
            )
            uploaded_embedding = embedding_objs[0]['embedding']
        except ValueError as e:
            # This provides a clear error if no face is in the image
            raise HTTPException(status_code=400, detail=f"Could not process image: No face detected. ({str(e)})")

        # Step 3: Fetch Stored Biometric Data from Database
        db_response = supabase.table('Biometric').select('face_embedding, face_image_url').eq('National_ID', customer_id).single().execute()
        
        # Step 4: Validate the Database Response
        if not db_response.data:
            raise HTTPException(status_code=404, detail=f"Biometric data not found for customer ID: {customer_id}")
        
        stored_embedding_str = db_response.data.get('face_embedding')
        match_image_url = db_response.data.get('face_image_url')

        if not stored_embedding_str:
            raise HTTPException(status_code=404, detail="Stored face embedding not found for this customer.")

        # Correctly parse the string from the DB into a list of numbers
        parsed_list = json.loads(stored_embedding_str)
        stored_embedding = [float(x) for x in parsed_list]

        # Step 5: Compare the Faces and Return Result
        distance = cosine(uploaded_embedding, stored_embedding)

        # Convert the result to a standard Python boolean to prevent errors
        is_match = bool(distance < DISTANCE_THRESHOLD)

        return {
            "verified": is_match,
            "message": "Verified Successfully" if is_match else "Verification Failed: Faces do not match.",
            "distance": float(distance),
            "image_url": match_image_url
        }

    except HTTPException:
        # Re-raise known HTTP errors directly
        raise
    except Exception as e:
        # Catch any other unexpected errors and report them
        print(f"An unexpected server error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Specific Backend Error: {str(e)}")
        
    finally:
        # This always runs to clean up the uploaded file
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

@app.post("/login-employee")
async def login_employee(employee_login_data: EmployeeLogin):
    try:
        response = supabase.table("Employees").select("EmID, EmPass, IsAdmin, EmName, EmSurName").eq("EmID", employee_login_data.emId).execute()
        if getattr(response, 'error', None):
            raise HTTPException(status_code=500, detail=f"Database error: {getattr(response.error, 'message', str(response.error))}")
        if not response.data:
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        employee = response.data[0]
        if not pwd_context.verify(employee_login_data.password, employee["EmPass"]):
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        return {
            "success": True, "message": "Login successful!", "emId": employee["EmID"],
            "isAdmin": employee["IsAdmin"], "name": employee["EmName"], "surname": employee["EmSurName"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during login: {str(e)}")

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
    # ... (The logic for getting balance and updating the Customer table is the same) ...
    try:
        # --- Steps 1 & 2 are the same ---
        customer_response = supabase.table("Customer").select("Balance").eq("National_ID", transaction.customer_id).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        current_balance = customer_response.data.get('Balance') or 0
        
        if transaction.transaction_type == 'withdrawal':
            if current_balance < transaction.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds for withdrawal.")
            new_balance = current_balance - transaction.amount
        else: # Deposit
            new_balance = current_balance + transaction.amount

        # --- Step 3 is the same ---
        supabase.table("Customer").update({"Balance": new_balance}).eq("National_ID", transaction.customer_id).execute()

        # --- Step 4 is UPDATED to include employee_id ---
        transaction_record = {
            "customer_id": transaction.customer_id,
            "employee_id": transaction.employee_id,  # NEW
            "transaction_type": transaction.transaction_type,
            "amount": transaction.amount,
            "note": transaction.note,
            "balance_after": new_balance
        }
        supabase.table("Transactions").insert(transaction_record).execute()

        # --- Step 5 is the same ---
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