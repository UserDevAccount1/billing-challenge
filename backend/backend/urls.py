import os
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings

def index_view(request):
    frontend_path = os.path.join(settings.BASE_DIR, "frontend", "index.html")
    if not os.path.exists(frontend_path):
        return HttpResponse("Frontend index.html not found.", status=404)
    with open(frontend_path, "r", encoding="utf-8") as f:
        return HttpResponse(f.read(), content_type="text/html")

urlpatterns = [
    path('', index_view, name='index'),
    path('api/', include('api.urls')),
]
