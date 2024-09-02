from django.db import models

from account.models import User
from crm.models import BaseModel

class Stock(BaseModel):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    exchange = models.CharField(max_length=50)

    def __str__(self):
        return self.symbol



class Subscription(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    frequency = models.IntegerField()  # Frequency in seconds
    active = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.user.email} - {self.stock.symbol}"


class Alert(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    threshold_price = models.DecimalField(max_digits=10, decimal_places=2)
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.stock.symbol} @ {self.price_threshold}"


class Comparison(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock_symbol_1 = models.CharField(max_length=10)
    stock_symbol_2 = models.CharField(max_length=10)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()


