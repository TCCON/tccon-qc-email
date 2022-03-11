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
                'questions': self._make_section('pres_err_', 'nans_', 'qc_flags_', 'timing_', 'rolling_xluft_'),
                'intro': """Data with any of the issues here generally requires reprocessing or release flagging (i.e.
spectra to be flagged on tccondata.org and withheld from the public files). If an issue here
does not require reprocessing or flagging, please describe why in the comments."""
            },
            {
                'name': 'Informational quality checks',
                'questions': self._make_section('hcl_vsf_', 'o2_fs_', 'nonlin_', 'sg_', 'lse_'),
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
            'whens_type': 'none',
            'cmts': [],
            'message': mark_safe(self._get_question_message(prefix)),
            'title': self._get_question_title(prefix)
        }

        whens_single_date = False
        whens_paired_dates = False
        for key, field in self._iter_fields_with_prefixes(prefix):
            m = re.search(r'(.+_when[0-9]+)s?$', key)
            if m:
                if key.endswith('s'):
                    key2 = m.group(1) + 'e'
                    fields['whens'].append((field, self._get_field_by_key(key2)))
                    whens_paired_dates = True
                else:
                    fields['whens'].append((field, None))
                    whens_single_date = True
            elif re.search(r'when[0-9]+e$', key):
                # We handle the end fields with their paired start fields
                pass
            elif key.endswith('cmts'):
                fields['cmts'].append(field)
            else:
                fields['mcs'].append(field)

        if whens_paired_dates:
            fields['whens_type'] = 'paired'
        elif whens_single_date:
            fields['whens_type'] = 'single'
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
    site = models.CharField(max_length=2, choices=utils.get_sites_as_choices(label_fmt='name+id'), verbose_name='Site')
    netcdf_files = models.TextField(verbose_name='NetCDF files')
    modification_time = models.DateTimeField(auto_now=True)

    yes_req_date = {'timing_present': 'timing_when0s',
                    'pres_err_present': 'pres_err_when0s',
                    'rolling_xluft_present': 'rolling_xluft_when0s',
                    'sg_present': 'sg_when0s',
                    'nonlin_present': 'nonlin_when0s',
                    'hcl_vsf_unstable': 'hcl_vsf_when0',
                    'o2_fs_unstable': 'o2_fs_when0'}

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
    timing_cmts = models.TextField(blank=True, verbose_name='Comments')

    pres_err_title = 'Pressure sensor error'
    pres_err_message = 'Check the zmin - zobs plot (< 1 hPa ideal, < 3 hPa acceptable) if available. If not, check pout for drift.'
    pres_err_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Is pressure error present')
    pres_err_reproc = models.CharField(max_length=1, choices=_choices_ynms, verbose_name='Requires reprocessing')
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
    pres_err_cmts = models.TextField(blank=True, verbose_name='Comments')

    nans_title = 'Window NaNs (Non-Voigt compiler check)'
    nans_message = 'Check the bar graph of NaNs per window; if some windows are all NaNs and others not, this indicates a compiler problem. Common offenders are the CH4 5938 wCO2 windows.'
    nans_present = models.CharField(max_length=1, choices=_choices_yn, verbose_name='Mismatched numbers of NaNs')
    nans_reproc = models.CharField(max_length=1, choices=_choices_ynms, verbose_name='Required reprocessing')
    nans_cmts = models.TextField(blank=True, verbose_name='Comments (include which windows are affected)')

    qc_flags_title = 'Automatic QC flags'
    qc_flags_message = 'Check the bar graph of flags removing spectra for unusual flags removing significant numbers of spectra. xhf_error can remove more than it should at wet sites in particular.'
    qc_flags_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Unusual flags present')
    qc_flags_reproc = models.CharField(max_length=1, choices=_choices_ynms, verbose_name='Required reprocessing')
    qc_flags_cmts = models.TextField(blank=True, verbose_name='Comments (include which flags are unusual)')

    rolling_xluft_title = 'Rolling Xluft check'
    rolling_xluft_message = 'Check the 500 spectra rolling Xluft median for time periods significantly outside the ±0.004 limits'
    rolling_xluft_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Out-of-family Xluft present')
    rolling_xluft_flag = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Required release flagging')
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
    rolling_xluft_cmts = models.TextField(blank=True, verbose_name='Comments')

    lse_title = 'LSE'
    lse_message = """Check the rolling median LSE plot. This should be < 0.0001 or so if the site has two detectors
and an M16 controller. If it is uniformly zero (i.e. the site has only one detector), confirm that:

<ul>
<li>1. If the site has an M16 controller, that the XSM setting is on (which removes ghosts)</li>
<li>2. If the site has an M15 controller, that the team used the Dohe method to correct ghosts</li>
<li>3. If the LSE is large, inquire why</li>
</ul>"""
    lse_present = models.CharField(max_length=1, choices=_choices_lse, verbose_name='LSE status')
    lse_follow_up = models.CharField(max_length=1, choices=_choices_yn, verbose_name='Requires follow up')
    lse_cmts = models.TextField(blank=True, verbose_name='Comments')

    sg_title = 'SG stretch'
    sg_message = """Check the rolling median SG stretch plot, considering both the median and individual
spectra data points. Large deviations in the median, or repeating diurnal variations cen-
tered on solar noon in the individual values indicative of diurnal cycles > 1 ppm should
be brought to the PI’s attention, especially if they correspond with deviations in Xluft.
(These diurnal variations may be difficult to see in long time series.)"""
    sg_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='SG stretch suggests pointing error')
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
    sg_cmts = models.TextField(blank=True, verbose_name='Comments')

    nonlin_title = 'Nonlinearity'
    nonlin_message = """Examine time series plots of DIP and CL, along with the rolling derivative of DIP vs. CL, and the DIP vs. CL scatter plot. 
A significant relationship between DIP and CL could indicate that the detectors run in a nonlinear regime, particularly if DIP<0. (As a reference 
point, the Sodankylä DIP vs. CL slope when the signal levels were too high is around 0.01, and 0 when the light levels were limited.) At this time, we do not understand what DIP>0 indicates."""
    nonlin_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Nonlinearity present')
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
    nonlin_cmts = models.TextField(blank=True, verbose_name='Comments')

    hcl_vsf_title = 'HCl VSF'
    hcl_vsf_message = 'Check the HCl VSF plot and verify that the VSF is stable over time. If there are jumps, check if they are related to changes in the instrument.'
    hcl_vsf_unstable = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='HCl VSF is unstable/jumps')
    hcl_vsf_follow_up = models.CharField(max_length=1, choices=_choices_yn, verbose_name='Requires follow up')
    hcl_vsf_when0 = models.DateField(blank=True, null=True)
    hcl_vsf_when1 = models.DateField(blank=True, null=True)
    hcl_vsf_when2 = models.DateField(blank=True, null=True)
    hcl_vsf_when3 = models.DateField(blank=True, null=True)
    hcl_vsf_when4 = models.DateField(blank=True, null=True)
    hcl_vsf_when5 = models.DateField(blank=True, null=True)
    hcl_vsf_when6 = models.DateField(blank=True, null=True)
    hcl_vsf_when7 = models.DateField(blank=True, null=True)
    hcl_vsf_when8 = models.DateField(blank=True, null=True)
    hcl_vsf_when9 = models.DateField(blank=True, null=True)
    hcl_vsf_cmts = models.TextField(blank=True, verbose_name='Comments')

    o2_fs_title = 'O2 frequency shift'
    o2_fs_message = 'Check the o2_7885_fs time series. If the values are off the y-axix scale or there are jumps, check with the site to see if these are related to changes in the instrument.'
    o2_fs_unstable = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='O2 FS is off scale/jumps')
    o2_fs_follow_up = models.CharField(max_length=1, choices=_choices_yn, verbose_name='Requires follow up')
    o2_fs_when0 = models.DateField(blank=True, null=True)
    o2_fs_when1 = models.DateField(blank=True, null=True)
    o2_fs_when2 = models.DateField(blank=True, null=True)
    o2_fs_when3 = models.DateField(blank=True, null=True)
    o2_fs_when4 = models.DateField(blank=True, null=True)
    o2_fs_when5 = models.DateField(blank=True, null=True)
    o2_fs_when6 = models.DateField(blank=True, null=True)
    o2_fs_when7 = models.DateField(blank=True, null=True)
    o2_fs_when8 = models.DateField(blank=True, null=True)
    o2_fs_when9 = models.DateField(blank=True, null=True)
    o2_fs_cmts = models.TextField(blank=True, verbose_name='Comments')

    additional_title = ''
    additional_cmts = models.TextField(blank=True, verbose_name='Additional comments')

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
                            fieldset[ifield] = self._format_date_range(startfield.name, endfield.name if endfield is not None else None)
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
        if end_key is None:
            # Handle single date cases (like for HCl VSF) where we specify single dates instead of ranges.
            # If start is None, that means that the user did not provide a value for this date, so return
            # None. Otherwise, just format the date.
            if start is None:
                return None
            else:
                return start.strftime('%Y-%m-%d')

        end = getattr(self, end_key, None)

        # Handle paired date cases (i.e. beginning and ends). If both are None, assume no value given. If
        # one is None, then assume that is an open-ended side to the range. Otherwise, just print the
        # date range.
        #
        # NOTE: currently I have form validation set so that a date range *must* be provided (both start and end).
        # I'm just keeping this in case I want to revert.
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
