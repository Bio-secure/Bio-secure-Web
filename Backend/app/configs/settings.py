import os
from dotenv import load_dotenv
from supabase import create_client, Client
from passlib.context import CryptContext

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IRIS_MODEL_API_URL = os.getenv("IRIS_MODEL_API_URL", "http://localhost:8081")
BIOMETRIC_BUCKET = os.getenv("BIOMETRIC_BUCKET")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL and Key must be set in environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None

# thresholds
FACE_DISTANCE_THRESHOLD = 0.35
IRIS_AUTHENTICATION_THRESHOLD = 0.65

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")