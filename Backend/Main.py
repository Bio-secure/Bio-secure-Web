import os
import shutil
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from pydantic import BaseModel # Only one import needed for BaseModel
from passlib.context import CryptContext

# Define Pydantic models
class EmployeeCreate(BaseModel):
    employeeId: int 
    name: str       
    surname: str    
    password: str   
    isAdmin: bool

# NEW: Pydantic model for Employee Login
class EmployeeLogin(BaseModel):
    emId: int
    password: str

# Password hashing context (defined once globally)
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

UPLOAD_FOLDER = "uploads"
ASSET_FOLDER = "asset"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSET_FOLDER, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/assets", StaticFiles(directory=ASSET_FOLDER), name="asset")

@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

@app.get("/customers")
def get_all_customers():
    """
    Fetches a list of all customers to populate the frontend dropdown.
    """
    try:
        response = supabase.table('Customer').select('National_ID, Name, SurName').execute()
        if response.data:
            # Format the name for display in the dropdown
            for customer in response.data:
                customer['displayName'] = f"{customer['Name']} {customer['SurName']}"
            return response.data
        return []
    except Exception as e:
        print(f"Error fetching customers: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch customer list.")

@app.post("/verify")
async def verify_customer_identity(
    image: UploadFile = File(...),
    customer_id: str = Form(...) # Get the selected customer's ID from the form
):
    """
    Verifies if the uploaded image matches the selected customer's stored embedding.
    """
    if not image.filename or not customer_id:
        raise HTTPException(status_code=400, detail="Image file and Customer ID are required.")

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    
    try:
        # 1. Save uploaded image temporarily
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # 2. Generate embedding for the uploaded image
        try:
            embedding_objs = DeepFace.represent(img_path=image_path, model_name="VGG-Face", enforce_detection=False)
            if not embedding_objs or 'embedding' not in embedding_objs[0]:
                raise ValueError("Could not process a face in the uploaded image.")
            uploaded_embedding = embedding_objs[0]['embedding']
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Face processing error: {e}")

        # 3. Fetch the stored embedding for the SELECTED customer
        response = supabase.table('Biometric').select('face_embedding, face_image_url').eq('National ID', customer_id).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Biometric data not found for the selected customer.")
        
        stored_embedding = response.data['face_embedding']
        match_image_url = response.data['face_image_url']

        # 4. Compare the two embeddings
        from scipy.spatial.distance import cosine
        distance = cosine(uploaded_embedding, stored_embedding)

        # 5. Return the result
        if distance < DISTANCE_THRESHOLD:
            return {
                "verified": True,
                "message": "Verified Successfully",
                "distance": distance,
                "image_url": match_image_url
            }
        else:
            return {
                "verified": False,
                "message": "Verification Failed: Faces do not match.",
                "distance": distance,
                "image_url": match_image_url
            }

    except Exception as e:
        print(f"An unexpected error occurred during verification: {e}")
        raise HTTPException(status_code=500, detail="An internal verification error occurred.")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

@app.post("/register-employee")
async def register_employee(employee_data: EmployeeCreate):
    try:
        # Get the current time for FDW in UTC
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # --- CRITICAL: HASH THE PASSWORD ---
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

        supabase_error = getattr(response, 'error', None)
        if supabase_error:
            raise HTTPException(status_code=500, detail=f"Failed to register employee: {getattr(supabase_error, 'message', str(supabase_error))}")
        
        return {"message": "Employee registered successfully!", "data": response.data}
    except Exception as e:
        print(f"Error registering employee: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# NEW: Employee Login Endpoint
@app.post("/login-employee")
async def login_employee(employee_login_data: EmployeeLogin):
    try:
        # 1. Fetch employee by EmID, including Name and SurName
        response = supabase.table("Employees").select("EmID", "EmPass", "IsAdmin", "EmName", "EmSurName").eq("EmID", employee_login_data.emId).execute() 
        
        supabase_error = getattr(response, 'error', None)
        if supabase_error:
            print(f"Supabase error during login: {supabase_error}")
            raise HTTPException(status_code=500, detail=f"Database error: {getattr(supabase_error, 'message', str(supabase_error))}")

        employee_data = response.data
        if not employee_data:
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        
        employee = employee_data[0] # Assuming EmID is unique, there's only one result

        # 2. Verify password
        if not pwd_context.verify(employee_login_data.password, employee["EmPass"]):
            raise HTTPException(status_code=401, detail="Invalid Employee ID or Password.")
        
        # 3. Successful login: Return success, admin status, and employee name/surname
        return {
            "success": True,
            "message": "Login successful!",
            "emId": employee["EmID"],
            "isAdmin": employee["IsAdmin"],
            "name": employee["EmName"],
            "surname": employee["EmSurName"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"An unexpected error occurred during employee login: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during login: {str(e)}")


@app.post("/register-user")
async def register_user(user_data: dict):
    try:
        balance_value = user_data.get("balance")
        if balance_value is not None:
            try:
                balance_value = float(balance_value) if str(balance_value).strip() != '' else None
            except ValueError:
                raise HTTPException(status_code=400, detail="Balance must be a valid number.")

        payload = {
            "National_ID": int(user_data.get("nationalId")) if user_data.get("nationalId") is not None else None,
            "Name": user_data.get("firstName"),
            "SurName": user_data.get("lastName"),
            "BirthDate": user_data.get("birthDate"),
            "PhoneNo": int(user_data.get("phoneNo")) if user_data.get("phoneNo") is not None else None,
            "Gender": user_data.get("gender"),
            "DOR": datetime.datetime.now(datetime.timezone.utc).isoformat(), # Using UTC
            "Email": user_data.get("email") or None,
            "Balance": balance_value,
        }

        print(f"Payload for Supabase: {payload}")

        response = supabase.table("Customer").insert([payload]).execute()

        print(f"Supabase raw response: {response}")

        supabase_error = getattr(response, 'error', None)

        if supabase_error:
            print(f"Supabase error object type: {type(supabase_error)}")
            print(f"Supabase error details: {supabase_error}")
            error_message = getattr(supabase_error, 'message', str(supabase_error))
            raise HTTPException(status_code=500, detail=f"Failed to save data: {error_message}")
        elif not response.data and not supabase_error:
            print("Supabase operation successful, but no data was explicitly returned in response.")
            return {"message": "User registered successfully!", "data": []}
        else:
            data = response.data
            print(f"Inserted: {data}")
            return {"message": "User registered successfully!", "data": data}

    except ValueError as ve:
        print(f"Validation error in payload: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"Invalid data format: {str(ve)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"An unexpected error occurred in register_user: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/registration-records")
async def get_registration_records():
    try:
        response = supabase.table("Customer").select("National_ID", "Name", "SurName", "DOR", "Balance").order("DOR", desc=True).execute()

        supabase_error = getattr(response, 'error', None)

        if supabase_error:
            print(f"Supabase fetch error for registrations: {supabase_error}")
            error_message = getattr(supabase_error, 'message', str(supabase_error))
            raise HTTPException(status_code=500, detail=f"Failed to fetch registration records: {error_message}")
        elif not response.data:
            print("No registration records found.")
            return []
        else:
            return response.data

    except HTTPException:
        raise
    except Exception as e:
        print(f"An unexpected error occurred while fetching registration records: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/registration-stats")
async def get_registration_stats():
    """
    Fetches registration statistics (today, this week, this month).
    Counts are based on the server's current date in UTC.
    Updated to handle Supabase client response structure.
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc) # Using UTC
        
        # Start of today (UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Start of the week (Monday, UTC) - Python's weekday() is 0=Monday, 6=Sunday
        week_start = today_start - datetime.timedelta(days=today_start.weekday())
        
        # Start of the month (UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        today_count_response = supabase.table("Customer").select("*", count="exact")\
            .gte("DOR", today_start.isoformat())\
            .execute()
        
        week_count_response = supabase.table("Customer").select("*", count="exact")\
            .gte("DOR", week_start.isoformat())\
            .execute()
            
        month_count_response = supabase.table("Customer").select("*", count="exact")\
            .gte("DOR", month_start.isoformat())\
            .execute()

        # Extract counts directly from the .count attribute
        today_count = today_count_response.count
        week_count = week_count_response.count
        month_count = month_count_response.count

        return {
            "today": today_count,
            "week": week_count,
            "month": month_count
        }

    except Exception as e:
        print(f"Error fetching registration stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch registration stats: {str(e)}")