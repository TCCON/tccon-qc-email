from django.conf import settings
from django.forms import ModelForm
from .models import SiteInfoUpdate
from . import utils

import re


class SiteInfoUpdateForm(ModelForm):
    class Meta:
        model = SiteInfoUpdate
        fields = ['release_lag',
                  'location',
                  'contact',
                  'site_reference',
                  'data_reference']

    @classmethod
    def fixed_fields(cls):
        return tuple(f for f in SiteInfoUpdate.standard_fields() if f not in cls.Meta.fields)

    # def save(self, user, site_info, commit=True):
    #     data = self.cleaned_data
    #     data['user_updated'] = user
    #     for field in self.fixed_fields():
    #         data[field] = site_info[field]
    #     super().save(commit=commit)

    def clean(self):
        cleaned_data = super().clean()
        contact_re = re.compile(r'.+<.+@.+>(\s*;.+<.+@.+>)*\s*$')
        if not contact_re.match(cleaned_data.get('contact', '')):
            self.add_error('contact', 'Must have format "Name <email>" (no quotes) or "Name1 <email1>; Name2 <email2>"')
        if cleaned_data['release_lag'] > utils.get_max_release_lag():
            self.add_error('release_lag', 'Release lag cannot be greater than {} days'.format(settings.MAX_RELEASE_LAG))
