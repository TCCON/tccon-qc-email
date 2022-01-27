from django.db import models
from django.utils.safestring import mark_safe
from tcconauth import utils

import re


_choices_yn = [
    ('y', 'Yes'),
    ('n', 'No'),
]

_choices_ynu = [
    ('y', 'Yes'),
    ('n', 'No'),
    ('u', 'Uncertain')
]

_choices_ynms = [
    ('y', 'Yes'),
    ('n', 'No'),
    ('m', 'Maybe'),
    ('s', 'Site discretion')
]

_choices_lse = [
    ('s', 'Small enough'),
    ('0', 'Uniformly 0'),
    ('l', 'Larger than usual')
]


class ISection:
    def sections(self):
        sect_list = [
            {
                'name': 'Preface',
                'questions': self._make_section('reviewer', 'site', 'netcdf_files'),
                'intro': ''
            },
            {
                'name': 'Critical quality checks',
                'questions': self._make_section('timing_', 'pres_err_', 'nans_', 'qc_flags_', 'rolling_xluft_'),
                'intro': """Data with any of the issues here generally requires reprocessing or release flagging (i.e.
spectra to be flagged on tccondata.org and withheld from the public files). If an issue here
does not require reprocessing or flagging, please describe why in the comments."""
            },
            {
                'name': 'Informational quality checks',
                'questions': self._make_section('lse_', 'sg_', 'nonlin_'),
                'intro': """The checks in this section are generally ones that cannot be fixed except in special cases
and so do not require reprocessing. If the error is sufficiently large, the data may be flagged out."""
            },
            {
                'name': 'Additional comments',
                'questions': self._make_section('additional_'),
                'intro': 'Use this section for any additional comments to the site PI. Please reference plot numbers.'
            }
        ]

        for sect in sect_list:
            sect['intro'] = mark_safe(sect.get('intro', ''))

        return sect_list

    def sections_no_preface(self):
        sections = self.sections()
        return sections[1:]

    def preface(self):
        return self.sections()[0:1]

    def _make_section(self, *prefixes):
        return [self._make_question(p) for p in prefixes]

    def _make_question(self, prefix,):
        fields = {
            'mcs': [],
            'whens': [],
            'cmts': [],
            'message': mark_safe(self._get_question_message(prefix)),
            'title': self._get_question_title(prefix)
        }

        for key, field in self._iter_fields_with_prefixes(prefix):
            m = re.search(r'(.+_when[0-9]+)s$', key)
            if m:
                key2 = m.group(1) + 'e'
                fields['whens'].append((field, self._get_field_by_key(key2)))
            elif re.search(r'when[0-9]+e$', key):
                # We handle the end fields with their paired start fields
                pass
            elif key.endswith('cmts'):
                fields['cmts'].append(field)
            else:
                fields['mcs'].append(field)
        return fields

    @classmethod
    def _get_question_message(cls, prefix):
        return getattr(cls, f'{prefix}message', '')

    @classmethod
    def _get_question_title(cls, prefix):
        return getattr(cls, f'{prefix}title', prefix)

    def _get_field_by_key(self, key):
        raise NotImplementedError('_get_field_by_key must be implemented in a child class')

    def _iter_fields_with_prefixes(self, *prefixes):
        raise NotImplementedError('_iter_fields_with_prefixes must be implemented in a child class')


# Create your models here.
class QCReport(models.Model, ISection):
    # Debated about making reviewer a foreign key to the user database.
    # I decided against it because I don't want to deal with issues if
    # we remove a user.
    reviewer = models.CharField(max_length=128, verbose_name='Reviewer')
    site = models.CharField(max_length=2, choices=utils.get_sites_as_choices())
    netcdf_files = models.TextField()

    timing_title = 'Timing error'
    timing_message = 'Check at least the Xluft PM - AM plot (|∆| < 0.01 ideal) and Xluft vs. SZA plots.'
    timing_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Is timing error present')
    timing_reproc = models.CharField(max_length=1, choices=_choices_ynms, verbose_name='Requires reprocessing')
    timing_when0s = models.DateField(blank=True, null=True, verbose_name='Start of first timing error')
    timing_when0e = models.DateField(blank=True, null=True, verbose_name='End of first timing error')
    timing_when1s = models.DateField(blank=True, null=True, verbose_name='Start of second timing error')
    timing_when1e = models.DateField(blank=True, null=True, verbose_name='End of second timing error')
    timing_when2s = models.DateField(blank=True, null=True, verbose_name='Start of third timing error')
    timing_when2e = models.DateField(blank=True, null=True, verbose_name='End of third timing error')
    timing_when3s = models.DateField(blank=True, null=True, verbose_name='Start of fourth timing error')
    timing_when3e = models.DateField(blank=True, null=True, verbose_name='End of fourth timing error')
    timing_when4s = models.DateField(blank=True, null=True, verbose_name='Start of fifth timing error')
    timing_when4e = models.DateField(blank=True, null=True, verbose_name='End of fifth timing error')
    timing_when5s = models.DateField(blank=True, null=True, verbose_name='Start of sixth timing error')
    timing_when5e = models.DateField(blank=True, null=True, verbose_name='End of sixth timing error')
    timing_when6s = models.DateField(blank=True, null=True, verbose_name='Start of seventh timing error')
    timing_when6e = models.DateField(blank=True, null=True, verbose_name='End of seventh timing error')
    timing_when7s = models.DateField(blank=True, null=True, verbose_name='Start of eighth timing error')
    timing_when7e = models.DateField(blank=True, null=True, verbose_name='End of eighth timing error')
    timing_when8s = models.DateField(blank=True, null=True, verbose_name='Start of ninth timing error')
    timing_when8e = models.DateField(blank=True, null=True, verbose_name='End of ninth timing error')
    timing_when9s = models.DateField(blank=True, null=True, verbose_name='Start of tenth timing error')
    timing_when9e = models.DateField(blank=True, null=True, verbose_name='End of tenth timing error')
    timing_cmts = models.TextField(blank=True)

    pres_err_title = 'Pressure sensor error'
    pres_err_message = 'Check the zmin - zobs plot (< 1 hPa ideal, < 3 hPa acceptable) if available. If not, check pout for drift.'
    pres_err_present = models.CharField(max_length=1, choices=_choices_ynu)
    pres_err_reproc = models.CharField(max_length=1, choices=_choices_ynms)
    pres_err_when0s = models.DateField(blank=True, null=True)
    pres_err_when0e = models.DateField(blank=True, null=True)
    pres_err_when1s = models.DateField(blank=True, null=True)
    pres_err_when1e = models.DateField(blank=True, null=True)
    pres_err_when2s = models.DateField(blank=True, null=True)
    pres_err_when2e = models.DateField(blank=True, null=True)
    pres_err_when3s = models.DateField(blank=True, null=True)
    pres_err_when3e = models.DateField(blank=True, null=True)
    pres_err_when4s = models.DateField(blank=True, null=True)
    pres_err_when4e = models.DateField(blank=True, null=True)
    pres_err_when5s = models.DateField(blank=True, null=True)
    pres_err_when5e = models.DateField(blank=True, null=True)
    pres_err_when6s = models.DateField(blank=True, null=True)
    pres_err_when6e = models.DateField(blank=True, null=True)
    pres_err_when7s = models.DateField(blank=True, null=True)
    pres_err_when7e = models.DateField(blank=True, null=True)
    pres_err_when8s = models.DateField(blank=True, null=True)
    pres_err_when8e = models.DateField(blank=True, null=True)
    pres_err_when9s = models.DateField(blank=True, null=True)
    pres_err_when9e = models.DateField(blank=True, null=True)
    pres_err_cmts = models.TextField(blank=True)

    nans_title = 'Window NaNs (Non-Voigt compiler check)'
    nans_message = 'Check the bar graph of NaNs per window; if some windows are all NaNs and others not, this indicates a compiler problem. Common offenders are the CH4 5938 wCO2 windows.'
    nans_present = models.CharField(max_length=1, choices=_choices_yn)
    nans_reproc = models.CharField(max_length=1, choices=_choices_ynms)
    nans_cmts = models.TextField(blank=True)

    qc_flags_title = 'Automatic QC flags'
    qc_flags_message = 'Check the bar graph of flags removing spectra for unusual flags removing significant numbers of spectra. xhf_error can remove more than it should at wet sites in particular.'
    qc_flags_present = models.CharField(max_length=1, choices=_choices_ynu)
    qc_flags_reproc = models.CharField(max_length=1, choices=_choices_ynms)
    qc_flags_cmts = models.TextField(blank=True)

    rolling_xluft_title = 'Rolling Xluft check'
    rolling_xluft_message = 'Check the 500 spectra rolling Xluft median for time periods significantly outside the ±0.004 limits'
    rolling_xluft_present = models.CharField(max_length=1, choices=_choices_ynu)
    rolling_xluft_flag = models.CharField(max_length=1, choices=_choices_ynu)
    rolling_xluft_when0s = models.DateField(blank=True, null=True)
    rolling_xluft_when0e = models.DateField(blank=True, null=True)
    rolling_xluft_when1s = models.DateField(blank=True, null=True)
    rolling_xluft_when1e = models.DateField(blank=True, null=True)
    rolling_xluft_when2s = models.DateField(blank=True, null=True)
    rolling_xluft_when2e = models.DateField(blank=True, null=True)
    rolling_xluft_when3s = models.DateField(blank=True, null=True)
    rolling_xluft_when3e = models.DateField(blank=True, null=True)
    rolling_xluft_when4s = models.DateField(blank=True, null=True)
    rolling_xluft_when4e = models.DateField(blank=True, null=True)
    rolling_xluft_when5s = models.DateField(blank=True, null=True)
    rolling_xluft_when5e = models.DateField(blank=True, null=True)
    rolling_xluft_when6s = models.DateField(blank=True, null=True)
    rolling_xluft_when6e = models.DateField(blank=True, null=True)
    rolling_xluft_when7s = models.DateField(blank=True, null=True)
    rolling_xluft_when7e = models.DateField(blank=True, null=True)
    rolling_xluft_when8s = models.DateField(blank=True, null=True)
    rolling_xluft_when8e = models.DateField(blank=True, null=True)
    rolling_xluft_when9s = models.DateField(blank=True, null=True)
    rolling_xluft_when9e = models.DateField(blank=True, null=True)
    rolling_xluft_cmts = models.TextField(blank=True)

    lse_title = 'LSE'
    lse_message = """Check the rolling median LSE plot. This should be < 0.0001 or so if the site has two detectors
and an M16 controller. If it is uniformly zero (i.e. the site has only one detector), confirm that:

<ul>
<li>1. If the site has an M16 controller, that the XSM setting is on (which removes ghosts)</li>
<li>2. If the site has an M15 controller, that the team used the Dohe method to correct ghosts</li>
<li>3. If the LSE is large, inquire why</li>
</ul>"""
    lse_present = models.CharField(max_length=1, choices=_choices_lse)
    lse_follow_up = models.CharField(max_length=1, choices=_choices_yn)
    lse_cmts = models.TextField(blank=True)

    sg_title = 'SG stretch'
    sg_message = """Check the rolling median SG stretch plot, considering both the median and individual
spectra data points. Large deviations in the median, or repeating diurnal variations cen-
tered on solar noon in the individual values indicative of diurnal cycles > 1 ppm should
be brought to the PI’s attention, especially if they correspond with deviations in Xluft.
(These diurnal variations may be difficult to see in long time series.)"""
    sg_present = models.CharField(max_length=1, choices=_choices_ynu)
    sg_when0s = models.DateField(blank=True, null=True)
    sg_when0e = models.DateField(blank=True, null=True)
    sg_when1s = models.DateField(blank=True, null=True)
    sg_when1e = models.DateField(blank=True, null=True)
    sg_when2s = models.DateField(blank=True, null=True)
    sg_when2e = models.DateField(blank=True, null=True)
    sg_when3s = models.DateField(blank=True, null=True)
    sg_when3e = models.DateField(blank=True, null=True)
    sg_when4s = models.DateField(blank=True, null=True)
    sg_when4e = models.DateField(blank=True, null=True)
    sg_when5s = models.DateField(blank=True, null=True)
    sg_when5e = models.DateField(blank=True, null=True)
    sg_when6s = models.DateField(blank=True, null=True)
    sg_when6e = models.DateField(blank=True, null=True)
    sg_when7s = models.DateField(blank=True, null=True)
    sg_when7e = models.DateField(blank=True, null=True)
    sg_when8s = models.DateField(blank=True, null=True)
    sg_when8e = models.DateField(blank=True, null=True)
    sg_when9s = models.DateField(blank=True, null=True)
    sg_when9e = models.DateField(blank=True, null=True)
    sg_cmts = models.TextField(blank=True)

    nonlin_title = 'Nonlinearity'
    nonlin_message = """Examine plots of rolling derivative of DIP vs. CL, the DIP vs. CL scatter plot, and the 
timeseries of DIP itself. Sodankyla 2017 data (with a known nonlinearity) had a DIP vs.
O2 CL slope of 0.01, such a slope should be near 0 when no nonlinearity is present."""
    nonlin_present = models.CharField(max_length=1, choices=_choices_ynu)
    nonlin_when0s = models.DateField(blank=True, null=True)
    nonlin_when0e = models.DateField(blank=True, null=True)
    nonlin_when1s = models.DateField(blank=True, null=True)
    nonlin_when1e = models.DateField(blank=True, null=True)
    nonlin_when2s = models.DateField(blank=True, null=True)
    nonlin_when2e = models.DateField(blank=True, null=True)
    nonlin_when3s = models.DateField(blank=True, null=True)
    nonlin_when3e = models.DateField(blank=True, null=True)
    nonlin_when4s = models.DateField(blank=True, null=True)
    nonlin_when4e = models.DateField(blank=True, null=True)
    nonlin_when5s = models.DateField(blank=True, null=True)
    nonlin_when5e = models.DateField(blank=True, null=True)
    nonlin_when6s = models.DateField(blank=True, null=True)
    nonlin_when6e = models.DateField(blank=True, null=True)
    nonlin_when7s = models.DateField(blank=True, null=True)
    nonlin_when7e = models.DateField(blank=True, null=True)
    nonlin_when8s = models.DateField(blank=True, null=True)
    nonlin_when8e = models.DateField(blank=True, null=True)
    nonlin_when9s = models.DateField(blank=True, null=True)
    nonlin_when9e = models.DateField(blank=True, null=True)
    nonlin_cmts = models.TextField(blank=True)

    additional_title = ''
    additional_cmts = models.TextField(blank=True)

    def sections_with_values(self):
        sections = super().sections()

        # Replace each question with its corresponding value
        for section in sections:
            for question in section['questions']:
                for key, fieldset in question.items():
                    if isinstance(fieldset, str):
                        # message and title are not actual field sets
                        continue
                    elif key == 'whens':
                        for ifield, (startfield, endfield) in enumerate(fieldset):
                            fieldset[ifield] = self._format_date_range(startfield.name, endfield.name)
                        question['whens'] = [w for w in fieldset if w]
                    else:
                        for ifield, field in enumerate(fieldset):
                            getter = getattr(self, f'get_{field.name}_display', None)
                            value = getter() if getter else getattr(self, field.name)
                            fieldset[ifield] = {'label': field.verbose_name, 'value': value}

        return sections

    def sections_with_values_no_preface(self):
        return self.sections_with_values()[1:]

    def _format_date_range(self, start_key, end_key):
        start = getattr(self, start_key, None)
        end = getattr(self, end_key, None)

        if start is None and end is None:
            return None

        if start is not None:
            start = start.strftime('%Y-%m-%d')
        else:
            start = 'beginning'

        if end is not None:
            end = end.strftime('%Y-%m-%d')
        else:
            end = 'end'

        return f'{start} to {end}'

    def _iter_fields_with_prefixes(self, *prefixes):
        for field in self._meta.get_fields():
            key = field.name
            for prefix in prefixes:
                if key.startswith(prefix):
                    yield key, field

    def _get_field_by_key(self, key):
        for field in self._meta.get_fields():
            if field.name == key:
                return field

        raise KeyError(key)