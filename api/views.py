from .models import MallonExchangeOne, MallonExchangeTwo
from django.http import JsonResponse
import requests

def exchangeOne(request):
    exchange_request = requests.get("https://exchange.matraining.com/md")
    if exchange_request.status_code == 200:
        data = exchange_request
        MallonExchangeOne.objects.update_or_create(id=1, defaults=dict(
            market_data = data.json()
        ))
        return JsonResponse(data.json)
    return JsonResponse([])

def exchangeTwo(request):
    exchange_request = requests.get("https://exchange2.matraining.com/md")
    if exchange_request.status_code == 200:
        data = exchange_request
        MallonExchangeTwo.objects.update_or_create(id=1, defaults=dict(
            market_data = data.json()
        ))
        return JsonResponse(data.json)
    return JsonResponse([])

