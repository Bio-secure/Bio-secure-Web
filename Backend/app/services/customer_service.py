import datetime
from fastapi import HTTPException
from models.customer_model import CustomerUpdate
from configs.settings import supabase

def get_customer_details_service(customer_id: int):
    try:
        # Fetch main customer
        customer_response = supabase.table("Customer").select("*").eq("National_ID", customer_id).single().execute()
        if not customer_response.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer_data = customer_response.data

        # Face biometric
        try:
            biometric_response = supabase.table("Biometric").select("face_image_url").eq("National_ID", customer_id).single().execute()
            customer_data['face_image_url'] = biometric_response.data.get('face_image_url') if biometric_response.data else None
        except Exception:
            customer_data['face_image_url'] = None

        # Transactions
        transactions_response = supabase.table("Transactions") \
            .select("id, created_at, transaction_type, amount, note, employee_id") \
            .eq("customer_id", customer_id) \
            .order("created_at", desc=True) \
            .limit(15) \
            .execute()

        customer_data['transactions'] = enrich_transactions(transactions_response.data)
        return customer_data
    except Exception as e:
        print(f"Error fetching customer details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customer details.")


def enrich_transactions(transactions: list):
    if not transactions:
        return []

    enriched = []
    for tx in transactions:
        employee_name = "System"
        if tx.get("employee_id"):
            try:
                employee_response = supabase.table("Employees").select("EmName, EmSurName").eq("EmID", tx["employee_id"]).single().execute()
                if employee_response.data:
                    emp = employee_response.data
                    employee_name = f"{emp['EmName']} {emp['EmSurName']}"
            except Exception:
                employee_name = "Unknown Employee"
        tx["employee_name"] = employee_name
        enriched.append(tx)
    return enriched


def list_customers_service_page(page: int = 1, page_size: int = 10):
    try:
        offset = (page - 1) * page_size
        response = (
            supabase.table("Customer")
            .select("National_ID, Name, SurName, phone_no, Email")
            .range(offset, offset + page_size - 1)  # Supabase uses index ranges
            .execute()
        )

        total_count = (
            supabase.table("Customer")
            .select("National_ID", count="exact")  # get total for pagination
            .execute()
        ).count

        return {
            "data": response.data or [],
            "total": total_count,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        print(f"❌ Error fetching customers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customers.")
    
def list_customers_service():
    try:
        response = supabase.table("Customer").select("National_ID, Name, SurName, phone_no, Email").execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching customers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch customers.")

def update_customer_service(customer_id: int, customer: CustomerUpdate):
    # Build update payload (only non-null fields)
    update_data = {k: v for k, v in customer.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    # Update customer in Supabase
    response = supabase.table("Customer").update(update_data).eq("National_ID", customer_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"message": "Customer updated successfully", "data": response.data}

def delete_customer_service(customer_id: int):
    response = supabase.table("Customer").delete().eq("National_ID", customer_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {"message": "Customer deleted successfully"}