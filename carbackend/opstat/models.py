from django.db import models


# Create your models here.
class SiteStatus(models.Model):
    siteid = models.CharField(max_length=2, primary_key=True)
    sitename = models.CharField(max_length=30)
    username = models.CharField(max_length=30, null=True)
    date = models.DateTimeField(null=True)
    status = models.CharField(max_length=1, choices=(('y', 'Yes'), ('n', 'No')))
    description = models.CharField(max_length=150, null=True)


class SiteStatusHistory(models.Model):
    site = models.ForeignKey(SiteStatus, on_delete=models.PROTECT)
    username = models.CharField(max_length=30, null=True)
    date = models.DateTimeField(null=True)
    status = models.CharField(max_length=1, choices=(('y', 'Yes'), ('n', 'No')))
    description = models.CharField(max_length=150, null=True)
