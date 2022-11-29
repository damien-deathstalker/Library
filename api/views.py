from .models import MallonExchangeOne, MallonExchangeTwo
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests, json


class Price:
    def __init__(self, bid, ask) -> None:
        self.buy = bid
        self.sell = ask
    
    def __str__(self) -> str:
        return f"{self.buy} - {self.sell}"
    
    def __repr__(self) -> str:
        return str(self)

class MarketData:
    def __init__(self, trade_data:dict) -> None:
        self.SELL_LIMIT = trade_data.get("SELL_LIMIT")
        self.ASK_PRICE = trade_data.get("ASK_PRICE")
        self.BUY_LIMIT = trade_data.get("BUY_LIMIT")
        self.MAX_PRICE_SHIFT = trade_data.get("MAX_PRICE_SHIFT")
        self.LAST_TRADED_PRICE = trade_data.get("LAST_TRADED_PRICE")
        self.TICKER = trade_data.get("TICKER")
        self.BID_PRICE = trade_data.get("BID_PRICE")
        self.PRICE = Price(trade_data.get("BID_PRICE"), trade_data.get("ASK_PRICE"))
    
    def __str__(self) -> str:
        return f"{self.TICKER} ({self.BID_PRICE}/{self.ASK_PRICE})"

    def __repr__(self) -> str:
        return str(self)
    
    @property
    def as_dict(self) -> dict:
        data = {}
        data[self.TICKER] = str(self.PRICE)
        return data

        

@csrf_exempt
def exchangeOne(request):
    data = {}
    if request.method == "POST":
        data = json.loads(request.body)
        MallonExchangeOne.objects.update_or_create(id=1, defaults=dict(
            market_data = data
        ))
    elif request.method == "GET":
        try: 
            exchange = MallonExchangeOne.objects.get(id=1)
            market_data = exchange.market_data
            for md in market_data:
                md_obj = MarketData(md)
                data.update(md_obj.as_dict)
                # data.append(md_obj.as_dict)
        except Exception as e: print(e)
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

