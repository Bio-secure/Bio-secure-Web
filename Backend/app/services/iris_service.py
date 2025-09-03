import json
from fastapi import HTTPException
import requests

from configs.settings import IRIS_MODEL_API_URL


def authenticate_iris_from_api(user_id: str, image_data_b64: str) -> dict:
    headers = {"Content-Type": "application/json"}
    payload = {"user_id": user_id, "image_data": image_data_b64}
    response = None
    try:
        response = requests.post(f"{IRIS_MODEL_API_URL}/authenticate-iris", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Iris Model API's /authenticate-iris: {e}")
        if response is not None and response.text:
            try:
                error_detail = response.json().get("detail", response.text)
            except json.JSONDecodeError:
                error_detail = response.text
            raise HTTPException(status_code=response.status_code, detail=f"Iris API error: {error_detail}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to communicate with Iris API: {e}")