from django.db.models import Q, QuerySet
from django.utils import timezone


from services.util import CustomAPIRequestUtil
from stock.models import Stock


class StockService(CustomAPIRequestUtil):
    serializer_class = StockSerializer

    def create_stock(self, payload):
        symbol = payload.get("symbol")
        name = payload.get("name")
        exchange = payload.get("exchange")

        stock, is_created = Stock.available_objects.get_or_create(
            symbol__iexact=symbol,
            name=name,
            exchange=exchange,
            created_at=timezone.now()
        )

        stock.created_by = self.auth_user
        stock.save()

        self.report_activity(ActivityType.create, stock)

        return stock, None

    def update_stock(self, payload, stock_id=None):
        if stock_id:
            stock, error = self.fetch_stock_by_id(stock_id)
            if error:
                return None, error
        else:
            return None, self.make_error("Stock ID is required")

        stock.name = payload.get("name") or stock.name
        stock.exchange = payload.get("exchange") or stock.exchange
        stock.updated_by = self.auth_user
        stock.updated_at = timezone.now()
        stock.save()

        self.clear_temp_cache(stock)
        self.report_activity(ActivityType.update, stock)

        return stock, None

    def delete_stock(self, stock_id):
        stock, error = self.fetch_stock_by_id(stock_id)
        if error:
            return None, error

        stock.deleted_at = timezone.now()
        stock.deleted_by = self.auth_user
        stock.save()

        self.clear_temp_cache(stock)
        self.report_activity(ActivityType.delete, stock)

        return stock, None

    def hard_delete_stock(self, stock):
        stock.delete()

        self.clear_temp_cache(stock)
        self.report_activity(ActivityType.delete, stock)

        return stock, None

    def find_stock_by_symbol(self, symbol):
        def __fetch():
            stock = self.__get_base_query().filter(symbol__iexact=symbol).first()
            if not stock:
                return None, self.make_404(f"Stock with symbol '{symbol}' not found")
            return stock, None

        cache_key = self.generate_cache_key("stock_symbol", symbol.lower())
        return self.get_cache_value_or_default(cache_key, __fetch)

    def fetch_stock_by_id(self, stock_id=None):
        def __fetch():
            stock = self.__get_base_query().filter(pk=stock_id).first()
            if not stock:
                return None, self.make_404("Stock not found")
            return stock, None

        cache_key = self.generate_cache_key("stock_id", stock_id)
        return self.get_cache_value_or_default(cache_key, __fetch)

    def fetch_stock_list(self, filter_params) -> QuerySet:
        self.page_size = filter_params.get("page_size", 100)
        filter_keyword = filter_params.get("keyword")

        q = Q()
        if filter_keyword:
            q &= (Q(name__icontains=filter_keyword) | Q(symbol__icontains=filter_keyword))

        return self.__get_base_query().filter(q).order_by("-created_at")

    def create_subscription(self, payload):
        user = self.auth_user
        stock_symbol = payload.get("stock_symbol")

        stock, error = self.find_stock_by_symbol(stock_symbol)
        if error:
            return None, error

        existing_subscription = StockSubscription.objects.filter(user=user, stock=stock).first()
        if existing_subscription:
            return None, self.make_error("Subscription already exists")

        frequency = payload.get("frequency")

        subscription = StockSubscription.objects.create(
            user=user,
            stock=stock,
            frequency=frequency,
            created_at=timezone.now()
        )

        subscription.created_by = user
        subscription.save()

        self.report_activity(ActivityType.create, subscription)

        return subscription, None

    def delete_subscription(self, subscription_id):
        subscription, error = self.fetch_subscription_by_id(subscription_id)
        if error:
            return None, error

        subscription.deleted_at = timezone.now()
        subscription.deleted_by = self.auth_user
        subscription.save()

        self.clear_temp_cache(subscription)
        self.report_activity(ActivityType.delete, subscription)

        return subscription, None

    def create_alert(self, payload):
        user = self.auth_user
        stock_symbol = payload.get("stock_symbol")

        stock, error = self.find_stock_by_symbol(stock_symbol)
        if error:
            return None, error

        price_threshold = payload.get("price_threshold")

        alert = StockAlert.objects.create(
            user=user,
            stock=stock,
            price_threshold=price_threshold,
            created_at=timezone.now()
        )

        alert.created_by = user
        alert.save()

        self.report_activity(ActivityType.create, alert)

        return alert, None

    def delete_alert(self, alert_id):
        alert, error = self.fetch_alert_by_id(alert_id)
        if error:
            return None, error

        alert.deleted_at = timezone.now()
        alert.deleted_by = self.auth_user
        alert.save()

        self.clear_temp_cache(alert)
        self.report_activity(ActivityType.delete, alert)

        return alert, None

    def fetch_subscription_by_id(self, subscription_id=None):
        def __fetch():
            subscription = StockSubscription.objects.filter(pk=subscription_id).first()
            if not subscription:
                return None, self.make_404("Subscription not found")
            return subscription, None

        cache_key = self.generate_cache_key("subscription_id", subscription_id)
        return self.get_cache_value_or_default(cache_key, __fetch)

    def fetch_alert_by_id(self, alert_id=None):
        def __fetch():
            alert = StockAlert.objects.filter(pk=alert_id).first()
            if not alert:
                return None, self.make_404("Alert not found")
            return alert, None

        cache_key = self.generate_cache_key("alert_id", alert_id)
        return self.get_cache_value_or_default(cache_key, __fetch)

    @classmethod
    def __get_base_query(cls):
        return Stock.objects.all()

    def clear_temp_cache(self, stock):
        self.clear_cache(self.generate_cache_key("stock_id", stock.id))
        self.clear_cache(self.generate_cache_key("stock_symbol", stock.symbol.lower()))

