from rest_framework.routers import DefaultRouter
from .views import NoteViewSet, sync, ask
from django.urls import path, include

router = DefaultRouter()
router.register(r'notes', NoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('sync', sync, name='sync-sheet'),  # POST /api/notes/sync
    path('ask', ask, name='ask-question'),  # POST /api/notes/ask
]
