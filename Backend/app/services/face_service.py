import json
import traceback
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from scipy.spatial.distance import cosine

from configs.settings import supabase, DeepFace, FACE_DISTANCE_THRESHOLD


# --- Step 1: Generate embedding from face image ---
async def generate_face_embedding(face_image_path: str):
    try:
        embedding_objs = await run_in_threadpool(
            DeepFace.represent,
            img_path=face_image_path,
            model_name="VGG-Face",
            enforce_detection=True
        )
        if not embedding_objs:
            return None
        return embedding_objs[0].get("embedding")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate embedding: {e}")


# --- Step 2: Get stored embedding from DB ---
async def get_stored_face_embedding(customer_id: int):
    try:
        db_response = await run_in_threadpool(
            lambda: supabase.table("Biometric")
                            .select("face_embedding, face_image_url")
                            .eq("National_ID", customer_id)
                            .single()
                            .execute()
        )
        if not db_response.data or not db_response.data.get("face_embedding"):
            return None, None

        stored_data = db_response.data.get("face_embedding")
        image_url = db_response.data.get("face_image_url")

        # Handle legacy case: JSON string vs JSON array
        if isinstance(stored_data, str):
            stored_embedding = json.loads(stored_data)
        else:
            stored_embedding = stored_data

        return stored_embedding, image_url
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching stored embedding: {e}")


# --- Step 3: Compare embeddings ---
def compare_embeddings(uploaded_embedding, stored_embedding):
    if uploaded_embedding is None or stored_embedding is None:
        return False, None
    distance = cosine(uploaded_embedding, stored_embedding)
    is_match = bool(distance < FACE_DISTANCE_THRESHOLD)
    return is_match, distance


async def authenticate_face_from_api(customer_id: int, face_image_path: str):
    try:
        uploaded_embedding = await generate_face_embedding(face_image_path)
        if not uploaded_embedding:
            return {"is_authenticated": False, "message": "No face detected."}

        stored_embedding, match_url = await get_stored_face_embedding(customer_id)
        if not stored_embedding:
            return {"is_authenticated": False, "message": "No registered face biometric data."}

        is_match, distance = compare_embeddings(uploaded_embedding, stored_embedding)

        return {
            "is_authenticated": is_match,
            "distance": float(distance) if distance is not None else None,
            "image_url": match_url,
            "message": "Face Verified Successfully" if is_match else "Face Verification Failed"
        }
    except Exception as e:
        return {"is_authenticated": False, "message": f"Face verification error: {e}"}