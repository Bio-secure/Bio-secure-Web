from typing import Optional
from fastapi import FastAPI, Form, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware

from configs.settings import supabase


from models.customer_model import CustomerUpdate
from models.employee_models import EmployeeCreate, EmployeeLogin, VerifyPasswordRequest
from models.transaction_models import TransactionCreate
from services.biometric_service import register_biometric_service
from services.customer_service import delete_customer_service, get_customer_details_service, list_customers_service, update_customer_service
from services.employee_service import list_employees_service, login_employee_service, register_employee_service, verify_password_service
from services.report_service import get_customer_logs_service, get_employee_logs_service, get_registration_records_service, get_registration_stats_service
from services.transaction_service import create_transaction_service
from services.user_service import register_user_service
from services.verification_service import verify_customer_identity_service

app = FastAPI()

origins = [
    "http://localhost:5173", 
    "http://127.0.0.1:5173", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def root():
    return {"message": "FastAPI is running!"}

@app.post("/register-biometric")
def register_biometric(
    national_id: str = Form(...),
    face_image: UploadFile = File(...),
    iris_image: UploadFile = File(None)
):
    return register_biometric_service(national_id, face_image, iris_image)
    
@app.post("/verify")
async def verify_customer_identity(
    background_tasks: BackgroundTasks,
    face_image: UploadFile = File(None),
    iris_image: UploadFile = File(None),
    customer_id: int = Form(...)
):
    return await verify_customer_identity_service(customer_id, background_tasks, face_image, iris_image)

@app.get("/customer-details/{customer_id}")
def get_customer_details(customer_id: int):
    return get_customer_details_service(customer_id)

@app.get("/customers")
def list_customers():
    return list_customers_service()

@app.get("/employees")
def list_employees():
    return list_employees_service()

@app.post("/register-employee")
def register_employee(employee_data: EmployeeCreate):
    return register_employee_service(employee_data)

@app.post("/login-employee")
def login_employee(employee_login_data: EmployeeLogin):
    return login_employee_service(employee_login_data)

@app.post("/register-user")
def register_user(user_data: dict):
    return register_user_service(user_data)

@app.post("/transaction")
def create_transaction(transaction: TransactionCreate):
    return create_transaction_service(transaction)

@app.get("/registration-records")
def get_registration_records():
    return get_registration_records_service()

@app.get("/registration-stats")
def get_registration_stats():
    return get_registration_stats_service()

@app.get("/customer-logs")
def get_customer_logs(show_all: Optional[bool] = Query(False), period: Optional[str] = Query(None)):
    return get_customer_logs_service(show_all, period)

@app.get("/employee-logs")
def get_employee_logs(period: Optional[str] = Query(None)):
    return get_employee_logs_service(period)

    
@app.get("/debug")
def debug():
    response = supabase.table("Customer").select("*").limit(2).execute()
    print("DEBUG DATA:", response.data)
    return response.data

@app.post("/verify-password")
def verify_password(payload: VerifyPasswordRequest):
    return verify_password_service(payload)

## Supabase CRUD Utility Endpoints

@app.put("/customers/{customer_id}")
async def update_customer(customer_id: int, customer: CustomerUpdate):
    return await update_customer_service(customer_id, customer)

@app.delete("/customers/{customer_id}")
async def delete_customer(customer_id: int):
    return await delete_customer_service(customer_id) 