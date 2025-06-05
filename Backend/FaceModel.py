from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from deepface import DeepFace
import os
import shutil

app = FastAPI()

# Enable CORS for frontend access (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder setup
UPLOAD_FOLDER = "uploads"
ASSET_FOLDER = "asset"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Serve image folders
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/assets", StaticFiles(directory=ASSET_FOLDER), name="asset")

# Test route
@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

# Face identification endpoint
@app.post("/identify")
async def identify_face(image: UploadFile = File(...)):
    # Save uploaded image
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Perform face recognition
    try:
        result = DeepFace.find(
            img_path=image_path,
            db_path=ASSET_FOLDER,
            enforce_detection=False
        )

        if len(result) > 0 and len(result[0]) > 0:
            match_path = result[0].iloc[0]["identity"]
            match_name = os.path.basename(match_path)
            match_url = f"http://localhost:8000/assets/{match_name}"
            return {"identity": match_name, "image_url": match_url}
        else:
            return {"identity": "No match found", "image_url": None}

    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
