import json
import os, base64, datetime, aiofiles
from fastapi import HTTPException, UploadFile, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
import httpx
import numpy as np

from services.face_service import authenticate_face_from_api
from configs.settings import supabase, IRIS_MODEL_API_URL
from utils.email_utils import send_authentication_report_email
from scipy.spatial.distance import cosine
from services.iris_service import extract_iris_features, match_iris

# --- Helpers ---

async def fetch_customer(customer_id: int):
    response = await run_in_threadpool(
        lambda: supabase.table("Customer")
                        .select("Name, SurName, Email")
                        .eq("National_ID", customer_id)
                        .single()
                        .execute()
    )
    if not response.data:
        return None
    return response.data


async def save_temp_file(upload: UploadFile, suffix: str):
    try:
        # Define a temporary directory at the project root
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Build the file path using a unique name and the temporary directory
        ext = upload.filename.split('.')[-1]
        file_path = os.path.join(temp_dir, f"{suffix}_query.{ext}")
        
        # Asynchronously read the file content
        contents = await upload.read()
        
        # Asynchronously write the file content to the temp path
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)
            
        return file_path
    except Exception as e:
        # Re-raise the exception with a more descriptive error message
        raise Exception(f"Failed to save temporary file: {e}")


async def log_failure(customer_id, name, surname):
    payload = {
        "Customer_National_ID": customer_id,
        "Name": name,
        "SurName": surname,
        "Result": False,
        "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    await run_in_threadpool(lambda: supabase.table("CustomerLogs").insert([payload]).execute())

# --- Main service ---
async def verify_customer_identity_service(
    national_id: str,
    background_tasks: BackgroundTasks,
    face_image: UploadFile = None,
    left_iris_image: UploadFile = None,
    right_iris_image: UploadFile = None
):
    # Initial check for at least one biometric input
    if not face_image and not (left_iris_image or right_iris_image):
        raise HTTPException(400, detail="At least one biometric input must be provided.")
    
    print("Received customer_id:", national_id)
    print("Face image:", face_image)
    print("Left iris image:", left_iris_image)
    print("Right iris image:", right_iris_image)

    # Fetch customer
    customer = await fetch_customer(national_id)
    if not customer:
        await log_failure(national_id, "Unknown", "Unknown")
        raise HTTPException(404, detail="Customer not found.")

    customer_name = customer.get("Name", "Unknown")
    customer_surname = customer.get("SurName", "Customer")
    customer_email = customer.get("Email")

    # Initialize results
    face_result = {"is_authenticated": False, "message": "No face image provided."}
    left_iris_result = {"is_authenticated": False, "message": "No left iris image provided."}
    right_iris_result = {"is_authenticated": False, "message": "No right iris image provided."}
    
    # Perform Face Verification if an image is provided
    if face_image:
        face_result = await verify_face(national_id, face_image)

    # Perform Iris Verification if images are provided
    if left_iris_image:
        left_iris_result = await verify_iris(national_id, left_iris_image, "left")
    
    if right_iris_image:
        right_iris_result = await verify_iris(national_id, right_iris_image, "right")

    overall_verified = False  # start with False

    # Check irises first
    iris_verified = (left_iris_result["is_authenticated"] or right_iris_result["is_authenticated"])

    # Only consider face if iris verification passes
    if iris_verified:
        if face_image:
            # If face provided, require it to also pass
            overall_verified = face_result["is_authenticated"]
        else:
            # If no face provided, iris alone is enough
            overall_verified = True
    else:
        # Neither iris passed
        overall_verified = False

    # Log the failure if needed
    if not overall_verified:
        await log_failure(national_id, customer_name, customer_surname)

    # Prepare Final Response
    final_details = {
        "face": face_result,
        "left_iris": left_iris_result,
        "right_iris": right_iris_result
    }

    if customer_email:
        biometric_type = " and ".join(
            filter(None, [
                face_image and "face",
                (left_iris_image or right_iris_image) and "iris"
            ])
        )
        background_tasks.add_task(
            send_authentication_report_email,
            customer_email,
            f"{customer_name} {customer_surname}".strip(),
            biometric_type,
            overall_verified,
            final_details,
        )

    return {
        "verified": overall_verified,
        "message": "Verification Succeeded" if overall_verified else "Verification Failed",
        "details": final_details,
    }


# --- Extracted Helpers ---

async def verify_face(customer_id: int, face_image: UploadFile):
    if not face_image:
        return {"is_authenticated": False, "details": {}}

    path = await save_temp_file(face_image, f"{customer_id}_face")
    try:
        details = await authenticate_face_from_api(customer_id, path) or {}
        return {"is_authenticated": details.get("is_authenticated", False), "details": details}
    finally:
        if os.path.exists(path):
            os.remove(path)


async def verify_iris(customer_id: str, iris_image: UploadFile, eye_type: str):
    if not iris_image:
        return {"is_authenticated": False, "message": "No iris image provided."}

    path = await save_temp_file(iris_image, f"{customer_id}_{eye_type}_iris")
    try:
        # Step 1: Extract features from the uploaded image
        uploaded_features = await run_in_threadpool(
            extract_iris_features, image_path=path
        )
        if not uploaded_features:
            return {"is_authenticated": False, "message": "Failed to extract iris features."}

        u_code, u_mask = uploaded_features
        print(f"Uploaded {eye_type} code shape: {u_code.shape}, mask shape: {u_mask.shape}")

        # Step 2: Get stored features from the database
        db_response = await run_in_threadpool(
            lambda: supabase.table("Biometric")
            .select(f"iris_{eye_type}_embedding")
            .eq("National_ID", customer_id)
            .single()
            .execute()
        )

        stored_features = db_response.data.get(f"iris_{eye_type}_embedding")

        if not stored_features:
            return {"is_authenticated": False, "message": f"No registered {eye_type} iris data."}

        # Handle stringified JSON
        if isinstance(stored_features, str):
            stored_features = json.loads(stored_features)

        # Handle dict with 'code' and 'mask'
        if isinstance(stored_features, dict):
            s_code = np.array(stored_features["code"], dtype=np.uint8)
            s_mask = np.array(stored_features["mask"], dtype=np.uint8)
            stored_features = (s_code, s_mask)

        # Handle tuple (code, mask)
        elif isinstance(stored_features, tuple) and len(stored_features) == 2:
            s_code, s_mask = stored_features

        else:
            return {"is_authenticated": False, "message": f"Stored {eye_type} iris data is invalid."}

        print(f"Stored {eye_type} code shape: {s_code.shape}, mask shape: {s_mask.shape}")

        # Step 3: Compare features
        match_details = match_iris(uploaded_features, stored_features)

        return {
            "is_authenticated": match_details["is_match"],
            "distance": match_details["distance"],
            "message": f"{eye_type.capitalize()} Iris Verified"
            if match_details["is_match"]
            else f"{eye_type.capitalize()} Iris Verification Failed"
        }

    except Exception as e:
        return {"is_authenticated": False, "message": f"{eye_type.capitalize()} Iris verification error: {e}"}

    finally:
        if os.path.exists(path):
            os.remove(path)
