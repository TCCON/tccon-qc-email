import json

from django.conf import settings
from django import forms
from django.forms import ModelForm, Form, FileField, TextInput
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

        return cleaned_data


class SiteInfoUpdateStaffForm(SiteInfoUpdateForm):
    class Meta:
        model = SiteInfoUpdate
        fields = ['long_name',
                  'data_doi',
                  'data_revision',
                  'release_lag',
                  'location',
                  'contact',
                  'site_reference',
                  'data_reference']
        widgets = {
            'data_doi': TextInput()
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('data_doi', '').startswith('10.'):
            self.add_error('data_doi', 'DOI must start with "10." (do not include leading "doi.org" or the like)')
        cleaned_data['data_doi'] = cleaned_data.get('data_doi', '').strip()  # just in case, make sure no surrounding whitespace
        return cleaned_data


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


class TypeRestrictedFileField(FileField):
    # Based on https://blog.bixly.com/accept-only-specific-file-types-in-django-file-upload
    def __init__(self, *args, **kwargs):
        self._content_types = set(kwargs.pop('content_types', {}))
        self._max_upload_bytes = kwargs.pop('max_upload_bytes', None)
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super().clean(*args, **kwargs)
        file = data.file
        try:
            content_type = data.content_type
            file_size = file.seek(0, 2)  # seek to the end and get the byte position
            file.seek(0)  # then go back to the beginning
            if content_type not in self._content_types:
                raise forms.ValidationError('Unsupported file type "{}". Supported types are: {}'.format(
                    content_type, ', '.join(self._content_types)
                ))
            elif self._max_upload_bytes is not None and file_size > self._max_upload_bytes:
                raise forms.ValidationError('File exceeds allowed size of {} bytes (file size = {} bytes)'.format(
                    self._max_upload_bytes, file_size
                ))
        except AttributeError:
            pass

        return data


class ReleaseFlagUpdateForm(Form):
    start = forms.DateField(label='Start date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    end = forms.DateField(label='End date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    name = forms.ChoiceField(label='Flag reason', choices=_get_flag_name_choices)
    comment = forms.CharField(label='Comment', max_length=256)
    plot = TypeRestrictedFileField(label='Upload an image of a plot',
                                   required=False,
                                   max_upload_bytes=5*1024**2,  # 5 MB
                                   content_types=('image/jpg', 'image/png'))

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
