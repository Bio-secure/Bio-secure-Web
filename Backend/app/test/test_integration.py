import io
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import BackgroundTasks
from starlette.datastructures import UploadFile as StarletteUploadFile
import pytest
import numpy as np
from starlette.testclient import TestClient
from PIL import Image
from services.verification_service import verify_customer_identity_service, supabase
from Main import app


# --------------------------
# Fixtures
# --------------------------

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_verification_dependencies(monkeypatch):
    print("\n[MOCK] verification dependencies applied")

    # Fake face API
    async def fake_authenticate_face_from_api(customer_id, path):
        print("[MOCK] authenticate_face_from_api called")
        return {"is_authenticated": True}

    # Fake iris extractor
    def fake_extract_iris_features(image_path):
        print("[MOCK] extract_iris_features called")
        return (np.ones((5, 5), dtype=np.uint8), np.zeros((5, 5), dtype=np.uint8))

    # Fake iris matcher
    def fake_match_iris(uploaded, stored):
        print("[MOCK] match_iris called")
        return {"is_match": True, "distance": 0.05}

    # Fake supabase
    class FakeSupabase:
        def table(self, name):
            print(f"[MOCK] supabase.table({name})")
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def single(self):
            return self

        def insert(self, *args, **kwargs):
            print("[MOCK] insert into table")
            return self

        def execute(self):
            # Return mock data depending on context
            return type("Resp", (), {"data": {
                "Name": "John",
                "SurName": "Doe",
                "Email": "john@example.com",
                "iris_left_embedding": {
                    "code": np.ones((5, 5), dtype=np.uint8).tolist(),
                    "mask": np.zeros((5, 5), dtype=np.uint8).tolist(),
                },
                "iris_right_embedding": {
                    "code": np.ones((5, 5), dtype=np.uint8).tolist(),
                    "mask": np.zeros((5, 5), dtype=np.uint8).tolist(),
                }
            }})()


    # Patch everything at the import site in verification_service.py
    monkeypatch.setattr("services.verification_service.authenticate_face_from_api", fake_authenticate_face_from_api)
    monkeypatch.setattr("services.verification_service.extract_iris_features", fake_extract_iris_features)
    monkeypatch.setattr("services.verification_service.match_iris", fake_match_iris)
    monkeypatch.setattr("services.verification_service.supabase", FakeSupabase())

#-- Authentication Report Mocks
@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("services.transaction_service.supabase") as mock:
        yield mock


@pytest.fixture
def mock_email_service():
    """Fixture to mock email sending."""
    with patch("services.verification_service.send_authentication_report_email") as mock_email:
        yield mock_email

# --------------------------
# Helpers
# --------------------------

def create_fake_image_bytes(color="white", size=(10, 10), mode="RGB"):
    """Returns a BytesIO object containing a simple in-memory image."""
    img = Image.new(mode, size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def create_fake_iris_bytes():
    return create_fake_image_bytes(color=128, size=(20, 20), mode="L")

# --------------------------
# Integration Tests
# --------------------------

def test_verify_face_only(client):
    files = {"face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg")}
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "face" in json_resp["details"]
    assert "left_iris" in json_resp["details"]
    assert "right_iris" in json_resp["details"]

@pytest.mark.asyncio
async def test_verify_iris_only(client):
    files = {
        "left_image": ("left.jpg", create_fake_iris_bytes(), "image/jpeg"),
        "right_image": ("right.jpg", create_fake_iris_bytes(), "image/jpeg")
    }
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "face" in json_resp["details"]
    assert "left_iris" in json_resp["details"]
    assert "right_iris" in json_resp["details"]

@pytest.mark.asyncio
async def test_verify_face_and_iris(client):
    files = {
        "face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg"),
        "left_image": ("left.jpg", create_fake_iris_bytes(), "image/jpeg"),
        "right_image": ("right.jpg", create_fake_iris_bytes(), "image/jpeg")
    }
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "face" in json_resp["details"]
    assert "left_iris" in json_resp["details"]
    assert "right_iris" in json_resp["details"]

@pytest.mark.asyncio
async def test_verify_missing_all_images(client):
    data = {"national_id": "12345"}
    response = client.post("/verify", data=data)
    assert response.status_code == 400  # no images provided

@pytest.mark.asyncio
async def test_verify_empty_file(client):
    empty_file = io.BytesIO(b"")
    files = {"face_image": ("empty.jpg", empty_file, "image/jpeg")}
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_verify_unsupported_file_type(client):
    fake_file = io.BytesIO(b"not an image")
    files = {"face_image": ("malicious.exe", fake_file, "application/octet-stream")}
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code in [400, 422]


# NEGATIVE INTEGRATION TESTS

def test_verify_missing_national_id(client):
    files = {"face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg")}
    response = client.post("/verify", files=files)
    assert response.status_code in (400, 422)
    body = response.json()
    assert "error" in body or "message" in body or "detail" in body


def test_verify_no_images(client):
    data = {"national_id": "12345"}
    response = client.post("/verify", data=data)
    assert response.status_code == 400
    body = response.json()
    assert "error" in body or "message" in body or "detail" in body


def test_verify_invalid_national_id(client, mocker):
    mocker.patch("services.verification_service.fetch_customer", return_value=None)

    files = {"face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg")}
    data = {"national_id": "abc"}  # not numeric

    response = client.post("/verify", files=files, data=data)

    assert response.status_code == 404

    body = response.json()
    assert "error" in body or "message" in body or "detail" in body


def test_verify_corrupted_image(client):
    files = {"face_image": ("not_image.jpg", b"this_is_not_an_image", "image/jpeg")}
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code == 400


def test_verify_missing_right_iris(client):
    files = {"left_image": ("left.jpg", create_fake_iris_bytes(), "image/jpeg")}
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)
    assert response.status_code in (400, 422)
    body = response.json()
    assert "right" in str(body).lower()


def test_verify_biometric_mismatch(client, mocker):
    files = {
        "left_image": ("left.jpg", create_fake_iris_bytes(), "image/jpeg"),
        "right_image": ("right.jpg", create_fake_iris_bytes(), "image/jpeg"),
    }
    data = {"national_id": "12345"}

    # Mock match_iris to always return False
    mocker.patch("services.verification_service.match_iris", return_value={"is_match": False, "distance": 1.0, "best_shift": 0})

    response = client.post("/verify", files=files, data=data)
    assert response.status_code == 401
    body = response.json()
    assert "not matched" in str(body).lower()

# --------------------------

# Authentication Notification Access

@pytest.mark.asyncio
async def test_email_sent_on_successful_verification(client, monkeypatch, mock_email_service):
    # Override the autouse FakeSupabase to return Alice
    class AliceSupabase:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def single(self): return self
        def insert(self, *a, **kw): return self
        def execute(self):
            return type("Resp", (), {"data": {
                "National_ID": "12345",
                "Name": "Alice",
                "SurName": "Smith",
                "Email": "alice@example.com"
            }})()

    monkeypatch.setattr("services.verification_service.supabase", AliceSupabase())

    # Simulate a successful face verification
    files = {"face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg")}
    data = {"national_id": "12345"}
    response = client.post("/verify", files=files, data=data)

    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["verified"] is True

    # Validate email
    mock_email_service.assert_called_once()
    email_args, _ = mock_email_service.call_args
    assert "alice@example.com" in email_args[0]      # recipient
    assert "Alice Smith" in email_args[1]            # full name
    assert "face" in email_args[2]                   # biometric type
    assert email_args[3] is True                     # success flag


@pytest.mark.asyncio
async def test_email_not_sent_if_no_email(client, monkeypatch, mock_email_service):
    # Override Supabase to return a user with no email
    class NoEmailSupabase:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def single(self): return self
        def insert(self, *a, **kw): return self
        def execute(self):
            return type("Resp", (), {"data": {
                "National_ID": "67890",
                "Name": "Bob",
                "SurName": "Brown",
                "Email": None
            }})()

    monkeypatch.setattr("services.verification_service.supabase", NoEmailSupabase())

    # Simulate a face verification attempt
    files = {"face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg")}
    data = {"national_id": "67890"}
    response = client.post("/verify", files=files, data=data)

    assert response.status_code == 200
    resp_json = response.json()
    assert "verified" in resp_json

    # Ensure email was NOT called
    mock_email_service.assert_not_called()

# -----------------------------
# Email Notifications

@pytest.mark.asyncio
async def test_integration_email_sent_on_authentication_failure(client, monkeypatch):
    # Test customer
    test_customer = {
        "National_ID": "9876543210123",
        "Name": "Alice",
        "SurName": "Smith",
        "Email": "alice.smith@example.com"
    }

    background_tasks = BackgroundTasks()

    # --- Mock supabase to return the customer ---
    class FakeSupabase:
        def table(self, name):
            return self
        def select(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def single(self):
            return self
        def insert(self, *args, **kwargs):
            return self
        def execute(self):
            # Returning customer data
            return type("Resp", (), {"data": test_customer})()

    monkeypatch.setattr("services.verification_service.supabase", FakeSupabase())

    # --- Mock face verification to fail ---
    async def fake_verify_face_fail(customer_id, face_image):
        return {"is_authenticated": False, "details": {}}
    monkeypatch.setattr("services.verification_service.verify_face", fake_verify_face_fail)

    # --- Mock iris verification to not be used (optional) ---
    async def fake_verify_iris(customer_id, iris_image, eye_type):
        return {"is_authenticated": False, "details": {}}
    monkeypatch.setattr("services.verification_service.verify_iris", fake_verify_iris)

    # --- Mock email sending ---
    mock_email = AsyncMock()
    monkeypatch.setattr(
        "services.verification_service.send_authentication_report_email",
        mock_email
    )

    files = {"face_image": ("face.jpg", create_fake_image_bytes(), "image/jpeg")}
    data = {"national_id": test_customer["National_ID"]}

    response = client.post("/verify", files=files, data=data)

    # --- Execute background tasks to actually send email ---
    for task, args, kwargs in background_tasks.tasks:
        await task(*args, **kwargs)

    # --- Assertions ---
    resp_json = response.json()
    assert resp_json["verified"] is False
    mock_email.assert_called_once()

    # Check email was sent
    mock_email.assert_awaited_once()
    called_args = mock_email.call_args[0]
    assert called_args[0] == test_customer["Email"]        # Email recipient
    assert "Alice Smith" in called_args[1]                # Full name
    assert "face" in called_args[2]                       # Authentication method
    assert called_args[3] is False                        # Result: failure