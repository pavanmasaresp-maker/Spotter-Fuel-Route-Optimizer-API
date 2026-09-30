from django.db import models

class GeocodeCache(models.Model):
    query = models.CharField(max_length=500, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    display_name = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now=True)

class RouteCache(models.Model):
    cache_key = models.CharField(max_length=64, unique=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now=True)
