from django.forms import ModelForm, SelectDateWidget, DateInput
from .models import QCReport

import re


class DatePickerWidget(DateInput):
    template_name = 'widgets/datepicker.html'


#
class QcReportForm(ModelForm):
    class Meta:
        model = QCReport
        fields = '__all__'
        widgets = {
            'timing_when1s': DatePickerWidget(),
            'timing_when1e': DatePickerWidget(),
        }

    def sections(self):
        return [
            ('Preface', list(self._iter_fields_by_key('reviewer', 'site', 'netcdf_files'))),
            ('Critical quality checks', self._make_section('timing_', 'pres_err_', 'nans_', 'qc_flags_', 'rolling_xluft_')),
            ('Informational quality checks', self._make_section('lse_', 'sg_', 'nonlin_')),
            ('Additional comments', self._make_section('additional_'))
        ]

    def _make_section(self, *prefixes):
        return [self._make_question(p) for p in prefixes]

    def _make_question(self, prefix):
        fields = {'mcs': [], 'whens': [], 'cmts': []}
        for key, field in self._iter_fields_with_prefixes(prefix):
            m = re.search(r'(.+_when[0-9]+)s$', key)
            if m:
                key2 = m.group(1) + 'e'
                fields['whens'].append((field, self[key2]))
            elif re.search(r'when[0-9]+e$', key):
                # We handle the end fields with their paired start fields
                pass
            elif key.endswith('cmts'):
                fields['cmts'].append(field)
            else:
                fields['mcs'].append(field)
        return fields

    def _iter_fields_with_prefixes(self, *prefixes):
        for key in self.fields.keys():
            for prefix in prefixes:
                if key.startswith(prefix):
                    # Calling self[key] returns a BoundField, which is what we need for rendering
                    yield key, self[key]

    def _iter_fields_by_key(self, *keys):
        for k in keys:
            yield self[k]
