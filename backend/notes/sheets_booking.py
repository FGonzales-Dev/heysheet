import os, uuid, datetime as dt
from typing import Optional
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SERVICES_TAB = "Services"
APPTS_TAB = "Appointments"

def _svc(readonly: bool):
    scope = "https://www.googleapis.com/auth/spreadsheets.readonly" if readonly \
            else "https://www.googleapis.com/auth/spreadsheets"
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=[scope]
    )
    return build("sheets", "v4", credentials=creds)

def list_services():
    s = _svc(True)
    vals = s.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{SERVICES_TAB}!A1:Z"
    ).execute().get("values", [])
    if not vals: return []
    headers, rows = vals[0], vals[1:]
    df = pd.DataFrame(rows, columns=headers[:len(rows[0])])
    return df.fillna("").astype(str).to_dict(orient="records")

def create_appointment(name, email, phone, service_name, total_sessions, sessions_text=""):
    s = _svc(False)
    booking_id = uuid.uuid4().hex[:8].upper()
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    row = [name, email, phone, service_name, str(total_sessions), sessions_text, booking_id, ts]
    s.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{APPTS_TAB}!A1:Z",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values":[row]}
    ).execute()
    return booking_id

def _find_row(booking_id:str) -> Optional[int]:
    s = _svc(True)
    vals = s.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{APPTS_TAB}!A1:Z"
    ).execute().get("values", [])
    if not vals: return None
    headers, rows = vals[0], vals[1:]
    if "Booking ID" not in headers: return None
    col = headers.index("Booking ID")
    for i, r in enumerate(rows, start=2):
        if len(r) > col and r[col] == booking_id:
            return i
    return None

def update_appointment(booking_id, **patch):
    rownum = _find_row(booking_id)
    if not rownum: return False
    s = _svc(True)
    headers = s.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{APPTS_TAB}!A1:Z1"
    ).execute().get("values", [[]])[0]
    def col(ix): return chr(ord('A') + ix)
    mapf = {
        "name":"Name","email":"Email","phone":"Phone","service":"Service",
        "total_sessions":"Total Sessions",
        "sessions_text":'Sessions (Format: Session 1: Date at Time | Session 2: Date at Time | etc.)'
    }
    data=[]
    for k,v in patch.items():
        h = mapf.get(k)
        if v is None or not h or h not in headers: continue
        data.append({"range": f"{APPTS_TAB}!{col(headers.index(h))}{rownum}", "values":[[str(v)]]})
    if not data: return True
    sw = _svc(False)
    sw.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={"valueInputOption":"RAW","data":data}
    ).execute()
    return True
