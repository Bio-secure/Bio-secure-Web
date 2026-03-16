import datetime
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from configs.settings import supabase
from models.transaction_models import TransactionCreate


def create_transaction_service(transaction: TransactionCreate):
    is_successful = True
    failure_reason = ""
    http_status_code = 200

    customer_response = supabase.table("Customer") \
        .select("Name", "SurName", "Balance") \
        .eq("National_ID", transaction.customer_id) \
        .single().execute()

    if not customer_response.data:
        is_successful = False
        failure_reason = "Customer Not Found"
        http_status_code = 404
    else:
        current_balance = customer_response.data.get("Balance") or 0
        if transaction.transaction_type == "withdrawal" and current_balance < transaction.amount:
            is_successful = False
            failure_reason = "Insufficient Funds"
            http_status_code = 400

    if is_successful:
        customer_data = customer_response.data
        customer_name = customer_data.get("Name", "N/A")
        customer_surname = customer_data.get("SurName", "N/A")
        current_balance = customer_data.get("Balance") or 0

        new_balance = (
            current_balance - transaction.amount
            if transaction.transaction_type == "withdrawal"
            else current_balance + transaction.amount
        )

        supabase.table("Customer").update({"Balance": new_balance}).eq("National_ID", transaction.customer_id).execute()

        transaction_record = {
            "customer_id": transaction.customer_id,
            "employee_id": transaction.employee_id,
            "transaction_type": transaction.transaction_type,
            "amount": transaction.amount,
            "note": transaction.note,
            "balance_after": new_balance,
        }
        supabase.table("Transactions").insert(transaction_record).execute()

        supabase.table("CustomerLogs").insert([
            {
                "Customer_National_ID": transaction.customer_id,
                "Name": customer_name,
                "SurName": customer_surname,
                "Result": True,
                "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        ]).execute()

        return JSONResponse(status_code=200, content={"message": f"{transaction.transaction_type.capitalize()} successful!", "new_balance": new_balance})

    else:
        log_payload = {
            "Customer_National_ID": transaction.customer_id,
            "Result": False,
            "Transaction_Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if failure_reason == "Customer Not Found":
            log_payload["Name"] = "Unknown"
            log_payload["SurName"] = "Customer"
        elif failure_reason == "Insufficient Funds":
            log_payload["Name"] = customer_response.data.get("Name", "N/A")
            log_payload["SurName"] = customer_response.data.get("SurName", "N/A")

        supabase.table("CustomerLogs").insert([log_payload]).execute()
        return JSONResponse(status_code=http_status_code, content={"message": failure_reason})
