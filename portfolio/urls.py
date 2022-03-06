from django.shortcuts import render
from django.urls import path

urlpatterns = [
    path('', lambda request: render(request, "portfolio/index.html"), name="portfolio_index")
]