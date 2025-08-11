from rest_framework import viewsets
from .models import Note
from .serializers import NoteSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .sheets_rag import sync_sheet, QAEngine
class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer

@api_view(["POST"])
def sync(request):
    n = sync_sheet()
    return Response({ "synced_rows": n })

_engine = None
def _get_engine():
    global _engine
    if _engine is None:
        _engine = QAEngine()
    return _engine

@api_view(["POST"])
def ask(request):
    q = (request.data.get("question") or "").strip()
    if not q:
        return Response({"error":"Missing 'question'."}, status=400)
    engine = _get_engine()
    answer, matches = engine.ask(q)
    return Response({"answer": answer, "matches": matches})