from .models import MallonExchangeOne, MallonExchangeTwo
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests

@csrf_exempt
def exchangeOne(request):
    data = [{}]
    if request.method == "POST":
        with open("/home/dadeathstalker/Library/test.txt", "w") as file:
            file.write(str(request.text))
            file.write("\n")
            file.write(str(request.body))
            file.write("\n")
            file.write(str(request))
    elif request.method == "GET":
        try: data = MallonExchangeOne.objects.get(id=1).market_data
        except: pass
    return JsonResponse(data, safe=False)


def exchangeTwo(request):
    exchange_request = requests.get("https://exchange2.matraining.com/md")
    if exchange_request.status_code == 200:
        data = exchange_request
        MallonExchangeTwo.objects.update_or_create(id=1, defaults=dict(
            market_data = data.json()
        ))
        return JsonResponse(data.json)
    return JsonResponse([])

