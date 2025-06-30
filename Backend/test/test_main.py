import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import json
import requests
import io
from unittest.mock import AsyncMock
from fastapi import status
from postgrest.exceptions import APIError as PostgrestAPIError

# --- Global Patching ---
supabase_create_client_func_patcher = patch('Main.create_client')
mock_create_client_func = supabase_create_client_func_patcher.start()

mock_supabase_instance = MagicMock()
mock_create_client_func.return_value = mock_supabase_instance

deepface_lib_patcher = patch('Main.DeepFace')
mock_deepface_lib = deepface_lib_patcher.start()

httpx_async_client_patcher = patch('httpx.AsyncClient')
mock_httpx_async_client_cls = httpx_async_client_patcher.start()
mock_httpx_async_client_instance = MagicMock()
mock_httpx_async_client_cls.return_value.__aenter__.return_value = mock_httpx_async_client_instance
mock_httpx_async_client_instance.post.return_value.__aenter__.return_value.json.return_value = {"embedding": [0.5]*128}
mock_httpx_async_client_instance.post.return_value.__aenter__.return_value.raise_for_status.return_value = None

from Main import app, HTTPException, BackgroundTasks, authenticate_iris_from_api


def create_supabase_execute_response_obj(data=None, error=None, count=None, status_code=200):
    mock_response_obj = MagicMock()
    mock_response_obj.data = data if isinstance(data, list) else ([data] if data else [])
    mock_response_obj.error = error
    mock_response_obj.count = count
    mock_response_obj.status_code = status_code
    mock_response_obj.status = f"{status_code} OK" if status_code == 200 else f"{status_code} Error"
    return mock_response_obj


@pytest.fixture(scope="session", autouse=True)
def stop_global_patches():
    yield
    supabase_create_client_func_patcher.stop()
    deepface_lib_patcher.stop()
    httpx_async_client_patcher.stop()


@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict('os.environ', {
        'SUPABASE_URL': "http://mock-supabase.com",
        'SUPABASE_KEY': "mock_key",
        'BIOMETRIC_BUCKET': "mock-biometric-bucket",
        'IRIS_MODEL_API_URL': "http://localhost:8081"
    }):
        yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app=app, base_url="http://test") as tc:
        yield tc


@pytest.fixture
def mock_supabase_client(monkeypatch):
    mock = MagicMock()

    def create_execute_mock(data):
        execute_mock = MagicMock()
        execute_mock.return_value.data = data
        return execute_mock

    def table_side_effect(table_name):
        if table_name == "Biometric":
            chain = MagicMock()
            chain.select.return_value.eq.return_value.single.return_value.execute = create_execute_mock({
                "face_embedding": json.dumps([0.1] * 128),
                "face_image_url": "http://mock-url.com/stored_face_321.jpg",
                "iris_embedding": None
            })
            return chain

        elif table_name == "Customer":
            chain = MagicMock()
            chain.select.return_value.eq.return_value.single.return_value.execute = create_execute_mock({
                "Name": "Face", "SurName": "Only", "Email": "faceonly@example.com"
            })
            return chain

        elif table_name == "AuthenticationAttempts":
            chain = MagicMock()
            chain.insert.return_value.execute = create_execute_mock([{"id": 1}])
            return chain

        return MagicMock()

    mock.table.side_effect = table_side_effect
    monkeypatch.setattr("Main.supabase", mock)
    return mock


@pytest.fixture
def mock_deepface():
    mock_deepface_lib.reset_mock()
    mock_deepface_lib.represent = MagicMock(return_value=[{'embedding': [0.1] * 128}])
    return mock_deepface_lib


@pytest.fixture
def mock_requests_post():
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "embedding": [0.5] * 128,
            "message": "Mocked Iris auth success.",
            "is_authenticated": True,
            "similarity": 0.99,
            "matched_user_id": "mock_user",
            "best_similarity": 0.99,
            "detail": "Mocked success."
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_send_email():
    with patch('Main.send_authentication_report_email') as mock_send:
        yield mock_send

@pytest.fixture
def mock_iris_authenticator(monkeypatch):
    mock = AsyncMock()
    mock.return_value = {
        "is_authenticated": True,
        "similarity": 0.95,
        "matched_user_id": "789",
        "detail": "Iris match found with high confidence"
    }
    monkeypatch.setattr("Main.authenticate_iris_from_api", mock)
    return mock


@pytest.mark.asyncio
async def test_verify_customer_identity_face_success_only(
    client, mock_supabase_client, mock_deepface, mock_send_email, mock_requests_post
):
    customer_id = 321
    mock_uploaded_face_embedding = [0.1] * 128
    mock_deepface.represent.return_value = [{'embedding': mock_uploaded_face_embedding}]

    test_file_content = b"fake image data"
    files = {'face_image': ('face.jpg', test_file_content, 'image/jpeg')}
    data = {'customer_id': customer_id}

    response = client.post("/verify", files=files, data=data)

    assert response.status_code == 200
    assert response.json()["verified"] is True


@patch("Main.authenticate_iris_from_api", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_verify_customer_identity_iris_success_only(
    mock_iris_authenticator, client, mock_supabase_client, mock_send_email
):
    customer_id = 456
    test_image_bytes = b"fake iris image"

    mock_iris_authenticator.return_value = {
        "is_authenticated": True,
        "similarity": 0.92,
        "matched_user_id": str(customer_id),
        "detail": "Match found with high confidence"
    }

    mock_supabase_client.customer_execute.side_effect = lambda: MagicMock(
        data={"Name": "Iris", "SurName": "Only", "Email": "irisonly@example.com"}
    )
    mock_supabase_client.auth_insert_execute.side_effect = lambda: MagicMock(data=[{"id": 2}])

    files = {
        "iris_image": ("iris.jpg", io.BytesIO(test_image_bytes), "image/jpeg")
    }
    data = {
        "customer_id": str(customer_id)
    }

    response = client.post("/verify", files=files, data=data)

    assert response.status_code == 200
    assert response.json()["verified"] is True


@pytest.fixture
def mock_face_authenticator(monkeypatch):
    mock = AsyncMock()
    mock.return_value = AsyncMock(resturn_value= {
        "is_authenticated": True,
        "similarity": 0.93,
        "matched_user_id": "789",
        "detail": "Face match found with high confidence"
    })
    monkeypatch.setattr("Main.authenticate_face_from_api", mock)
    return mock

@pytest.mark.asyncio
async def test_verify_customer_identity_iris_face_success(
    client,
    mock_supabase_client,
    mock_send_email,
    mock_iris_authenticator,
    mock_face_authenticator,
):
    customer_id = 789
    test_iris_image_bytes = b"fake iris image"
    test_face_image_bytes = b"fake face image"

    # Mock Supabase customer data retrieval
    mock_supabase_client.customer_execute.side_effect = lambda: MagicMock(
        data={"Name": "IrisFace", "SurName": "User", "Email": "irisface@example.com"}
    )
    mock_supabase_client.auth_insert_execute.side_effect = lambda: MagicMock(data=[{"id": 3}])

    # Mock the iris API response as successful
    mock_iris_authenticator.return_value = {
        "is_authenticated": True,
        "similarity": 0.95,
        "matched_user_id": str(customer_id),
        "detail": "Iris match found with high confidence"
    }

    # Mock the face API response as successful
    mock_face_authenticator.return_value = {
        "is_authenticated": True,
        "similarity": 0.93,
        "matched_user_id": str(customer_id),
        "detail": "Face match found with high confidence"
    }

    files = {
        "iris_image": ("iris.jpg", io.BytesIO(test_iris_image_bytes), "image/jpeg"),
        "face_image": ("face.jpg", io.BytesIO(test_face_image_bytes), "image/jpeg"),
    }
    data = {
        "customer_id": str(customer_id)
    }

    response = client.post("/verify", files=files, data=data)

    assert response.status_code == 200
    response_json = response.json()

    # Expect verification success when both iris and face match
    assert response_json["verified"] is True
    assert "iris" in response_json["details"]
    assert "face" in response_json["details"]
    assert response_json["details"]["iris"]["is_authenticated"] is True
    assert response_json["details"]["face"]["is_authenticated"] is True

# Input Validation & Error Cases

@pytest.mark.asyncio
async def test_verify_missing_all_images(client):
    response = client.post("/verify", data={"customer_id": "123"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "At least one of face_image or iris_image must be provided."


@pytest.mark.asyncio
async def test_verify_missing_customer_id(client):
    test_face = io.BytesIO(b"fake image data")
    files = {"face_image": ("face.jpg", test_face, "image/jpeg")}

    response = client.post("/verify", files=files)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # FastAPI auto-validates required Form fields


@pytest.mark.asyncio
async def test_verify_invalid_customer_id_type(client):
    test_face = io.BytesIO(b"fake image data")
    files = {"face_image": ("face.jpg", test_face, "image/jpeg")}
    data = {"customer_id": "not-a-number"}

    response = client.post("/verify", files=files, data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_verify_unsupported_file_type(client):
    fake_file = io.BytesIO(b"This is not an image")
    files = {"face_image": ("malicious.exe", fake_file, "application/octet-stream")}
    data = {"customer_id": "123"}

    response = client.post("/verify", files=files, data=data)
    # Still should process, as the backend currently doesn't block MIME types.
    # If you want to enforce, you'd need to add validation.
    assert response.status_code == 200 or response.status_code == 400


@pytest.mark.asyncio
async def test_verify_empty_file(client):
    empty_file = io.BytesIO(b"")
    files = {"iris_image": ("iris.jpg", empty_file, "image/jpeg")}
    data = {"customer_id": "123"}

    response = client.post("/verify", files=files, data=data)
    # Should return a failure response, not crash
    assert response.status_code == 200
    assert response.json()["verified"] is False