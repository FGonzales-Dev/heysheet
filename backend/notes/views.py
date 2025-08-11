from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Note
from .serializers import NoteSerializer
from .sheets_rag import sync_sheet, QAEngine
from .sheets_booking import list_services, create_appointment, update_appointment

from groq import Groq
import os, json, re

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer


@api_view(["POST"])
def sync(request):
    n = sync_sheet()
    return Response({"synced_rows": n})


# -------- single endpoint plumbing --------
_engine = None
def _get_engine():
    global _engine
    if _engine is None:
        try:
            _engine = QAEngine()
        except RuntimeError:
            # build index on first use
            sync_sheet()
            _engine = QAEngine()
    return _engine


_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# STRONGER rules to avoid false positives (no LLM fallback by default)
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


def _extract_create(text: str, services_data):
    """extract name/email/phone/service/total_sessions/sessions_text from free text."""
    try:
        out = _groq.chat.completions.create(
            model="llama3-8b-8192",
            temperature=0,
            messages=[
                {"role": "system", "content": "Extract booking fields and return STRICT JSON only."},
                {
                    "role": "user",
                    "content": (
                        f"Services (truncated): {json.dumps(services_data[:8])}\n"
                        f"User: {text}\n"
                        'Return: {"name":"","email":"","phone":"","service":"","total_sessions":0,"sessions_text":""}'
                    ),
                },
            ],
        ).choices[0].message.content
        d = json.loads(out)
        d["total_sessions"] = int(d.get("total_sessions") or 0)
        return d
    except Exception:
        return {}


def _extract_update(text: str):
    """extract booking_id and patch fields from free text."""
    try:
        out = _groq.chat.completions.create(
            model="llama3-8b-8192",
            temperature=0,
            messages=[
                {"role": "system", "content": "Extract update for an appointment. Return STRICT JSON only."},
                {
                    "role": "user",
                    "content": (
                        f"User: {text}\n"
                        'Return: {"booking_id":"","name":null,"email":null,"phone":null,"service":null,"total_sessions":null,"sessions_text":null}'
                    ),
                },
            ],
        ).choices[0].message.content
        d = json.loads(out)
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


@api_view(["POST"])
def ask(request):
    q = (request.data.get("question") or "").strip()
    if not q:
        return Response({
            "answer": "Tell me what you’d like to do: “show services”, “book the 5 sessions class…”, “update booking ABCD1234…”, or ask business hours.",
            "intent": "unknown"
        })

    intent = _intent(q)
    print("\n=== /api/ask ===", {"q": q, "intent": intent})  # watch with: docker compose logs -f backend

    # 1) services list (return readable summary + raw array)
    if intent == "services.list":
        svcs = list_services()
        lines = []
        for s in svcs:
            name = s.get("Class Name") or s.get("Service") or s.get("Name") or "Service"
            dur  = s.get("Duration")
            price = s.get("Price")
            loc = s.get("Location")
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
                "missing": missing
            })

        bid = create_appointment(
            d["name"], d["email"], str(d["phone"]),
            d["service"], int(d["total_sessions"]),
            d.get("sessions_text", "")
        )
        return Response({
            "answer": f"Booking created. Your Booking ID is {bid}.",
            "intent": "appointments.create",
            "booking_id": bid
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

    # 4) fallback — business-hours RAG
    engine = _get_engine()
    answer, matches = engine.ask(q)
    return Response({
        "answer": answer,
        "intent": "qa",
        "matches": matches
    })
