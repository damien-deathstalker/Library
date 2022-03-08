from typing import Text
from django.http import Http404, HttpResponse
from django.shortcuts import render
import os
from django.conf import settings

# Create your views here.
def download(request, cv_type):
    path: Text = ".pdf"
    if cv_type == "extended_cv": 
        path = f"Kofi Bekoe Ofei - CV{path}"
    elif cv_type == "resume": 
        path = f"Kofi Bekoe Ofei - Resume{path}"
    file_path = os.path.join(settings.MEDIA_ROOT, 'docs', path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404