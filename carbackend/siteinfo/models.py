from django.db import models
from django.contrib.auth.models import User

from copy import copy


# Create your models here.
class SiteInfoUpdate(models.Model):
    # Information kept for historical purposes
    user_updated = models.ForeignKey(User, on_delete=models.RESTRICT)
    datetime_updated = models.DateTimeField(auto_now=True)

    # Standard fields that we expect for every site
    site_id = models.CharField(max_length=2)
    long_name = models.CharField(max_length=32)
    release_lag = models.PositiveIntegerField()
    location = models.CharField(max_length=256)
    contact = models.CharField(max_length=256)
    site_reference = models.TextField()
    data_doi = models.TextField()
    data_reference = models.TextField()
    data_revision = models.CharField(max_length=8)

    # Allow for arbitrary extra fields
    extra_fields = models.JSONField(default=dict)

    @property
    def standard_fields(self):
        return ('long_name', 'release_lag', 'location', 'contact', 'site_reference',
                'data_doi', 'data_reference', 'data_revision')

    def to_dict(self):
        std_fields = {k: getattr(self, k) for k in self.standard_fields}
        the_dict = copy(self.extra_fields)
        the_dict.update(std_fields)
        return the_dict

