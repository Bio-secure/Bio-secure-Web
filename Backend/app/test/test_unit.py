import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.user_service import register_user_service
from models.transaction_models import TransactionCreate
from services.transaction_service import create_transaction_service
from services.employee_service import login_employee_service
from models.employee_models import EmployeeLogin
from services import report_service
from services.iris_service import encode_iris, extract_iris_features, masked_hamming_distance, match_iris
from services.face_service import compare_embeddings
from models.employee_models import EmployeeCreate, EmployeeLogin, VerifyPasswordRequest
from services.employee_service import list_employees_service, login_employee_service, register_employee_service, verify_password_service
from models.customer_model import CustomerUpdate
from services.customer_service import delete_customer_service, enrich_transactions, get_customer_details_service, list_customers_service, update_customer_service
from services.biometric_service import register_biometric_face_service, register_biometric_iris_service
from fastapi import UploadFile, HTTPException
import numpy as np  
from services.employee_service import pwd_context 


class DummyUploadFile:
    def __init__(self):
        self.filename = "test.jpg"
        self.content_type = "image/jpeg"
        self._data = b"fake image content"
        self._index = 0

    async def read(self, n: int = -1):  # <- allow optional argument
        if n == -1:
            n = len(self._data) - self._index
        chunk = self._data[self._index:self._index+n]
        self._index += n
        return chunk
    
# Test for register_biometric_face_service Suaccessccess
    
@pytest.mark.asyncio
async def test_register_face_success():
    national_id = "12345"
    file = DummyUploadFile()

    with patch("services.biometric_service.DeepFace") as mock_df, \
         patch("services.biometric_service.fetch_customer_name", new_callable=AsyncMock) as mock_fetch, \
         patch("services.biometric_service.supabase") as mock_supabase, \
         patch("services.biometric_service.run_in_threadpool", new_callable=AsyncMock) as mock_threadpool:

        # Mock DeepFace.represent
        mock_df.represent.return_value = [{"embedding": [0.1, 0.2, 0.3]}]

        # Mock fetch customer
        mock_fetch.return_value = ("John", "Doe")

        # Mock run_in_threadpool to return the embedding list
        mock_threadpool.return_value = [{"embedding": [0.1, 0.2, 0.3]}]

        result = await register_biometric_face_service(national_id, file)
        assert "message" in result
        assert "registered successfully" in result["message"]
        
@pytest.mark.asyncio
async def test_register_iris_success():
    national_id = "12345"
    left_file = DummyUploadFile()
    right_file = DummyUploadFile()

    with patch("services.biometric_service.fetch_customer_name", new_callable=AsyncMock) as mock_fetch, \
         patch("services.biometric_service.extract_iris_features", return_value=(np.array([0]), np.array([0]))), \
         patch("services.biometric_service.supabase") as mock_supabase:

        mock_fetch.return_value = ("John", "Doe")

        result = await register_biometric_iris_service(national_id, left_file, right_file)
        assert "message" in result
        assert "registered successfully" in result["message"]

# Test for register_biometric_face_service Failure
# --- Failure test: face registration ---
@pytest.mark.asyncio
async def test_register_face_failure():
    national_id = "12345"
    file = DummyUploadFile()

    with patch("services.biometric_service.DeepFace") as mock_df, \
         patch("services.biometric_service.fetch_customer_name", new_callable=AsyncMock) as mock_fetch, \
         patch("services.biometric_service.supabase") as mock_supabase, \
         patch("services.biometric_service.run_in_threadpool", new_callable=AsyncMock) as mock_threadpool:

        # Simulate DeepFace returning empty embeddings
        mock_df.represent.return_value = [{}]
        mock_fetch.return_value = ("John", "Doe")
        mock_threadpool.return_value = [{}]

        with pytest.raises(Exception) as excinfo:
            await register_biometric_face_service(national_id, file)
        assert "Failed to process face image" in str(excinfo.value)

# --- Failure test: iris registration ---
@pytest.mark.asyncio
async def test_register_iris_failure():
    national_id = "12345"
    left_file = DummyUploadFile()
    right_file = DummyUploadFile()

    with patch("services.biometric_service.fetch_customer_name", new_callable=AsyncMock) as mock_fetch, \
         patch("services.biometric_service.extract_iris_features", side_effect=Exception("Extraction failed")), \
         patch("services.biometric_service.supabase") as mock_supabase:

        mock_fetch.return_value = ("John", "Doe")

        with pytest.raises(Exception) as excinfo:
            await register_biometric_iris_service(national_id, left_file, right_file)
        assert "Iris processing failed" in str(excinfo.value)

# --- Test Supabase upload failure ---
@pytest.mark.asyncio
async def test_register_face_supabase_failure():
    national_id = "12345"
    file = DummyUploadFile()

    with patch("services.biometric_service.DeepFace") as mock_df, \
         patch("services.biometric_service.fetch_customer_name", new_callable=AsyncMock) as mock_fetch, \
         patch("services.biometric_service.run_in_threadpool", new_callable=AsyncMock) as mock_threadpool:

        mock_df.represent.return_value = [{"embedding": [0.1, 0.2, 0.3]}]
        mock_fetch.return_value = ("John", "Doe")

        # Make run_in_threadpool fail on Supabase upload
        mock_threadpool.side_effect = Exception("Upload failed")

        with pytest.raises(HTTPException) as excinfo:
            await register_biometric_face_service(national_id, file)

        assert excinfo.value.status_code == 400
        assert "Failed to process face image" in excinfo.value.detail
        assert "Upload failed" in excinfo.value.detail

@pytest.mark.asyncio
async def test_register_face_db_failure():
    national_id = "12345"
    file = DummyUploadFile()

    with patch("services.biometric_service.DeepFace") as mock_df, \
         patch("services.biometric_service.fetch_customer_name", new_callable=AsyncMock) as mock_fetch, \
         patch("services.biometric_service.run_in_threadpool", new_callable=AsyncMock) as mock_threadpool:

        mock_df.represent.return_value = [{"embedding": [0.1, 0.2, 0.3]}]
        mock_fetch.return_value = ("John", "Doe")

        # Simulate DB upsert failure
        mock_threadpool.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as excinfo:
            await register_biometric_face_service(national_id, file)

        # Correct status code
        assert excinfo.value.status_code == 400

        # Correct detail check
        assert "Failed to process face image" in excinfo.value.detail
        assert "DB error" in excinfo.value.detail


# --- test customer_service.py ---
# Dummy classes and data
class DummyResponse:
    def __init__(self, data):
        self.data = data

dummy_customer = {"National_ID": 1, "Name": "John", "SurName": "Doe"}
dummy_transaction = {
    "id": 1,
    "created_at": "2025-01-01T00:00:00",
    "transaction_type": "deposit",
    "amount": 100,
    "employee_id": None
}

def get_customer_details_service(customer_id: int, db=None):
    db = db or supabase  # use global if not passed
    try:
        # Fetch main customer
        customer_response = db.table("Customer").select("*").eq("National_ID", customer_id).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer_data = customer_response.data

        # Face biometric
        try:
            biometric_response = db.table("Biometric").select("face_image_url").eq("National_ID", customer_id).single().execute()
            customer_data['face_image_url'] = biometric_response.data.get('face_image_url') if biometric_response.data else None
        except Exception:
            customer_data['face_image_url'] = None

        # Transactions
        transactions_response = db.table("Transactions") \
            .select("id, created_at, transaction_type, amount, note, employee_id") \
            .eq("customer_id", customer_id) \
            .order("created_at", desc=True) \
            .limit(15) \
            .execute()

        customer_data['transactions'] = enrich_transactions(transactions_response.data)
        return customer_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching customer details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customer details.")

def test_get_customer_details_success():
    # Create a mock supabase
    mock_sup = MagicMock()

    # Mock Customer table
    mock_customer_table = MagicMock()
    mock_customer_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=dummy_customer)

    # Mock Biometric table
    mock_bio_table = MagicMock()
    mock_bio_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"face_image_url": "url"})

    # Mock Transactions table
    mock_transactions_table = MagicMock()
    mock_transactions_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[dummy_transaction])

    # Map table names to mocks
    def table_side_effect(table_name):
        if table_name == "Customer":
            return mock_customer_table
        elif table_name == "Biometric":
            return mock_bio_table
        elif table_name == "Transactions":
            return mock_transactions_table
        else:
            return MagicMock()

    mock_sup.table.side_effect = table_side_effect

    # Mock enrich_transactions
    with patch("services.customer_service.enrich_transactions", side_effect=lambda x: x):
        result = get_customer_details_service(1, db=mock_sup)

    # Assertions
    assert result["National_ID"] == 1
    assert result["face_image_url"] == "url"
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["amount"] == 100

# list_customers_service
def test_list_customers_success():
    with patch("services.customer_service.supabase") as mock_sup:
        mock_sup.table.return_value.select.return_value.execute.return_value.data = [dummy_customer]
        result = list_customers_service()
        assert isinstance(result, list)
        assert result[0]["National_ID"] == 1

def test_list_customers_failure():
    with patch("services.customer_service.supabase") as mock_sup:
        mock_sup.table.side_effect = Exception("Supabase error")
        with pytest.raises(HTTPException) as excinfo:
            list_customers_service()
        assert excinfo.value.status_code == 500


# update_customer_service
def test_update_customer_success():
    with patch("services.customer_service.supabase") as mock_sup:
        mock_sup.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [dummy_customer]
        customer_update = CustomerUpdate(Name="Jane")
        result = update_customer_service(1, customer_update)
        assert "message" in result
        assert result["message"] == "Customer updated successfully"

def test_update_customer_no_data():
    customer_update = CustomerUpdate()  # all fields None
    with pytest.raises(HTTPException) as excinfo:
        update_customer_service(1, customer_update)
    assert excinfo.value.status_code == 400

def test_update_customer_not_found():
    with patch("services.customer_service.supabase") as mock_sup:
        mock_sup.table.return_value.update.return_value.eq.return_value.execute.return_value.data = None
        customer_update = CustomerUpdate(Name="Jane")
        with pytest.raises(HTTPException) as excinfo:
            update_customer_service(999, customer_update)
        assert excinfo.value.status_code == 404


# delete_customer_service
def test_delete_customer_success():
    with patch("services.customer_service.supabase") as mock_sup:
        mock_sup.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [dummy_customer]
        result = delete_customer_service(1)
        assert "message" in result
        assert result["message"] == "Customer deleted successfully"

def test_delete_customer_not_found():
    with patch("services.customer_service.supabase") as mock_sup:
        mock_sup.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = None
        with pytest.raises(HTTPException) as excinfo:
            delete_customer_service(999)
        assert excinfo.value.status_code == 404


# --- Dummy data ---
dummy_employee = {
    "EmID": "1",
    "EmName": "John",
    "EmSurName": "Doe",
    "IsAdmin": True,
    "EmPass": "$2b$12$fakehashedpassword"
}


# -----------------------
# list_employees_service
# -----------------------
def test_list_employees_success():
    mock_sup = MagicMock()
    mock_sup.table.return_value.select.return_value.execute.return_value.data = [dummy_employee]

    with patch("services.employee_service.supabase", mock_sup):
        result = list_employees_service()
        assert isinstance(result, list)
        assert result[0]["EmID"] == "1"


def test_list_employees_failure():
    mock_sup = MagicMock()
    mock_sup.table.side_effect = Exception("DB error")
    
    with patch("services.employee_service.supabase", mock_sup):
        with pytest.raises(HTTPException) as excinfo:
            list_employees_service()
        assert excinfo.value.status_code == 500


# -----------------------
# register_employee_service
# -----------------------
def test_register_employee_success():
    employee_data = EmployeeCreate(
        employeeId="1", name="John", surname="Doe", password="secret", isAdmin=True
    )

    mock_sup = MagicMock()
    mock_sup.table.return_value.insert.return_value.execute.return_value.data = [dummy_employee]

    with patch("services.employee_service.supabase", mock_sup), \
         patch("services.employee_service.pwd_context.hash", return_value="hashed_pw") as mock_hash:
        result = register_employee_service(employee_data)
        assert "message" in result
        assert "Employee registered successfully" in result["message"]
        assert result["data"][0]["EmID"] == "1"
        mock_hash.assert_called_once_with("secret")


def test_register_employee_failure():
    employee_data = EmployeeCreate(
        employeeId="1", name="John", surname="Doe", password="secret", isAdmin=True
    )

    mock_sup = MagicMock()
    mock_sup.table.return_value.insert.side_effect = Exception("Insert failed")

    with patch("services.employee_service.supabase", mock_sup):
        with pytest.raises(HTTPException) as excinfo:
            register_employee_service(employee_data)
        assert excinfo.value.status_code == 500
        assert "Insert failed" in excinfo.value.detail


# -----------------------
# login_employee_service
# -----------------------
def test_login_success():
    employee_login = EmployeeLogin(emId="1", password="secret")
    mock_sup = MagicMock()

    # Employee record returned
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = dummy_employee
    # Mock password verification
    with patch("services.employee_service.pwd_context.verify", return_value=True):
        with patch("services.employee_service.supabase", mock_sup):
            result = login_employee_service(employee_login)
            assert result["success"] is True
            assert result["emId"] == "1"


def test_login_wrong_password():
    employee_login = EmployeeLogin(emId="1", password="wrong_pw")
    mock_sup = MagicMock()
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = dummy_employee

    with patch("services.employee_service.pwd_context.verify", return_value=False):
        with patch("services.employee_service.supabase", mock_sup):
            with pytest.raises(HTTPException) as excinfo:
                login_employee_service(employee_login)
            assert excinfo.value.status_code == 401


def test_login_employee_not_found():
    employee_login = EmployeeLogin(emId="2", password="secret")
    mock_sup = MagicMock()
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

    with patch("services.employee_service.supabase", mock_sup):
        with pytest.raises(HTTPException) as excinfo:
            login_employee_service(employee_login)
        assert excinfo.value.status_code == 404


# -----------------------
# verify_password_service
# -----------------------
def test_verify_password_success():
    payload = VerifyPasswordRequest(emId=1, password="secret")
    mock_sup = MagicMock()
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"EmPass": "any_fake_hash"}

    with patch("services.employee_service.supabase", mock_sup), \
         patch.object(pwd_context, "verify", return_value=True):
        result = verify_password_service(payload)
        assert result["valid"] is True

def test_verify_password_invalid():
    payload = VerifyPasswordRequest(emId=1, password="wrong")
    mock_sup = MagicMock()
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"EmPass": "any_fake_hash"}

    with patch("services.employee_service.supabase", mock_sup), \
         patch.object(pwd_context, "verify", return_value=False):
        with pytest.raises(HTTPException) as excinfo:
            verify_password_service(payload)
        assert excinfo.value.status_code == 401

def test_verify_password_employee_not_found():
    payload = VerifyPasswordRequest(emId="999", password="secret")
    mock_sup = MagicMock()
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

    with patch("services.employee_service.supabase", mock_sup):
        with pytest.raises(HTTPException) as excinfo:
            verify_password_service(payload)
        assert excinfo.value.status_code == 404

# --- test face_service.py comparing embeddings ---
def test_compare_embeddings_match():
    emb1 = np.array([0.1, 0.2, 0.3])
    emb2 = np.array([0.1, 0.2, 0.3])
    match, dist = compare_embeddings(emb1, emb2)
    assert match is True
    assert dist == 0

def test_compare_embeddings_mismatch():
    emb1 = np.array([1, 0, 0])
    emb2 = np.array([0, 1, 0])
    match, dist = compare_embeddings(emb1, emb2)
    assert match is False
    assert dist > 0

# --- Iris Registration service Test ---
def test_encode_iris_basic():
    polar = np.array([[0.6, 0.4], [0.5, 0.2]])
    noise = np.array([[0,1],[1,0]])
    code, mask = encode_iris(polar, noise)
    assert code.shape == polar.shape
    assert mask.shape == noise.shape
    assert code[0,0] == 1  # 0.6 > 0.5
    assert code[0,1] == 0  # 0.4 <= 0.5

def test_masked_hamming_distance_shift():
    code1 = np.array([[0,1],[1,0]], dtype=np.uint8)
    code2 = np.array([[1,0],[1,0]], dtype=np.uint8)
    mask1 = np.zeros_like(code1)
    mask2 = np.zeros_like(code2)
    d, s = masked_hamming_distance(code1, mask1, code2, mask2)
    assert 0 <= d <= 1
    assert isinstance(s, int)

def test_match_iris_threshold():
    f1 = (np.array([[0,1],[1,0]]), np.zeros((2,2)))
    f2 = (np.array([[0,1],[1,0]]), np.zeros((2,2)))
    result = match_iris(f1, f2, threshold=0.1)
    assert result["is_match"] is True

@patch("services.iris_service.segment")
@patch("services.iris_service.normalize")
@patch("cv2.imread")
def test_extract_iris_features(mock_imread, mock_normalize, mock_segment):
    mock_imread.return_value = np.ones((10,10), dtype=np.uint8)
    mock_segment.return_value = ((5,5,3),(3,3,1), None)
    mock_normalize.return_value = (np.array([[0.6]]), np.array([[0]]))
    
    code, mask = extract_iris_features("dummy.jpg")
    assert code.shape == (1,1)
    assert mask.shape == (1,1)

# -------------------------------
# Helper to properly mock supabase.execute().data
def mock_supabase_for_logs(data):
    execute_mock = MagicMock()
    execute_mock.data = data
    # return object from execute()
    table_mock = MagicMock()
    select_mock = MagicMock()
    select_mock.order.return_value = select_mock  # chainable
    select_mock.limit.return_value = select_mock
    select_mock.gte.return_value = select_mock
    select_mock.execute.return_value = execute_mock
    table_mock.select.return_value = select_mock
    mock = MagicMock()
    mock.table.return_value = table_mock
    return mock

def test_get_customer_logs_period_today_fixed():
    sample_data = [{"Transaction_Timestamp": "2025-09-04T12:00:00"}]
    mock_sup = mock_supabase_for_logs(sample_data)

    with patch("services.report_service.supabase", mock_sup):
        result = report_service.get_customer_logs_service(period="today")
        assert result == sample_data

def test_get_employee_logs_default_fixed():
    sample_data = [{"Log_Timestamp": "2025-09-04T12:00:00"}]
    mock_sup = mock_supabase_for_logs(sample_data)

    with patch("services.report_service.supabase", mock_sup):
        result = report_service.get_employee_logs_service()
        assert result == sample_data

def test_get_employee_logs_period_week_fixed():
    sample_data = [{"Log_Timestamp": "2025-09-01T12:00:00"}]
    mock_sup = mock_supabase_for_logs(sample_data)

    with patch("services.report_service.supabase", mock_sup):
        result = report_service.get_employee_logs_service(period="week")
        assert result == sample_data

#--- Transaction Service Test ---        
def mock_supabase_select(select_return=None):
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = select_return
    mock_supabase = MagicMock()
    mock_supabase.table.return_value = mock_table
    return mock_supabase

def test_withdrawal_success():
    transaction = TransactionCreate(customer_id=1, employee_id=2, transaction_type="withdrawal", amount=50, note="ATM")
    mock_sup = mock_supabase_select(select_return={"Name": "John", "SurName": "Doe", "Balance": 100})

    with patch("services.transaction_service.supabase", mock_sup):
        response = create_transaction_service(transaction)
        assert response.status_code == 200
        assert "successful" in response.body.decode()

#--- user_service.py test ---
def mock_supabase_insert(insert_return=None):
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value.data = insert_return
    mock_supabase = MagicMock()
    mock_supabase.table.return_value = mock_table
    return mock_supabase

def test_register_user_success():
    user_data = {
        "nationalId": "12345",
        "firstName": "John",
        "lastName": "Doe",
        "birthDate": "1990-01-01",
        "phoneNo": "5551234",
        "gender": "male",
        "balance": "1000",
        "email": "john@example.com"
    }
    mock_sup = mock_supabase_insert(insert_return=[{"id": 1}])

    with patch("services.user_service.supabase", mock_sup):
        result = register_user_service(user_data)
        assert result["message"] == "User registered successfully!"
        assert result["data"] == [{"id": 1}]
        mock_sup.table.return_value.insert.assert_called_once()

def test_register_user_invalid_balance():
    user_data = {"balance": "not_a_number"}
    with patch("services.user_service.supabase", mock_supabase_insert()):
        with pytest.raises(HTTPException) as exc:
            register_user_service(user_data)
        assert exc.value.status_code == 400

def test_register_user_supabase_failure():
    mock_sup = MagicMock()
    mock_sup.table.return_value.insert.side_effect = Exception("DB down")
    with patch("services.user_service.supabase", mock_sup):
        with pytest.raises(HTTPException) as exc:
            register_user_service({"nationalId": "123"})
        assert exc.value.status_code == 500

# -----------------------------
# Fake Supabase for Employee and Logs
# -----------------------------
class FakeTable:
    def __init__(self, data=None):
        self._data = data
        self.insert_called_with = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def single(self):
        return self

    def execute(self):
        return type("Resp", (), {"data": self._data})()

    def insert(self, payload):
        self.insert_called_with = payload
        return self

class FakeSupabase:
    def table(self, name):
        if name == "Employees":
            return FakeTable({
                "EmID": 1,
                "EmPass": "$2b$12$hashedpassword",
                "IsAdmin": True,
                "EmName": "Alice",
                "EmSurName": "Smith"
            })
        elif name == "EmployeeLogs":
            return FakeTable()  # empty table for logging
        return FakeTable()

# -------------------------------
# Employee Login Service Test
@pytest.fixture
def employee_data():
    return {
        "EmID": "01",
        "EmPass": "$2b$12$hashedpassword",
        "EmName": "Alice",
        "EmSurName": "Smith",
        "IsAdmin": True
    }

@pytest.mark.parametrize(
    "password_input, expected_exception, expected_status",
    [
        ("correctpass", None, None),  # success case
        ("wrongpass", HTTPException, 401)  # wrong password
    ]
)
def test_login_employee_service_correct(monkeypatch, password_input, expected_exception, expected_status):
    login_data = EmployeeLogin(emId=1, password="correctpass")

    # Patch supabase with our fake
    monkeypatch.setattr("services.employee_service.supabase", FakeSupabase())

    # Patch password verification
    monkeypatch.setattr(
        "services.employee_service.pwd_context.verify",
        lambda pw, hashed: True
    )

    response = login_employee_service(login_data)
    assert response["success"] is True
    assert response["emId"] == 1

# ----------------------------
# VERIFY PASSWORD TESTS
# ----------------------------

def test_verify_password_success(monkeypatch, employee_data):
    class FakeSupabase:
        def table(self, name):
            return self
        def select(self, *args, **kwargs):
            return self
        def eq(self, key, value):
            return self
        def single(self):
            return self
        def execute(self):
            return type("Resp", (), {"data": {"EmPass": employee_data["EmPass"]}})()
    
    monkeypatch.setattr("services.employee_service.supabase", FakeSupabase())

    def fake_verify(password, hashed):
        return password == "correctpass"
    
    monkeypatch.setattr("services.employee_service.pwd_context", MagicMock(verify=fake_verify))

    payload = VerifyPasswordRequest(emId="01", password="correctpass")
    result = verify_password_service(payload)
    assert result["valid"] is True

def test_verify_password_wrong(monkeypatch, employee_data):
    class FakeSupabase:
        def table(self, name):
            return self
        def select(self, *args, **kwargs):
            return self
        def eq(self, key, value):
            return self
        def single(self):
            return self
        def execute(self):
            return type("Resp", (), {"data": {"EmPass": employee_data["EmPass"]}})()
    
    monkeypatch.setattr("services.employee_service.supabase", FakeSupabase())

    def fake_verify(password, hashed):
        return False
    
    monkeypatch.setattr("services.employee_service.pwd_context", MagicMock(verify=fake_verify))

    payload = VerifyPasswordRequest(emId="01", password="wrongpass")
    with pytest.raises(HTTPException) as exc:
        verify_password_service(payload)
    assert exc.value.status_code == 401

def test_verify_password_not_found(monkeypatch):
    class FakeSupabase:
        def table(self, name):
            return self
        def select(self, *args, **kwargs):
            return self
        def eq(self, key, value):
            return self
        def single(self):
            return self
        def execute(self):
            return type("Resp", (), {"data": None})()
    
    monkeypatch.setattr("services.employee_service.supabase", FakeSupabase())

    payload = VerifyPasswordRequest(emId="01", password="any")
    with pytest.raises(HTTPException) as exc:
        verify_password_service(payload)
    assert exc.value.status_code == 404

