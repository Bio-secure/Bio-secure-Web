import aiofiles, os, json, base64, shutil, traceback, httpx
from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from utils.fetch_customer import fetch_customer_name
from configs.settings import supabase, DeepFace, BIOMETRIC_BUCKET, IRIS_MODEL_API_URL

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
    path, ext = await save_file_temp(face_image, f"{national_id}_face")
    filename = f"face/{national_id}_{name}.{ext}"

    try:
        # Generate face embedding
        embedding_objs = await run_in_threadpool(
            DeepFace.represent,
            img_path=path,
            model_name="VGG-Face",
            enforce_detection=False
        )
        embedding = embedding_objs[0].get("embedding")
        if not embedding:
            raise HTTPException(status_code=400, detail="No face embedding generated.")

        # Read file and upload to Supabase
        async with aiofiles.open(path, "rb") as f:
            file_bytes = await f.read()
            await run_in_threadpool(
                supabase.storage.from_(BIOMETRIC_BUCKET).upload,
                filename,
                file_bytes,   
                {"upsert": "true"}
            )

        # Get public URL
        url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(filename)
        return url, embedding

    finally:
        if os.path.exists(path):
            os.remove(path)



# --- Handle Iris ---
async def process_iris(national_id: str, name: str, iris_image: UploadFile):
    path, ext = await save_file_temp(iris_image, f"{national_id}_iris")
    filename = f"iris/{national_id}_{name}.{ext}"

    try:
        async with aiofiles.open(path, "rb") as f:
            b64 = base64.b64encode(await f.read()).decode()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{IRIS_MODEL_API_URL}/get-iris-embedding",
                json={"image_data": b64},
                timeout=30.0
            )
            response.raise_for_status()
            iris_data = response.json()
            embedding = iris_data.get("embedding")
            if not embedding:
                raise HTTPException(status_code=400, detail="No iris embedding returned.")

        async with aiofiles.open(path, "rb") as f:
            await run_in_threadpool(
                supabase.storage.from_(BIOMETRIC_BUCKET).upload,
                f,
                filename,
                {"upsert": "true"}
            )
        url = supabase.storage.from_(BIOMETRIC_BUCKET).get_public_url(filename)
        return url, embedding
    finally:
        if os.path.exists(path):
            os.remove(path)

async def register_biometric_service(national_id: str, face_image: UploadFile, iris_image: UploadFile = None):
    if not DeepFace:
        raise HTTPException(status_code=503, detail="Face recognition unavailable.")

    first, last = await fetch_customer_name(national_id)
    sanitized_name = f"{first}_{last}".replace(" ", "_")

    face_url, face_embedding = await process_face(national_id, sanitized_name, face_image)

    iris_url, iris_embedding = (None, None)
    if iris_image:
        iris_url, iris_embedding = await process_iris(national_id, sanitized_name, iris_image)

    payload = {
        "National_ID": int(national_id),
        "face_image_url": face_url,
        "face_embedding": json.dumps(face_embedding),
        "iris_image_url": iris_url,
        "iris_embedding": json.dumps(iris_embedding) if iris_embedding else None,
    }

    try:
        await run_in_threadpool(
            supabase.table("Biometric").upsert(payload, on_conflict="National_ID").execute
        )
        return {"message": f"Biometric data registered successfully for ID {national_id}."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"DB insert failed: {e}")
