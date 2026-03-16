import os
import json
import datetime
import aiofiles
import numpy as np
import cv2
from fastapi import HTTPException, UploadFile, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from services.face_service import authenticate_face_from_api
from services.iris_service import extract_iris_features, match_iris
from configs.settings import supabase
from utils.email_utils import send_authentication_report_email

# --- Helpers ---
async def save_temp_file(upload: UploadFile, suffix: str):
    os.makedirs("temp", exist_ok=True)
    ext = upload.filename.split('.')[-1]
    path = os.path.join("temp", f"{suffix}.{ext}")
    contents = await upload.read()
    async with aiofiles.open(path, "wb") as f:
        await f.write(contents)
    return path

async def fetch_customer(customer_id: int):
    response = await run_in_threadpool(
        lambda: supabase.table("Customer")
                        .select("Name, SurName, Email")
                        .eq("National_ID", customer_id)
                        .single()
                        .execute()
    )
    return response.data if response.data else None

async def log_failure(customer_id, name, surname):
    payload = {
        "Customer_National_ID": customer_id,
        "Name": name,
        "SurName": surname,
        "Result": False,
        "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    await run_in_threadpool(lambda: supabase.table("CustomerLogs").insert([payload]).execute())

# --- Iris Verification ---
async def verify_single_iris(customer_id: str, image: UploadFile, eye_type: str):
    if not image:
        return {"is_authenticated": False, "message": f"No {eye_type} iris image provided.", "distance": None}

    path = await save_temp_file(image, f"{customer_id}_{eye_type}_iris")
    try:
        # Preprocess + extract features
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        img = cv2.equalizeHist(img)
        img = cv2.resize(img, (240, 240))
        uploaded_features = await run_in_threadpool(extract_iris_features, path)

        # Load stored embedding from Supabase
        db_response = await run_in_threadpool(
            lambda: supabase.table("Biometric")
            .select(f"iris_{eye_type}_embedding")
            .eq("National_ID", customer_id)
            .single()
            .execute()
        )
        stored_features = db_response.data.get(f"iris_{eye_type}_embedding")
        if not stored_features:
            return {"is_authenticated": False, "message": f"No stored {eye_type} iris.", "distance": None}

        if isinstance(stored_features, str):
            stored_features = json.loads(stored_features)

        s_code = np.array(stored_features["code"], dtype=np.uint8)
        s_mask = np.array(stored_features["mask"], dtype=np.uint8)
        stored_features_tuple = (s_code, s_mask)

        match_details = match_iris(uploaded_features, stored_features_tuple)

        return {
            "is_authenticated": match_details["is_match"],
            "distance": match_details["distance"],
            "message": f"{eye_type.capitalize()} Iris Verified" if match_details["is_match"] else f"{eye_type.capitalize()} Iris Verification Failed"
        }
    finally:
        if os.path.exists(path):
            os.remove(path)

# --- Face Verification ---
async def verify_face(customer_id: int, face_image: UploadFile):
    if not face_image:
        return {"is_authenticated": False, "message": "No face image provided."}

    path = await save_temp_file(face_image, f"{customer_id}_face")
    try:
        details = await authenticate_face_from_api(customer_id, path)
        return {"is_authenticated": details.get("is_authenticated", False), "details": details, "message": "Face Verified" if details.get("is_authenticated") else "Face Verification Failed"}
    finally:
        if os.path.exists(path):
            os.remove(path)

# --- Main Verification Service ---
async def verify_customer_identity_service(
    national_id: str,
    background_tasks: BackgroundTasks,
    face_image: UploadFile = None,
    left_iris_image: UploadFile = None,
    right_iris_image: UploadFile = None,
    iris_threshold: float = 0.35  # adjustable threshold
):
    if not national_id.isdigit():
        raise HTTPException(status_code=404, detail="Invalid National ID")
    if not any([face_image, left_iris_image, right_iris_image]):
        raise HTTPException(status_code=400, detail="At least one image must be provided")

    customer = await fetch_customer(national_id)
    if not customer:
        await log_failure(national_id, "Unknown", "Unknown")
        raise HTTPException(status_code=404, detail="Customer not found")

    name = customer.get("Name", "Unknown")
    surname = customer.get("SurName", "Customer")
    email = customer.get("Email")

    # --- Face Verification ---
    face_result = await verify_face(national_id, face_image) if face_image else {
        "is_authenticated": False, "message": "No face image provided.", "distance": None
    }

    # --- Iris Verification ---
    left_result = await verify_single_iris(national_id, left_iris_image, "left")
    right_result = await verify_single_iris(national_id, right_iris_image, "right")

    # --- Combine Iris Results with Weighting ---
    iris_verified = False
    iris_distances = []
    if left_iris_image and left_result.get("distance") is not None:
        iris_distances.append(left_result["distance"])
    if right_iris_image and right_result.get("distance") is not None:
        iris_distances.append(right_result["distance"])

    if iris_distances:
        avg_iris_distance = sum(iris_distances) / len(iris_distances)
        iris_verified = avg_iris_distance < iris_threshold
    else:
        avg_iris_distance = None  # No iris data

    # --- Overall Verification ---
    overall_verified = face_result["is_authenticated"]
    if iris_distances:
        overall_verified = overall_verified and iris_verified

    # --- Update iris messages ---
    if left_iris_image:
        left_result["is_authenticated"] = left_result.get("distance", 1.0) < iris_threshold
        left_result["message"] = f"Left Iris Verified" if left_result["is_authenticated"] else f"Left Iris Verification Failed"
    if right_iris_image:
        right_result["is_authenticated"] = right_result.get("distance", 1.0) < iris_threshold
        right_result["message"] = f"Right Iris Verified" if right_result["is_authenticated"] else f"Right Iris Verification Failed"

    # --- Log failure ---
    if not overall_verified:
        await log_failure(national_id, name, surname)

    # --- Email report ---
    if email:
        biometric_type = ", ".join(filter(None, [
            "face" if face_image else None,
            "iris" if iris_distances else None
        ]))
        background_tasks.add_task(
            send_authentication_report_email,
            email,
            f"{name} {surname}".strip(),
            biometric_type,
            overall_verified,
            {"face": face_result, "left_iris": left_result, "right_iris": right_result},
        )

    return {
        "verified": overall_verified,
        "message": "Verification Succeeded" if overall_verified else "Verification Failed",
        "details": {"face": face_result, "left_iris": left_result, "right_iris": right_result, "avg_iris_distance": avg_iris_distance},
    }
