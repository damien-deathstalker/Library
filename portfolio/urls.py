from django.shortcuts import render
from django.urls import path
from .views import download

urlpatterns = [
    path('', lambda request: render(request, "portfolio/index.html"), name="portfolio_index"),
    path('download/<slug:cv_type>/', download, name="portfolio_download")
]