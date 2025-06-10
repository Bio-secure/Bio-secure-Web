import os
import shutil
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from deepface import DeepFace # Assuming DeepFace is used and installed

# Load environment variables from .env file
load_dotenv()

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL and Key must be set in .env file or environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FastAPI App Setup ---
app = FastAPI()

# Enable CORS for frontend access
# In production, replace "*" with your specific frontend domain(s), e.g., ["http://localhost:8080", "https://yourfrontend.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Folder Setup for DeepFace ---
UPLOAD_FOLDER = "uploads"
ASSET_FOLDER = "asset"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSET_FOLDER, exist_ok=True) # Ensure asset folder also exists

# Serve static files (images)
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/assets", StaticFiles(directory=ASSET_FOLDER), name="asset")

# --- Routes ---

@app.get("/")
def root():
    """Basic test route to confirm FastAPI is running."""
    return {"message": "FastAPI is running!"}

@app.post("/identify")
async def identify_face(image: UploadFile = File(...)):
    """
    Endpoint to identify a face from an uploaded image against a database of known faces.
    Uses DeepFace library.
    """
    if not image.filename:
        raise HTTPException(status_code=400, detail="No image file provided.")

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    try:
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        result = DeepFace.find(
            img_path=image_path,
            db_path=ASSET_FOLDER,
            enforce_detection=False # Set to True if you want to strictly enforce face detection
        )

        if len(result) > 0 and not result[0].empty:
            # Assuming DeepFace returns a pandas DataFrame, and we want the first match
            match_path = result[0].iloc[0]["identity"]
            match_name = os.path.basename(match_path) # e.g., "person_name.jpg"
            # Construct URL for the matched image
            match_url = f"http://localhost:8000/assets/{match_name}"
            return {"identity": match_name, "image_url": match_url}
        else:
            return {"identity": "No match found", "image_url": None}

    except Exception as e:
        print(f"DeepFace identification error: {str(e)}")
        # You might want to remove the uploaded image on error
        if os.path.exists(image_path):
            os.remove(image_path)
        raise HTTPException(status_code=500, detail=f"Face identification failed: {str(e)}")
    finally:
        # Clean up the uploaded image after processing (optional, but good practice)
        if os.path.exists(image_path):
            os.remove(image_path)

@app.post("/register-user")
async def register_user(user_data: dict):
    """
    Endpoint to register a new user in the Customer table.
    Expects user details including National_ID.
    """
    try:
        payload = {
            "National_ID": int(user_data.get("nationalId")) if user_data.get("nationalId") else None,
            "Name": user_data.get("firstName"),
            "SurName": user_data.get("lastName"),
            "BirthDate": user_data.get("birthDate"),
            "PhoneNo": int(user_data.get("phoneNo")) if user_data.get("phoneNo") else None,
            "Gender": user_data.get("gender"),
            "DOR": datetime.datetime.now().isoformat(), # Date of Registration
            "Email": user_data.get("email") or None,
            "Balance": float(user_data.get("balance")) if user_data.get("balance") else 0.0
        }

        # Debugging: Print payload to see what's being sent
        print(f"Payload for Supabase: {payload}")

        response = supabase.table("Customer").insert([payload]).execute()

        # Debugging: Print the raw response from Supabase
        print(f"Supabase raw response: {response}")

        # Safely check for an error attribute in the response
        supabase_error = getattr(response, 'error', None)

        if supabase_error:
            # An actual error occurred from Supabase (e.g., RLS, schema mismatch, constraint violation)
            print(f"Supabase error object type: {type(supabase_error)}")
            print(f"Supabase error details: {supabase_error}")
            error_message = getattr(supabase_error, 'message', str(supabase_error))
            raise HTTPException(status_code=500, detail=f"Failed to save data: {error_message}")
        elif not response.data:
            # This case means no explicit error, but also no data was returned.
            # For inserts, Supabase usually returns the inserted row(s) in 'data'.
            # If 'data' is empty, it might mean the insert was technically successful but didn't return anything.
            # Given the previous context, we'll assume success here.
            print("Supabase operation successful, but no data was explicitly returned in response.")
            return {"message": "User registered successfully!", "data": []} # Return empty list for data if none was returned
        else:
            # Success: response.data should contain the inserted row(s)
            data = response.data
            print(f"Inserted: {data}")
            return {"message": "User registered successfully!", "data": data}

    except ValueError as ve:
        # Handles cases where type conversions (int(), float()) fail for phoneNo, nationalId, balance
        print(f"Validation error in payload: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"Invalid data format: {str(ve)}")
    except HTTPException:
        # Re-raise HTTPExceptions that were explicitly raised (e.g., by RLS policy, or other specific errors)
        raise
    except Exception as e:
        # Catch-all for any other unexpected errors during the process
        print(f"An unexpected error occurred in register_user: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")