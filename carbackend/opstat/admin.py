from django.contrib import admin
from . import models

# Register your models here.
# May remove these in production?
admin.site.register(models.SiteStatus)
admin.site.register(models.SiteStatusHistory)
