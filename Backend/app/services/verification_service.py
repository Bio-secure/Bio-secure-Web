import os, base64, datetime, aiofiles
from fastapi import HTTPException, UploadFile, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
import httpx

from services.face_service import authenticate_face_from_api
from configs.settings import supabase, IRIS_MODEL_API_URL
from utils.email_utils import send_authentication_report_email


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
    ext = upload.filename.split('.')[-1]
    path = f"{suffix}_query.{ext}"
    contents = await upload.read()
    async with aiofiles.open(path, "wb") as f:
        f.write(contents)
    return path


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
    customer_id: int,
    background_tasks: BackgroundTasks,
    face_image: UploadFile = None,
    iris_image: UploadFile = None
):
    if not face_image and not iris_image:
        raise HTTPException(
            status_code=400,
            detail="At least one of face_image or iris_image must be provided."
        )

    # Step 1: Fetch customer
    customer = await fetch_customer(customer_id)
    if not customer:
        await log_failure(customer_id, "Biometric Auth Failure", "Customer Not Found")
        raise HTTPException(status_code=404, detail="Customer not found for verification.")

    customer_name = customer.get("Name", "Unknown")
    customer_surname = customer.get("SurName", "Customer")
    customer_email = customer.get("Email")

    # Step 2: Biometric checks
    face_is_match, face_details = await verify_face(customer_id, face_image)
    iris_is_match, iris_details = await verify_iris(customer_id, iris_image)

    # Step 3: Combine result
    overall_verified = (
        (face_is_match and iris_is_match)
        if (face_image and iris_image)
        else (face_is_match or iris_is_match)
    )

    if not overall_verified:
        await log_failure(customer_id, customer_name, customer_surname)

    # Step 4: Send email
    if customer_email:
        biometric_type = " and ".join(
            filter(None, [face_image and "face", iris_image and "iris"])
        )
        background_tasks.add_task(
            send_authentication_report_email,
            customer_email,
            f"{customer_name} {customer_surname}".strip(),
            biometric_type,
            overall_verified,
            {"face": face_details, "iris": iris_details},
        )

    return {
        "verified": overall_verified,
        "message": "Verification " + ("Succeeded" if overall_verified else "Failed"),
        "details": {"face": face_details, "iris": iris_details},
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


async def verify_iris(customer_id: int, iris_image: UploadFile):
    if not iris_image:
        return False, {}
    path = await save_temp_file(iris_image, f"{customer_id}_iris")
    try:
        async with aiofiles.open(path, "rb") as f:
            iris_b64 = base64.b64encode(f.read()).decode("utf-8")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{IRIS_MODEL_API_URL}/verify-iris",
                json={"customer_id": str(customer_id), "image_data": iris_b64},
                timeout=30.0,
            )
            details = resp.json()
            return details.get("is_authenticated", False), details
    finally:
        if os.path.exists(path):
            os.remove(path)
