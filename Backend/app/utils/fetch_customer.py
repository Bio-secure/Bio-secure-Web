from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from configs.settings import supabase


async def fetch_customer_name(national_id: str):
    try:
        response = await run_in_threadpool(
            lambda: supabase.table("Customer")
                           .select("Name, SurName")
                           .eq("National_ID", int(national_id))
                           .single()
                           .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Customer {national_id} not found.")
        return response.data.get("Name", ""), response.data.get("SurName", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching customer: {e}")