from django.db import models
from django.core.cache import cache
from configuration.basic_config import *
from rest_framework import serializers

"""
Activate configuration code below only when not running server
"""


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        pass

    def set_cache(self):
        cache.set(self.__class__.__name__, self)

    def save(self, *args, **kwargs):
        super(SingletonModel, self).save(*args, **kwargs)
        self.set_cache()

    @classmethod
    def load(cls):
        if cache.get(cls.__class__.__name__) is None:
            obj, created = cls.objects.get_or_create(pk=1)
            if not created:
                obj.set_cache()
            print(obj.__str__())
            return cache.get(cls.__class__.__name__)


class Interest(SingletonModel):
    interest_idx = models.AutoField(primary_key=True)
    interest_name = models.CharField(default="development", max_length=50)


class Pool(SingletonModel):
    pool_id = models.CharField(primary_key=True, max_length=50)
    pool_name = models.CharField(default=None, max_length=50)
    communication_mode = models.CharField(default="agora", max_length=7)
    current_population = models.IntegerField(default=0)
    max_population = models.IntegerField(default=6)
    interest = models.ManyToManyField(Interest)


class Member(SingletonModel):
    member_idx = models.AutoField(primary_key=True)
    nickname = models.CharField(max_length=30)
    level = models.CharField(default="bronze", max_length=7)
    pool_id = models.ForeignKey(Pool, on_delete=models.CASCADE)
