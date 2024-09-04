from django.db import models

from crm.models import BaseModel

class Stock(BaseModel):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.symbol

class Frequency(BaseModel):
    duration = models.IntegerField()
    duration_type = models.CharField(max_length=255)


class Subscription(BaseModel):
    user = models.ForeignKey("account.User", on_delete=models.CASCADE, related_name="subscriptions")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    frequency = models.ManyToManyField("Frequency")
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.stock.symbol}"


class Alert(BaseModel):
    user = models.ForeignKey("account.User", on_delete=models.CASCADE)
    stock = models.ForeignKey("Stock", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.email}'s alert for {self.stock.symbol}"


class Trigger(BaseModel):
    alert = models.ForeignKey("Alert", on_delete=models.CASCADE)
    threshold_price = models.DecimalField(max_digits=10, decimal_places=2)
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)



class StockTracker(BaseModel):
    stock = models.ForeignKey("Stock", on_delete=models.CASCADE)
    price = models.DecimalField(default=0, max_digits=20, decimal_places=3)