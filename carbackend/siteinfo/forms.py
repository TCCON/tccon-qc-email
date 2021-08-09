from django.forms import ModelForm, IntegerField
from .models import SiteInfoUpdate


class SiteInfoUpdateForm(ModelForm):
    class Meta:
        model = SiteInfoUpdate
        fields = ['release_lag',
                  'location',
                  'contact',
                  'site_reference',
                  'data_reference']
        # widgets = {
        #     'release_lag': IntegerField(min_value=0)
        # }
