from .models import MallonExchangeOne, MallonExchangeTwo
from django.http import JsonResponse
import requests

def exchangeOne(request):
    if request.method == "POST":
        with open("test.txt", "w") as file:
            file.write(request.POST)
    elif request.method == "GET":
        data = []
        try: data = MallonExchangeOne.objects.get(id=1).market_data
        except: pass
        return JsonResponse(data)


def exchangeTwo(request):
    exchange_request = requests.get("https://exchange2.matraining.com/md")
    if exchange_request.status_code == 200:
        data = exchange_request
        MallonExchangeTwo.objects.update_or_create(id=1, defaults=dict(
            market_data = data.json()
        ))
        return JsonResponse(data.json)
    return JsonResponse([])

