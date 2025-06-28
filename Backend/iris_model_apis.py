import json
import os
import shutil
import datetime
import traceback
import uuid
import math
import scipy.ndimage
import numpy as np
import cv2
import base64
from PIL import Image
import io

import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field # Import Field here, as it might be used in BaseModel
from scipy.spatial.distance import cosine # Needed for authentication comparison

from supabase import create_client, Client # New imports for Supabase client
from typing import Literal, Optional # Needed for Pydantic models



# --- Load environment variables for Supabase (for this service) ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BIOMETRIC_BUCKET = os.getenv("BIOMETRIC_BUCKET") # Still needed for Supabase client init if used

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL and Key must be set in .env file or environment variables for iris_model_api.py.")
# You might not strictly need BIOMETRIC_BUCKET in this specific API if you're only reading embeddings,
# but it's good practice to ensure all necessary envs are checked if a Supabase client is created.
# If this API doesn't upload to storage, BIOMETRIC_BUCKET check can be removed from here.

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) # Initialize Supabase client for this service

# --- Pydantic Models for Iris API Requests/Responses ---
class IrisImageRequest(BaseModel):
    image_data: str # Base64 encoded image

class IrisEmbeddingResponse(BaseModel):
    embedding: list[float]
    message: str = "Iris embedding generated successfully."

# New: These models are now part of iris_model_api.py as it handles authentication
class IrisAuthentication(BaseModel):
    user_id: str | None = None
    image_data: str
    reference_local_filename: str | None = None # For debugging, if you want to keep it here

class IrisAuthResponse(BaseModel):
    message: str
    user_id: str | None = None # Claimed user_id
    is_authenticated: bool | None = None
    similarity: float | None = None # Similarity to claimed user_id
    matched_user_id: str | None = None # Best matched user_id in open-set
    best_similarity: float | None = None # Best similarity in open-set
    detail: str | None = None


# --- Configuration for Iris Model ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
IMG_SIZE = 224 # EfficientNet input size
UNET_MODEL_PATH = "model/best_model.pth" # Path to your UNet model
EFFNET_BACKBONE_MODEL_PATH = "model/best_effnet_backbone_model.pth" # Path to your EfficientNet backbone
ARCFACE_HEAD_MODEL_PATH = "model/best_arcface_head_model.pth" # Path to your ArcFace head
CLASS_TO_IDX_PATH = "class_to_idx.json" # Path to your class_to_idx mapping

AUTHENTICATION_THRESHOLD = 0.65 # Moved here: Threshold for iris authentication


# --- Global Model Instances (Loaded once on startup) ---
unet_model = None
effnet_backbone = None
arcface_head = None
num_classes = 0
idx_to_class = {}

# --- Helper Functions (Copied from your Main.py for iris processing) ---

def extract_iris_zone(mask):
    """
    Extracts the center and radius of the largest circular contour from a binary mask.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None
    largest = max(contours, key=cv2.contourArea)
    (x, y), radius = cv2.minEnclosingCircle(largest)
    if radius <= 0:
        return None, None
    return (int(x), int(y)), int(radius)

def normalize_iris(image_rgb, center, radius, radial_res=64, angular_res=256):
    """
    Applies Daugman's rubber sheet model normalization to an iris image.
    Uses scipy.ndimage.map_coordinates for efficient interpolation.
    """
    image_gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY) if len(image_rgb.shape) == 3 else image_rgb

    cx, cy = center
    norm_r_grid, norm_theta_grid = np.meshgrid(
        np.linspace(0, 1, radial_res),
        np.linspace(0, 2 * np.pi, angular_res),
        indexing='ij'
    )

    x_coords = cx + norm_r_grid * radius * np.cos(norm_theta_grid)
    y_coords = cy + norm_r_grid * radius * np.sin(norm_theta_grid)
    
    coords = np.array([y_coords, x_coords])

    normalized = scipy.ndimage.map_coordinates(
        image_gray, coords, order=1, mode='nearest'
    )
    
    normalized = normalized.astype(np.uint8)
    
    if normalized.max() > 0:
        normalized = cv2.normalize(normalized, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
    
    return normalized

def clean_mask(mask):
    """Applies morphological operations to clean a binary mask."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned

def iris_pipeline_for_inference(img_array_rgb, unet_model_local, device_local):
    """
    Full iris preprocessing pipeline for inference:
    UNet segmentation -> mask cleaning -> iris zone extraction -> Daugman normalization.
    Returns the normalized iris image ready for feature extraction.
    """
    img_resized_for_unet = cv2.resize(img_array_rgb, (256, 256)) / 255.0
    img_tensor_for_unet = torch.tensor(img_resized_for_unet).permute(2, 0, 1).float().unsqueeze(0).to(device_local)
    
    with torch.no_grad():
        pred_mask_logits = unet_model_local(img_tensor_for_unet)
        pred_mask_resized = F.interpolate(pred_mask_logits, size=(img_array_rgb.shape[0], img_array_rgb.shape[1]), mode='bilinear', align_corners=False)
        pred_mask_np = (torch.sigmoid(pred_mask_resized).squeeze().cpu().numpy() > 0.5).astype(np.uint8) * 255

    binary_mask = clean_mask(pred_mask_np)

    center, radius = extract_iris_zone(binary_mask)
    if center is None or radius <= 0:
        print(f"WARNING: No clear iris found or invalid radius during segmentation for image. Rejecting image.")
        return None
        
    normalized_iris = normalize_iris(img_array_rgb, center, radius)
    return normalized_iris

# Custom ArcFace module definition (must match your training definition)
class ArcMarginProduct(nn.Module):
    def __init__(self, in_features, out_features, s=30.0, m=0.50, easy_margin=False):
        super(ArcMarginProduct, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)

        self.easy_margin = easy_margin
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m

    def forward(self, input, label=None):
        cosine = F.linear(F.normalize(input), F.normalize(self.weight))
        return cosine * self.s

# --- Image Processing Function for FastAPI Endpoint ---
async def process_iris_image_for_api(image_data_b64: str):
    """
    Decodes base64 image, performs iris segmentation and normalization,
    and extracts the feature embedding using the loaded models.
    Returns the normalized embedding (as a list).
    """
    global unet_model, effnet_backbone

    if unet_model is None or effnet_backbone is None:
        raise HTTPException(status_code=503, detail="Iris models not loaded. Cannot process iris image.")

    try:
        img_bytes = base64.b64decode(image_data_b64)
        img_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_np = np.array(img_pil)

        normalized_iris_gray = iris_pipeline_for_inference(img_np, unet_model, DEVICE)

        if normalized_iris_gray is None:
            raise ValueError("Iris segmentation and normalization failed for this image.")

        normalized_iris_rgb = cv2.cvtColor(normalized_iris_gray, cv2.COLOR_GRAY2RGB)
        
        transform_effnet = A.Compose([
            A.PadIfNeeded(min_height=256, min_width=256, border_mode=cv2.BORDER_CONSTANT, value=0, p=1.0),
            A.Resize(IMG_SIZE, IMG_SIZE),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ])
        
        transformed = transform_effnet(image=normalized_iris_rgb)
        img_tensor = transformed['image'].unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            features = effnet_backbone(img_tensor)
            embedding = F.normalize(features, p=2, dim=1).cpu().squeeze(0)
        
        return embedding.tolist()

    except Exception as e:
        print(f"Error during iris image processing: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process iris image: {e}")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def load_all_models():
    """Loads all pre-trained models and class mappings when the FastAPI app starts."""
    global unet_model, effnet_backbone, arcface_head, num_classes, idx_to_class

    print(f"Loading iris models on device: {DEVICE}")

    if not os.path.exists(CLASS_TO_IDX_PATH):
        print(f"Warning: {CLASS_TO_IDX_PATH} not found. Creating a dummy for demonstration.")
        dummy_classes = {f"user_{i:04d}": i for i in range(10)} # Example: 10 dummy users
        with open(CLASS_TO_IDX_PATH, "w") as f:
            json.dump(dummy_classes, f)

    with open(CLASS_TO_IDX_PATH, "r") as f:
        class_to_idx = json.load(f)
    num_classes = len(class_to_idx)
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    print(f"Loaded {num_classes} classes from {CLASS_TO_IDX_PATH}")

    try:
        unet_model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights="imagenet",
            in_channels=3,
            classes=1
        ).to(DEVICE)
        unet_model.load_state_dict(torch.load(UNET_MODEL_PATH, map_location=DEVICE))
        unet_model.eval()
        print(f"UNet model loaded from {UNET_MODEL_PATH}")
    except FileNotFoundError:
        print(f"Error: UNet model not found at {UNET_MODEL_PATH}. Iris segmentation will be unavailable.")
        unet_model = None
    except Exception as e:
        print(f"Error loading UNet model: {e}. Iris segmentation will be unavailable.")
        unet_model = None

    try:
        effnet_backbone = timm.create_model('efficientnet_b0', pretrained=False, num_classes=0).to(DEVICE)
        effnet_backbone.load_state_dict(torch.load(EFFNET_BACKBONE_MODEL_PATH, map_location=DEVICE))
        effnet_backbone.eval()
        print(f"EfficientNet backbone loaded from {EFFNET_BACKBONE_MODEL_PATH}")
    except FileNotFoundError:
        print(f"Error: EfficientNet backbone not found at {EFFNET_BACKBONE_MODEL_PATH}. Iris feature extraction will be unavailable.")
        effnet_backbone = None
    except Exception as e:
        print(f"Error loading EfficientNet backbone: {e}. Iris feature extraction will be unavailable.")
        effnet_backbone = None

    try:
        if effnet_backbone and effnet_backbone.num_features:
            arcface_head = ArcMarginProduct(
                in_features=effnet_backbone.num_features,
                out_features=num_classes,
                s=30.0,
                m=0.50,
                easy_margin=False
            ).to(DEVICE)
            arcface_head.load_state_dict(torch.load(ARCFACE_HEAD_MODEL_PATH, map_location=DEVICE))
            arcface_head.eval()
            print(f"ArcFace head loaded from {ARCFACE_HEAD_MODEL_PATH}")
        else:
             print("Warning: EfficientNet backbone not loaded or num_features not available. ArcFace head will not be loaded.")
             arcface_head = None
    except FileNotFoundError:
        print(f"Error: ArcFace head not found at {ARCFACE_HEAD_MODEL_PATH}. Iris authentication will be unavailable.")
        arcface_head = None
    except Exception as e:
        print(f"Error loading ArcFace head: {e}. Iris authentication will be unavailable.")
        arcface_head = None

    if not (unet_model and effnet_backbone and arcface_head):
        print("Warning: One or more iris models failed to load. Iris authentication functionality might be limited or unavailable.")
    else:
        print("All iris models loaded successfully.")


@app.post("/get-iris-embedding", response_model=IrisEmbeddingResponse)
async def get_iris_embedding(request: IrisImageRequest):
    """
    Endpoint to receive a base64 encoded iris image and return its embedding.
    """
    embedding = await process_iris_image_for_api(request.image_data)
    return IrisEmbeddingResponse(embedding=embedding)


@app.post("/authenticate-iris", response_model=IrisAuthResponse)
async def authenticate_iris(request: IrisAuthentication):
    """
    Authenticates or identifies a user based on an iris image.
    Supports both closed-set verification (with user_id) and open-set identification (without user_id).
    Optionally, for debugging, allows specifying a local reference filename in 'uploads'.
    """
    # Models are checked on startup, but a quick check here for safety
    if not (unet_model and effnet_backbone and arcface_head):
        raise HTTPException(status_code=503, detail="Iris authentication models are not fully loaded on the server.")

    try:
        # Process the incoming iris image to get its embedding (the query image)
        # We use process_iris_image_for_api locally within this service now
        query_embedding_np = np.array(await process_iris_image_for_api(request.image_data))

        reference_embedding_np = None
        detail_message = None

        # Determine if local file comparison or Supabase comparison
        if request.reference_local_filename:
            # --- DEBUGGING / LOCAL FILE COMPARISON PATH ---
            # This path is for debugging only and uses local file, not Supabase
            UPLOAD_FOLDER = "uploads" # Define UPLOAD_FOLDER for local access
            local_file_path = os.path.join(UPLOAD_FOLDER, request.reference_local_filename)
            if not os.path.exists(local_file_path):
                raise HTTPException(status_code=404, detail=f"Local reference file not found: {request.reference_local_filename}")
            
            print(f"DEBUG: Using local file {local_file_path} for iris reference.")
            
            with open(local_file_path, "rb") as f:
                local_img_bytes = f.read()
            local_img_b64 = base64.b64encode(local_img_bytes).decode('utf-8')
            
            # Get embedding for local reference file using the local processing function
            reference_embedding_np = np.array(await process_iris_image_for_api(local_img_b64))
            detail_message = f"Comparison against local file: {request.reference_local_filename}"

            if request.user_id:
                matched_user_id_for_response = request.user_id
            else:
                matched_user_id_for_response = f"local_file:{request.reference_local_filename}"

            similarity = 1 - cosine(query_embedding_np, reference_embedding_np)
            is_authenticated = bool(similarity >= AUTHENTICATION_THRESHOLD)

            return IrisAuthResponse(
                message="Authentication successful (local)." if is_authenticated else "Authentication failed (local).",
                user_id=request.user_id,
                is_authenticated=is_authenticated,
                similarity=similarity,
                matched_user_id=matched_user_id_for_response,
                best_similarity=similarity,
                detail=detail_message
            )

        elif request.user_id:
            # --- CLOSED-SET VERIFICATION (using Supabase DB) ---
            db_response = supabase.table('Biometric').select('iris_embedding').eq('National_ID', request.user_id).single().execute()
            
            if not db_response.data or not db_response.data.get('iris_embedding'):
                return IrisAuthResponse(
                    message=f"Iris data not found for user ID: {request.user_id}.",
                    user_id=request.user_id,
                    is_authenticated=False,
                    detail="No registered iris embedding found for this user in Supabase."
                )
            
            stored_embedding = db_response.data['iris_embedding']
            if isinstance(stored_embedding, str):
                stored_embedding = json.loads(stored_embedding)
            
            reference_embedding_np = np.array(stored_embedding, dtype=np.float32)

            similarity = 1 - cosine(query_embedding_np, reference_embedding_np)
            is_authenticated = bool(similarity >= AUTHENTICATION_THRESHOLD)

            return IrisAuthResponse(
                message="Authentication successful." if is_authenticated else "Authentication failed.",
                user_id=request.user_id,
                is_authenticated=is_authenticated,
                similarity=similarity,
                detail="Closed-set verification against Supabase."
            )
        else:
            # --- OPEN-SET IDENTIFICATION (using Supabase DB) ---
            db_response = supabase.table('Biometric').select('National_ID, iris_embedding').not_eq('iris_embedding', 'null').execute()
            
            if not db_response.data:
                return IrisAuthResponse(
                    message="No iris data registered in the system for identification.",
                    is_authenticated=False,
                    detail="No iris embeddings available in Supabase to compare against."
                )

            best_similarity = -1.0
            matched_user_id = None

            for record in db_response.data:
                national_id = record['National_ID']
                stored_embedding = record['iris_embedding']
                
                if isinstance(stored_embedding, str):
                    stored_embedding = json.loads(stored_embedding)
                
                stored_embedding_np = np.array(stored_embedding, dtype=np.float32)
                
                current_similarity = 1 - cosine(query_embedding_np, stored_embedding_np)
                
                if current_similarity > best_similarity:
                    best_similarity = current_similarity
                    matched_user_id = national_id
            
            is_authenticated = bool(best_similarity >= AUTHENTICATION_THRESHOLD)

            if matched_user_id:
                message = f"Identified as user {matched_user_id}." if is_authenticated else "No matching iris found above threshold."
            else:
                message = "No matching iris found in the database."

            return IrisAuthResponse(
                message=message,
                is_authenticated=is_authenticated,
                matched_user_id=matched_user_id,
                best_similarity=best_similarity,
                detail="Open-set identification performed against Supabase."
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"An unexpected error occurred during iris authentication: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during iris authentication: {str(e)}")


@app.get("/")
def read_root():
    return {"message": "Iris Model API is running!"}
