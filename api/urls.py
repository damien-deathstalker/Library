from django.urls import path
from .views import exchangeOne, exchangeTwo

urlpatterns = [
    path("market-data/1", exchangeOne),
    path("market-data/2", exchangeTwo),
]
