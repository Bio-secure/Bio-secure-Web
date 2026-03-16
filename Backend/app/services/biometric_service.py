import cv2
import aiofiles, os, json, base64, shutil, traceback, httpx
from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
import httpx

from services.iris_service import extract_iris_features
from utils.fetch_customer import fetch_customer_name
from configs.settings import supabase, DeepFace, BIOMETRIC_BUCKET, IRIS_MODEL_API_URL, SUPABASE_URL

# --- Utility: async save file ---
async def save_file_temp(upload: UploadFile, suffix: str):
    ext = upload.filename.split('.')[-1]
    path = f"{suffix}_temp.{ext}"
    async with aiofiles.open(path, "wb") as f:
        content = await upload.read()
        await f.write(content)
    return path, ext


# --- Handle Face ---
async def process_face(national_id: str, name: str, face_image: UploadFile):
    """
    Processes a face image, generates an embedding, and uploads it to Supabase.
    """
    # 1. Save the uploaded file to a temporary location
    file_extension = face_image.filename.split('.')[-1]
    temp_filepath = os.path.join(f"{national_id}_face.{file_extension}")
    
    try:
        # Use aiofiles to asynchronously write the file to disk
        async with aiofiles.open(temp_filepath, 'wb') as f:
            while chunk := await face_image.read(1024):
                await f.write(chunk)
    except Exception as e:
        print(f"Error saving temp file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image file.")

    # 2. Generate face embedding using DeepFace (CPU-bound)
    try:
        embedding_objs = await run_in_threadpool(
            DeepFace.represent,
            img_path=temp_filepath,
            model_name="VGG-Face",
            enforce_detection=False
        )
        if not embedding_objs or not embedding_objs[0].get("embedding"):
            raise ValueError("No face embedding generated.")
        
        embedding = embedding_objs[0].get("embedding")
    except Exception as e:
        print(f"DeepFace processing failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process face image: {e}")

    # 3. Upload the image to Supabase and get the public URL
    # We will upload the image using a robust, atomic approach.
    file_path_in_bucket = f"face/{national_id}_{name}.{file_extension}"
    
    try:
        # Uploading/Updating a file is an I/O operation, so wrap it in run_in_threadpool
        # Use the `update` method for upsert functionality (creating or overwriting)
        with open(temp_filepath, 'rb') as f:
            await run_in_threadpool(
                supabase.storage.from_(BIOMETRIC_BUCKET).update,
                file_path_in_bucket,
                f.read(),
                {"upsert": "true", "content-type": face_image.content_type}
            )

        # 4. Get the public URL for the uploaded file
        # This call is synchronous and does not require run_in_threadpool
        url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(file_path_in_bucket)
    
    except Exception as e:
        print(f"Supabase upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image to storage.")
    finally:
        # 5. Clean up the temporary file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

    return url, embedding


def preprocess_iris(img_path, size=240):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image at {img_path}")

    # Histogram equalization for illumination normalization
    img = cv2.equalizeHist(img)

    # Optional: detect iris/pupil center using Hough Circle (can improve later)
    # Here we just resize to a fixed size for stability
    img = cv2.resize(img, (size, size))

    return img


# --- Handle Iris ---
# --- Process a single iris (left or right) ---
async def process_single_iris(national_id: str, name: str, image: UploadFile, eye_type: str):
    try:
        # Save file temporarily
        ext = image.filename.split('.')[-1]
        filename = f"{national_id}_{name}_{eye_type}.{ext}"
        path = f"temp_{filename}"

        async with aiofiles.open(path, "wb") as f:
            content = await image.read()
            await f.write(content)

        # Step 1: Preprocess
        preprocessed_img = preprocess_iris(path)
        cv2.imwrite(path, preprocessed_img)  # overwrite temp file for feature extractor

        # Step 2: Extract iris embedding
        code, mask = await run_in_threadpool(extract_iris_features, path)
        embedding = {"code": code.tolist(), "mask": mask.tolist()}

        # Step 3: Upload to Supabase
        try:
            async with aiofiles.open(path, "rb") as f:
                file_bytes = await f.read()

            supabase.storage.from_(BIOMETRIC_BUCKET).upload(
                file=file_bytes,
                path=f"iris/{filename}",
                file_options={"content-type": image.content_type, "upsert": "true"}
            )

            image_url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(f"iris/{filename}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Supabase upload failed: {e}")
        finally:
            if os.path.exists(path):
                os.remove(path)

        return image_url, embedding

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Iris processing failed: {e}")


# --- Main function to process left and right iris ---
async def process_iris(national_id: str, name: str, left_iris_image: UploadFile = None, right_iris_image: UploadFile = None):
    left_url, left_embedding = None, None
    right_url, right_embedding = None, None

    if left_iris_image:
        left_url, left_embedding = await process_single_iris(national_id, name, left_iris_image, "left")

    if right_iris_image:
        right_url, right_embedding = await process_single_iris(national_id, name, right_iris_image, "right")

    return {
        "left_iris": {"url": left_url, "embedding": left_embedding},
        "right_iris": {"url": right_url, "embedding": right_embedding}
    }

# Register Face Biometric
async def register_biometric_face_service(national_id: str, face_image: UploadFile):
    if not DeepFace:
        raise HTTPException(status_code=503, detail="Face recognition unavailable.")

    first, last = await fetch_customer_name(national_id)
    sanitized_name = f"{first}_{last}".replace(" ", "_")

    face_url, face_embedding = await process_face(national_id, sanitized_name, face_image)

    payload = {
        "National_ID": int(national_id),
        "face_image_url": face_url,
        "face_embedding": json.dumps(face_embedding)
    }

    try:
        await run_in_threadpool(
            supabase.table("Biometric").upsert(payload, on_conflict="National_ID").execute
        )
        return {"message": f"Biometric data registered successfully for ID {national_id}."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")

# Register Iris Biometric
async def register_biometric_iris_service(national_id: str, left_image: UploadFile, right_image: UploadFile):
    first, last = await fetch_customer_name(national_id)
    sanitized_name = f"{first}_{last}".replace(" ", "_")

    # Step 1: Process both iris images and get their data
    iris_data = await process_iris(national_id, sanitized_name, left_image, right_image)

    # Step 2: Prepare the payload with iris data
    payload = {
        "National_ID": int(national_id),
        "iris_left_image_url": iris_data["left_iris"]["url"],
        "iris_left_embedding": iris_data["left_iris"]["embedding"] if iris_data["left_iris"]["embedding"] else None,
        "iris_right_image_url": iris_data["right_iris"]["url"],
        "iris_right_embedding": iris_data["left_iris"]["embedding"] if iris_data["right_iris"]["embedding"] else None,
    }

    # Step 3: Upsert the data to Supabase
    try:
        await run_in_threadpool(
            supabase.table("Biometric").upsert(payload, on_conflict="National_ID").execute
        )
        return {"message": f"Biometric iris data registered successfully for ID {national_id}."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")
