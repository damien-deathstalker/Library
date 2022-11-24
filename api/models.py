from django.db import models

# Create your models here.
class MallonExchangeOne(models.Model):
    market_data = models.JSONField(verbose_name="Market Data")

class MallonExchangeTwo(models.Model):
    market_data = models.JSONField(verbose_name="Market Data")