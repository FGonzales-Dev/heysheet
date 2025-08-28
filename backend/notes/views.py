from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.views.decorators.csrf import csrf_exempt
from threading import Thread
import logging

from .models import Note
from .serializers import NoteSerializer
from .sheets_rag import sync_sheet, QAEngine
from .sheets_booking import list_services, create_appointment, update_appointment

from groq import Groq
import os, json, re


# -------------------------
# Notes CRUD (unchanged)
# -------------------------
class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer


# -------------------------
# Health check (fast)
# -------------------------
@api_view(["GET", "POST"])
def ping(request):
    return Response({"ok": True})


# ---------------------------------------------------
# /api/sync: REAL SYNC without 504s (return fast)
# ---------------------------------------------------
def _run_sync_job():
    """Background job that performs the actual Google Sheets sync."""
    try:
        n = sync_sheet()
        logging.info("Sheets sync finished. synced_rows=%s", n)
    except Exception as e:
        logging.exception("Sheets sync failed: %s", e)


@csrf_exempt
@api_view(["POST"])
def sync(request):
    """
    Start the Google Sheets sync in a background thread and return 202 immediately.
    This prevents timeouts (504) and the misleading CORS message.
    """
    try:
        # Quick env checks so we fail fast with JSON (not a 504)
        google_creds = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not google_creds:
            return Response({"error": "GOOGLE_SHEETS_CREDENTIALS not set"}, status=500)

        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if not spreadsheet_id:
            return Response({"error": "SPREADSHEET_ID not set"}, status=500)

        # Sanity-check creds JSON (common misconfig)
        try:
            json.loads(google_creds)
        except json.JSONDecodeError as e:
            return Response(
                {"error": f"Invalid GOOGLE_SHEETS_CREDENTIALS JSON: {str(e)}"},
                status=500
            )

        # Fire-and-forget so HTTP response returns immediately (no 504)
        Thread(target=_run_sync_job, daemon=True).start()
        return Response({"started": True}, status=202)

    except Exception as e:
        import traceback
        print("Sync error:", str(e))
        print("Traceback:", traceback.format_exc())
        return Response({"error": str(e)}, status=500)


# ---------------------------------------------------
# QA engine: build lazily but NEVER block a request
# ---------------------------------------------------
_engine = None
_engine_building = False  # avoids spawning multiple builders


def _build_engine_async():
    """Build the index then instantiate QAEngine without blocking requests."""
    global _engine, _engine_building
    try:
        # build/update the index (heavy)
        sync_sheet()
        _engine = QAEngine()
        logging.info("QAEngine built and ready.")
    except Exception as e:
        logging.exception("QAEngine build failed: %s", e)
    finally:
        _engine_building = False


def _get_engine_nonblocking():
    """
    Return QAEngine if ready. If not, start a background build (once) and signal
    the caller to retry soon.
    """
    global _engine, _engine_building
    if _engine is not None:
        return _engine
    if not _engine_building:
        _engine_building = True
        Thread(target=_build_engine_async, daemon=True).start()
    raise RuntimeError("engine_initializing")


_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# STRONG rules (no LLM fallback) to avoid misclassifying simple Q&A
def _intent(text: str) -> str:
    t = text.lower().strip()

    # services list
    if any(k in t for k in [
        "services", "service list", "what are your services",
        "classes", "class list", "what classes"
    ]):
        return "services.list"

    # create booking
    if any(k in t for k in ["book", "reserve", "sign up", "schedule", "enroll"]):
        if not any(k in t for k in ["update", "change", "resched", "cancel"]):
            return "appointments.create"

    # update booking (must mention updating AND booking/appointment/id)
    if any(k in t for k in ["update", "change", "resched", "cancel"]) and \
       any(k in t for k in ["booking", "appointment", "booking id", "code", "id"]):
        return "appointments.update"

    return "qa"


# ---------- helpers for field extraction ----------
def _best_service_match(text: str, services):
    """Pick a service by token overlap with the catalog (simple & fast)."""
    text_l = text.lower()
    names = []
    for s in services:
        n = s.get("Class Name") or s.get("Service") or s.get("Name")
        if n:
            names.append(n)

    if not names:
        return None

    # exact-ish substring first
    for n in names:
        if n.lower() in text_l:
            return n

    # token overlap score
    def toks(s): return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) >= 3}
    tset = toks(text)
    best, best_score = None, 0.0
    for n in names:
        nset = toks(n)
        if not nset:
            continue
        score = len(tset & nset) / len(nset)
        if score > best_score:
            best, best_score = n, score

    return best if best_score >= 0.3 else None


def _extract_create(text: str, services_data):
    """
    Parse name/email/phone/service/total_sessions/sessions_text.
    Rule-based first; if some are missing, ask LLM to fill ONLY gaps.
    """
    out = {
        "name": "",
        "email": "",
        "phone": "",
        "service": "",
        "total_sessions": 0,
        "sessions_text": ""
    }

    # email
    m = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    if m:
        out["email"] = m.group(0)

    # phone (longest 7–15 digits)
    nums = re.findall(r"\b(?:\+?\d[\s-]?){7,15}\b", text)
    if nums:
        out["phone"] = max(("".join(filter(str.isdigit, n)) for n in nums), key=len)

    # total sessions: "5 sessions" or "total of 5"
    m = re.search(r"\b(\d+)\s*sessions?\b", text, re.I)
    if not m:
        m = re.search(r"\btotal(?:\s+of)?\s+(\d+)\b", text, re.I)
    if m:
        out["total_sessions"] = int(m.group(1))

    # name after "for ..."
    m = re.search(r"\bfor\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b", text)
    if m:
        out["name"] = m.group(1).strip()

    # sessions_text: "first session ..." or combine "session ..." snippets
    m = re.search(r"(first\s+session[^,.]+(?:[,;].*)?)", text, re.I)
    if m:
        out["sessions_text"] = m.group(1).strip()
    else:
        sess_parts = re.findall(r"(session\s*\d*[^,.]+)", text, re.I)
        if sess_parts:
            out["sessions_text"] = " | ".join(p.strip() for p in sess_parts)

    # service from catalog
    svc = _best_service_match(text, services_data)
    if svc:
        out["service"] = svc

    # Fill ONLY missing fields via a tiny LLM call
    missing = [k for k in ["name","email","phone","service","total_sessions","sessions_text"] if not out.get(k)]
    if missing:
        try:
            raw = _groq.chat.completions.create(
                model="llama3-8b-8192",
                temperature=0,
                messages=[
                    {"role": "system", "content": "Extract fields from text. Return strict JSON only."},
                    {"role": "user", "content":
                        f"Catalog (truncated): {json.dumps(services_data[:8])}\n"
                        f"User: {text}\n"
                        f"Fill ONLY these missing fields {missing}. "
                        'Return JSON with keys: name,email,phone,service,total_sessions,sessions_text; '
                        'do not invent values — leave empty string or 0 if unknown.'}
                ],
            ).choices[0].message.content
            d = json.loads(raw)
            for k in missing:
                if k == "total_sessions":
                    try:
                        out[k] = int(d.get(k) or 0)
                    except Exception:
                        pass
                else:
                    if d.get(k):
                        out[k] = str(d.get(k)).strip()
        except Exception:
            pass

    return out


def _extract_update(text: str):
    """extract booking_id and patch fields from free text."""
    try:
        raw = _groq.chat.completions.create(
            model="llama3-8b-8192",
            temperature=0,
            messages=[
                {"role": "system", "content": "Extract update for an appointment. Return STRICT JSON only."},
                {"role": "user", "content":
                    f"User: {text}\n"
                    'Return: {"booking_id":"","name":null,"email":null,"phone":null,"service":null,"total_sessions":null,"sessions_text":null}'}
            ],
        ).choices[0].message.content
        d = json.loads(raw)
        bid = (d.get("booking_id") or "").strip()
        patch = {
            k: d.get(k)
            for k in ["name", "email", "phone", "service", "total_sessions", "sessions_text"]
            if d.get(k) not in (None, "")
        }
        return bid, patch
    except Exception:
        m = re.search(r"\b([A-Z0-9]{6,12})\b", text)
        return (m.group(1) if m else None), {}


@csrf_exempt
@api_view(["POST"])
def ask(request):
    """
    Handle Q&A and booking intents.
    IMPORTANT: Never build heavy indexes inside this request; if the QAEngine
    is not ready, return 202 and build in the background.
    """
    q = (request.data.get("question") or "").strip()
    if not q:
        return Response({
            "answer": "Tell me what you’d like to do: “show services”, “book the 5 sessions class…”, “update booking ABCD1234…”, or ask business hours.",
            "intent": "unknown"
        })

    intent = _intent(q)
    logging.info("=== /api/ask === %s", {"q": q, "intent": intent})

    # 1) services list
    if intent == "services.list":
        svcs = list_services()
        lines = []
        for s in svcs:
            name  = s.get("Class Name") or s.get("Service") or s.get("Name") or "Service"
            dur   = s.get("Duration")
            price = s.get("Price")
            loc   = s.get("Location")
            bits = [name]
            if dur:   bits.append(f"{dur} min")
            if price: bits.append(f"${price}")
            if loc:   bits.append(f"@ {loc}")
            lines.append("• " + " — ".join(bits))
        summary = "Available services:\n" + ("\n".join(lines) if lines else "(none found)")
        return Response({
            "answer": summary,
            "intent": "services.list",
            "services": svcs
        })

    # 2) create appointment
    if intent == "appointments.create":
        svcs = list_services()
        d = _extract_create(q, svcs)

        missing = [k for k in ["name", "email", "phone", "service", "total_sessions"] if not d.get(k)]
        if missing:
            return Response({
                "answer": (
                    "I can book that, but I still need: "
                    + ", ".join(missing)
                    + ". Example:\n"
                    "“Book Ceramic Regular Class - 5 Sessions for Alex "
                    "(alex@example.com, 12345678), 5 sessions, first session 2025-08-15 19:00.”"
                ),
                "intent": "appointments.create",
                "missing": missing,
                "parsed": d
            })

        bid = create_appointment(
            d["name"], d["email"], str(d["phone"]),
            d["service"], int(d["total_sessions"]),
            d.get("sessions_text", "")
        )
        return Response({
            "answer": f"Booking created. Your Booking ID is {bid}.",
            "intent": "appointments.create",
            "booking_id": bid,
            "parsed": d
        })

    # 3) update appointment
    if intent == "appointments.update":
        bid, patch = _extract_update(q)
        if not bid:
            return Response({
                "answer": "Please include your Booking ID (e.g., ABCD1234).",
                "intent": "appointments.update",
                "missing": ["booking_id"]
            })

        ok = update_appointment(bid, **patch)
        if not ok:
            return Response({
                "answer": "I couldn't find that Booking ID. Double-check and try again.",
                "intent": "appointments.update",
                "not_found": True
            })

        return Response({
            "answer": f"Updated booking {bid}.",
            "intent": "appointments.update",
            "booking_id": bid,
            "patched": patch
        })

    # 4) fallback — business-hours RAG (non-blocking build)
    try:
        engine = _get_engine_nonblocking()
    except RuntimeError as e:
        if "engine_initializing" in str(e):
            return Response(
                {"answer": "Initializing knowledge index… try again in a moment.", "intent": "qa_initializing"},
                status=202
            )
        raise

    answer, matches = engine.ask(q)
    return Response({
        "answer": answer,
        "intent": "qa",
        "matches": matches
    })
