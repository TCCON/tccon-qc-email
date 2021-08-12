import json

from django.conf import settings
from django import forms
from django.forms import ModelForm, Form
from .models import SiteInfoUpdate, InfoFileLocks
from . import utils

from datetime import datetime
import os
import re
_this_year = datetime.today().year


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


def _get_flag_name_choices():
    with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
        definitions = tuple(json.load(f)['definitions'].keys())
    defs_long_form = {
        'ils': 'Problem with ILS',
        'tracking': 'Problem with solar tracker',
        'surface pressure': 'Error in surface pressure',
        'other': 'Other'
    }
    return [(k, defs_long_form[k]) for k in definitions]


def _get_flag_values():
    with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
        return json.load(f)['definitions']


class ReleaseFlagUpdateForm(Form):
    start = forms.DateField(label='Start date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    end = forms.DateField(label='End date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    name = forms.ChoiceField(label='Flag reason', choices=_get_flag_name_choices)
    comment = forms.CharField(label='Comment', max_length=256)
    plot = forms.FileField(label='Upload an image of a plot', required=False)

    def clean(self):
        cleaned_data = super().clean()
        print(cleaned_data)
        name = cleaned_data.get('name', None)
        flag_values = _get_flag_values()
        if name not in flag_values:
            # should never be the case, since the name has to be selected from a set of choices
            self.add_error('name', 'Error reason "{}" is not one of the allowed values'.format(name))

        if 'start' in cleaned_data and 'end' in cleaned_data and cleaned_data.get('start') > cleaned_data['end']:
            self.add_error('start', 'Start date cannot be after end date')
            self.add_error('end', 'End date cannot be before start date')

    def save_to_json(self, site_id, flag_id):
        curr_json = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_FILE)
        flag_defs = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_DEF_FILE)['definitions']

        # Update the JSON structure, add fields for the value and plot
        self.cleaned_data['value'] = flag_defs[self.cleaned_data['name']]
        if 'plot' in self.cleaned_data and self.cleaned_data['plot'] is not None:
            plot_data = self.cleaned_data['plot']
            _, ext = os.path.splitext(plot_data.name)
            plot_file = settings.FLAG_PLOT_DIRECTORY / '{}_{}_plot{}'.format(site_id, flag_id, ext)
            if not settings.FLAG_PLOT_DIRECTORY.exists():
                settings.FLAG_PLOT_DIRECTORY.mkdir()
            with open(plot_file, 'wb') as dest:
                for chunk in plot_data:
                    dest.write(chunk)
            self.cleaned_data['plot'] = str(plot_file.name)

        start = self.cleaned_data.pop('start')
        end = self.cleaned_data.pop('end')
        key = '{}_{}_{}_{}'.format(site_id, int(flag_id), start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))
        curr_json[key] = self.cleaned_data
        self.update_flag_file(curr_json)

    @staticmethod
    def update_flag_file(flag_dict):
        utils.backup_file_rolling(settings.RELEASE_FLAGS_FILE)
        InfoFileLocks.write_json_file(settings.RELEASE_FLAGS_FILE, flag_dict, indent=4)
