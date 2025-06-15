from pydantic import BaseModel
import uvicorn
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
import segmentation_models_pytorch as smp
import numpy as np
import cv2
import base64
from PIL import Image
import io
import os
import json
import math # For ArcFace
import scipy.ndimage # For optimized image transformation (map_coordinates)

# --- Configuration ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
IMG_SIZE = 224 # EfficientNet input size
UNET_MODEL_PATH = "model/best_model.pth" # Path to your trained UNet model
EFFNET_BACKBONE_MODEL_PATH = "model/best_effnet_backbone_model.pth" # Path to your trained EfficientNet backbone
ARCFACE_HEAD_MODEL_PATH = "model/best_arcface_head_model.pth" # Path to your trained ArcFace head
CLASS_TO_IDX_PATH = "class_to_idx.json" # Path to your class_to_idx.json

# Authentication threshold (cosine similarity)
AUTHENTICATION_THRESHOLD = 0.65 # Adjust this value based on your desired security level

# --- Pydantic Models for Request Body ---
class IrisAuthRequest(BaseModel):
    user_id: str | None = None # User ID is now optional for open-set authentication
    image_data: str # Base64 encoded image

class IrisAuthResponse(BaseModel):
    message: str
    user_id: str | None = None # Claimed user_id
    is_authenticated: bool | None = None
    similarity: float | None = None # Similarity to claimed user_id
    matched_user_id: str | None = None # Best matched user_id in open-set
    best_similarity: float | None = None # Best similarity in open-set
    detail: str | None = None


# --- Global Model Instances (Loaded once on startup) ---
unet_model = None
effnet_backbone = None
arcface_head = None
num_classes = 0

# --- Helper Functions (Copied/Adapted from your training notebooks) ---

def extract_iris_zone(mask):
    """
    Extracts the center and radius of the largest circular contour from a binary mask.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None
    largest = max(contours, key=cv2.contourArea)
    (x, y), radius = cv2.minEnclosingCircle(largest)
    if radius <= 0: # Ensure radius is positive
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
    # UNet input preprocessing: resize to 256x256, convert to tensor, normalize (simple 0-1)
    img_resized_for_unet = cv2.resize(img_array_rgb, (256, 256)) / 255.0
    img_tensor_for_unet = torch.tensor(img_resized_for_unet).permute(2, 0, 1).float().unsqueeze(0).to(device_local)
    
    with torch.no_grad():
        pred_mask_logits = unet_model_local(img_tensor_for_unet)
        # Resize mask prediction back to original image size for accurate contour finding
        pred_mask_resized = F.interpolate(pred_mask_logits, size=(img_array_rgb.shape[0], img_array_rgb.shape[1]), mode='bilinear', align_corners=False)
        pred_mask_np = (torch.sigmoid(pred_mask_resized).squeeze().cpu().numpy() > 0.5).astype(np.uint8) * 255

    binary_mask = clean_mask(pred_mask_np)

    center, radius = extract_iris_zone(binary_mask)
    if center is None or radius <= 0:
        # Fallback: If no clear iris is found, reject the image instead of using a default.
        # For a robust system, you want to ensure high quality input.
        print(f"WARNING: No clear iris found or invalid radius during segmentation for image. Rejecting image.")
        return None # Indicate failure to process iris
        
    normalized_iris = normalize_iris(img_array_rgb, center, radius)
    return normalized_iris # This is 64x256 grayscale uint8

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

    def forward(self, input, label): # Label is used during training, not inference here
        # For inference, we only need the feature vector 'input'
        # and the weights 'self.weight'. We do not use 'label'.
        # The forward pass will effectively compute cosine similarity for embedding extraction.
        cosine = F.linear(F.normalize(input), F.normalize(self.weight))
        return cosine * self.s # Scale by s, return logits or features depending on use case

# --- Event Handlers (Load models on startup) ---

@app.on_event("startup")
async def load_models():
    """Loads the pre-trained models and class mappings when the FastAPI app starts."""
    global unet_model, effnet_backbone, arcface_head, num_classes, idx_to_class

    print(f"Loading models on device: {DEVICE}")

    # Load class_to_idx for number of classes
    if not os.path.exists(CLASS_TO_IDX_PATH):
        raise FileNotFoundError(f"{CLASS_TO_IDX_PATH} not found. Please ensure it's in the same directory.")
    with open(CLASS_TO_IDX_PATH, "r") as f:
        class_to_idx = json.load(f)
    num_classes = len(class_to_idx)
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    print(f"Loaded {num_classes} classes from {CLASS_TO_IDX_PATH}")

    # 1. Load UNet Model
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
        print(f"Error: UNet model not found at {UNET_MODEL_PATH}. Please ensure it exists.")
        raise
    except Exception as e:
        print(f"Error loading UNet model: {e}")
        raise

    # 2. Load EfficientNet Backbone
    try:
        effnet_backbone = timm.create_model('efficientnet_b0', pretrained=False, num_classes=0).to(DEVICE)
        effnet_backbone.load_state_dict(torch.load(EFFNET_BACKBONE_MODEL_PATH, map_location=DEVICE))
        effnet_backbone.eval()
        print(f"EfficientNet backbone loaded from {EFFNET_BACKBONE_MODEL_PATH}")
    except FileNotFoundError:
        print(f"Error: EfficientNet backbone not found at {EFFNET_BACKBONE_MODEL_PATH}. Please ensure it exists.")
        raise
    except Exception as e:
        print(f"Error loading EfficientNet backbone: {e}")
        raise

    # 3. Load ArcFace Head
    try:
        # IN_FEATURES for EfficientNet B0 is typically 1280
        # Ensure this matches the `effnet_backbone.num_features`
        if effnet_backbone.num_features is None:
             raise ValueError("EfficientNet backbone did not expose num_features. Cannot initialize ArcFace head.")
        
        arcface_head = ArcMarginProduct(
            in_features=effnet_backbone.num_features,
            out_features=num_classes,
            s=30.0, # Must match s from training
            m=0.50, # Must match m from training
            easy_margin=False # Must match easy_margin from training
        ).to(DEVICE)
        arcface_head.load_state_dict(torch.load(ARCFACE_HEAD_MODEL_PATH, map_location=DEVICE))
        arcface_head.eval()
        print(f"ArcFace head loaded from {ARCFACE_HEAD_MODEL_PATH}")
    except FileNotFoundError:
        print(f"Error: ArcFace head not found at {ARCFACE_HEAD_MODEL_PATH}. Please ensure it exists.")
        raise
    except Exception as e:
        print(f"Error loading ArcFace head: {e}")
        raise

    print("All models loaded successfully.")


# --- Image Processing Function ---
async def process_iris_image(image_data_b64: str):
    """
    Decodes base64 image, performs iris segmentation and normalization,
    and extracts the feature embedding using the loaded models.
    Returns the normalized embedding tensor.
    """
    try:
        # Decode base64 image
        img_bytes = base64.b64decode(image_data_b64)
        img_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_np = np.array(img_pil) # Convert PIL Image to NumPy array (HWC, RGB)

        # Apply the iris pipeline (UNet segmentation + Daugman normalization)
        # This returns 64x256 grayscale uint8 image, or None if processing fails
        normalized_iris_gray = iris_pipeline_for_inference(img_np, unet_model, DEVICE)

        if normalized_iris_gray is None:
            raise ValueError("Iris segmentation and normalization failed for this image.")

        # Convert 64x256 grayscale to 3-channel RGB for EfficientNet input
        # and resize to IMG_SIZE (224x224)
        normalized_iris_rgb = cv2.cvtColor(normalized_iris_gray, cv2.COLOR_GRAY2RGB)
        
        # Apply transforms similar to validation transform in training
        # This prepares the image for EfficientNet
        transform_effnet = A.Compose([
            A.PadIfNeeded(min_height=256, min_width=256, border_mode=cv2.BORDER_CONSTANT, value=0, p=1.0),
            A.Resize(IMG_SIZE, IMG_SIZE),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ToTensorV2(),
        ])
        
        transformed = transform_effnet(image=normalized_iris_rgb)
        img_tensor = transformed['image'].unsqueeze(0).to(DEVICE) # Add batch dimension

        # Extract features using EfficientNet backbone
        with torch.no_grad():
            features = effnet_backbone(img_tensor)
            # Normalize features for cosine similarity
            embedding = F.normalize(features, p=2, dim=1).cpu().squeeze(0) # Remove batch dim, move to CPU
        
        return embedding

    except Exception as e:
        print(f"Error during iris image processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process iris image: {e}")



