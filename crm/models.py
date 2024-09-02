from django.db import models
from django.db.models import TextChoices
from django.utils import timezone


class ActivityType(TextChoices):
    delete = "delete"
    update = "update"
    create = "create"
    hard_delete = "hard_delete"



class AvailableManager(models.Manager):
    def get_queryset(self):
        return (
            super(AvailableManager, self)
            .get_queryset()
            .filter(deleted_at__isnull=True)
        )


class ObjectManager(models.Manager):
    def get_queryset(self):
        return super(ObjectManager, self).get_queryset()


class AppDbModel(models.Model):
    objects = ObjectManager()

    class Meta:
        abstract = True


class BaseModel(AppDbModel):
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    created_by = models.ForeignKey(
        "account.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        "account.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    deleted_by = models.ForeignKey(
        "account.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    available_objects = AvailableManager()

    class Meta:
        abstract = True


class ActivityLog(AppDbModel):
    user = models.ForeignKey(
        "account.User",
        on_delete=models.CASCADE,
        related_name="user_activities",
    )
    activity_type = models.CharField(max_length=255, null=True)
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} by {} - {}".format(self.activity_type, self.user, self.note)


