import datetime
from fastapi import HTTPException, Query
from configs.settings import supabase


def get_registration_records_service():
    try:
        response = supabase.table("Customer").select("National_ID, Name, SurName, DOR, Balance").order("DOR", desc=True).execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


def get_registration_stats_service():
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - datetime.timedelta(days=today_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        today_count = supabase.table("Customer").select("*", count="exact").gte("DOR", today_start.isoformat()).execute().count
        week_count = supabase.table("Customer").select("*", count="exact").gte("DOR", week_start.isoformat()).execute().count
        month_count = supabase.table("Customer").select("*", count="exact").gte("DOR", month_start.isoformat()).execute().count

        return {"today": today_count, "week": week_count, "month": month_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch registration stats: {e}")


def get_customer_logs_service(show_all: bool = False, period: str = None):
    try:
        query = supabase.table("CustomerLogs").select("*").order("Transaction_Timestamp", desc=True)

        if period:
            now = datetime.datetime.now(datetime.timezone.utc)
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=now.weekday())
            elif period == "month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.gte("Transaction_Timestamp", start_date.isoformat())
        elif not show_all:
            query = query.limit(15)

        response = query.execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch customer logs: {str(e)}")


def get_employee_logs_service(period: str = None):
    try:
        query = supabase.table("EmployeeLogs").select("*").order("Log_Timestamp", desc=True)

        if period:
            now = datetime.datetime.now(datetime.timezone.utc)
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=now.weekday())
            elif period == "month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.gte("Log_Timestamp", start_date.isoformat())
        else:
            query = query.limit(10)

        response = query.execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch employee logs: {str(e)}")
