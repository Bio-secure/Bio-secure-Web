import os
import shutil
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from pydantic import BaseModel
from pydantic import BaseModel
from passlib.context import CryptContext # NEW IMPORT for password hashing

class EmployeeCreate(BaseModel):
    employeeId: int 
    name: str       
    surname: str    
    password: str   
    isAdmin: bool

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

@app.post("/identify")
async def identify_face(image: UploadFile = File(...)):
    if DeepFace is None:
        raise HTTPException(status_code=503, detail="DeepFace is not available on this server.")

    if not image.filename:
        raise HTTPException(status_code=400, detail="No image file provided.")

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    try:
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        if not os.listdir(ASSET_FOLDER):
            raise HTTPException(status_code=404, detail="No faces found in asset directory for comparison.")

        result = DeepFace.find(
            img_path=image_path,
            db_path=ASSET_FOLDER,
            enforce_detection=False
        )

        if len(result) > 0 and not result[0].empty:
            match_path = result[0].iloc[0]["identity"]
            match_name = os.path.basename(match_path)
            match_url = f"http://localhost:8000/assets/{match_name}"
            return {"identity": match_name, "image_url": match_url}
        else:
            return {"identity": "No match found", "image_url": None}

    except Exception as e:
        print(f"DeepFace identification error: {str(e)}")
        if os.path.exists(image_path):
            os.remove(image_path)
        raise HTTPException(status_code=500, detail=f"Face identification failed: {str(e)}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

@app.post("/register-employee")
async def register_employee(employee_data: EmployeeCreate):
    try:
        # Get the current time for FDW, assuming Thailand timezone
        now_thailand_tz = datetime.datetime.now(datetime.timezone.utc)

        # --- CRITICAL: HASH THE PASSWORD ---
        hashed_password = pwd_context.hash(employee_data.password)

        payload = {
            "EmID": employee_data.employeeId,
            "EmName": employee_data.name,
            "EmSurName": employee_data.surname,
            "IsAdmin": employee_data.isAdmin,
            "FDW": now_thailand_tz.isoformat(), # First Day Working
            "EmPass": hashed_password # STORE THE HASHED PASSWORD
        }
        
        response = supabase.table("Employees").insert([payload]).execute()

        supabase_error = getattr(response, 'error', None)
        if supabase_error:
            raise HTTPException(status_code=500, detail=f"Failed to register employee: {getattr(supabase_error, 'message', str(supabase_error))}")
        
        return {"message": "Employee registered successfully!", "data": response.data}
    except Exception as e:
        print(f"Error registering employee: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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
            "DOR": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
        now = datetime.datetime.now(datetime.timezone.utc)
        
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