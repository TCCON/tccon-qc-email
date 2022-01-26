from django.db import models
from tcconauth import utils


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


# Create your models here.
class QCReport(models.Model):
    reviewer = models.CharField(max_length=128, verbose_name='Reviewer')
    site = models.CharField(max_length=2, choices=utils.get_sites_as_choices())
    netcdf_files = models.TextField()

    timing_present = models.CharField(max_length=1, choices=_choices_ynu, verbose_name='Is timing error present')
    timing_reproc = models.CharField(max_length=1, choices=_choices_ynms, verbose_name='Requires reprocessing')
    timing_when0s = models.DateField(blank=True, verbose_name='Start of first timing error')
    timing_when0e = models.DateField(blank=True, verbose_name='End of first timing error')
    timing_when1s = models.DateField(blank=True, verbose_name='Start of second timing error')
    timing_when1e = models.DateField(blank=True, verbose_name='End of second timing error')
    timing_when2s = models.DateField(blank=True, verbose_name='Start of third timing error')
    timing_when2e = models.DateField(blank=True, verbose_name='End of third timing error')
    timing_when3s = models.DateField(blank=True, verbose_name='Start of fourth timing error')
    timing_when3e = models.DateField(blank=True, verbose_name='End of fourth timing error')
    timing_when4s = models.DateField(blank=True, verbose_name='Start of fifth timing error')
    timing_when4e = models.DateField(blank=True, verbose_name='End of fifth timing error')
    timing_when5s = models.DateField(blank=True, verbose_name='Start of sixth timing error')
    timing_when5e = models.DateField(blank=True, verbose_name='End of sixth timing error')
    timing_when6s = models.DateField(blank=True, verbose_name='Start of seventh timing error')
    timing_when6e = models.DateField(blank=True, verbose_name='End of seventh timing error')
    timing_when7s = models.DateField(blank=True, verbose_name='Start of eighth timing error')
    timing_when7e = models.DateField(blank=True, verbose_name='End of eighth timing error')
    timing_when8s = models.DateField(blank=True, verbose_name='Start of ninth timing error')
    timing_when8e = models.DateField(blank=True, verbose_name='End of ninth timing error')
    timing_when9s = models.DateField(blank=True, verbose_name='Start of tenth timing error')
    timing_when9e = models.DateField(blank=True, verbose_name='End of tenth timing error')
    timing_cmts = models.TextField(blank=True)

    pres_err_present = models.CharField(max_length=1, choices=_choices_ynu)
    pres_err_reproc = models.CharField(max_length=1, choices=_choices_ynms)
    pres_err_when0s = models.DateField(blank=True)
    pres_err_when0e = models.DateField(blank=True)
    pres_err_when1s = models.DateField(blank=True)
    pres_err_when1e = models.DateField(blank=True)
    pres_err_when2s = models.DateField(blank=True)
    pres_err_when2e = models.DateField(blank=True)
    pres_err_when3s = models.DateField(blank=True)
    pres_err_when3e = models.DateField(blank=True)
    pres_err_when4s = models.DateField(blank=True)
    pres_err_when4e = models.DateField(blank=True)
    pres_err_when5s = models.DateField(blank=True)
    pres_err_when5e = models.DateField(blank=True)
    pres_err_when6s = models.DateField(blank=True)
    pres_err_when6e = models.DateField(blank=True)
    pres_err_when7s = models.DateField(blank=True)
    pres_err_when7e = models.DateField(blank=True)
    pres_err_when8s = models.DateField(blank=True)
    pres_err_when8e = models.DateField(blank=True)
    pres_err_when9s = models.DateField(blank=True)
    pres_err_when9e = models.DateField(blank=True)
    pres_err_cmts = models.TextField(blank=True)

    nans_present = models.CharField(max_length=1, choices=_choices_yn)
    nans_reproc = models.CharField(max_length=1, choices=_choices_ynms)
    nans_cmts = models.TextField(blank=True)

    qc_flags_present = models.CharField(max_length=1, choices=_choices_ynu)
    qc_flags_reproc = models.CharField(max_length=1, choices=_choices_ynms)
    qc_flags_cmts = models.TextField(blank=True)

    rolling_xluft_present = models.CharField(max_length=1, choices=_choices_ynu)
    rolling_xluft_flag = models.CharField(max_length=1, choices=_choices_ynu)
    rolling_xluft_when0s = models.DateField(blank=True)
    rolling_xluft_when0e = models.DateField(blank=True)
    rolling_xluft_when1s = models.DateField(blank=True)
    rolling_xluft_when1e = models.DateField(blank=True)
    rolling_xluft_when2s = models.DateField(blank=True)
    rolling_xluft_when2e = models.DateField(blank=True)
    rolling_xluft_when3s = models.DateField(blank=True)
    rolling_xluft_when3e = models.DateField(blank=True)
    rolling_xluft_when4s = models.DateField(blank=True)
    rolling_xluft_when4e = models.DateField(blank=True)
    rolling_xluft_when5s = models.DateField(blank=True)
    rolling_xluft_when5e = models.DateField(blank=True)
    rolling_xluft_when6s = models.DateField(blank=True)
    rolling_xluft_when6e = models.DateField(blank=True)
    rolling_xluft_when7s = models.DateField(blank=True)
    rolling_xluft_when7e = models.DateField(blank=True)
    rolling_xluft_when8s = models.DateField(blank=True)
    rolling_xluft_when8e = models.DateField(blank=True)
    rolling_xluft_when9s = models.DateField(blank=True)
    rolling_xluft_when9e = models.DateField(blank=True)
    rolling_xluft_cmts = models.TextField(blank=True)

    lse_present = models.CharField(max_length=1, choices=_choices_lse)
    lse_follow_up = models.CharField(max_length=1, choices=_choices_yn)
    lse_cmts = models.TextField(blank=True)

    sg_present = models.CharField(max_length=1, choices=_choices_ynu)
    sg_when0s = models.DateField(blank=True)
    sg_when0e = models.DateField(blank=True)
    sg_when1s = models.DateField(blank=True)
    sg_when1e = models.DateField(blank=True)
    sg_when2s = models.DateField(blank=True)
    sg_when2e = models.DateField(blank=True)
    sg_when3s = models.DateField(blank=True)
    sg_when3e = models.DateField(blank=True)
    sg_when4s = models.DateField(blank=True)
    sg_when4e = models.DateField(blank=True)
    sg_when5s = models.DateField(blank=True)
    sg_when5e = models.DateField(blank=True)
    sg_when6s = models.DateField(blank=True)
    sg_when6e = models.DateField(blank=True)
    sg_when7s = models.DateField(blank=True)
    sg_when7e = models.DateField(blank=True)
    sg_when8s = models.DateField(blank=True)
    sg_when8e = models.DateField(blank=True)
    sg_when9s = models.DateField(blank=True)
    sg_when9e = models.DateField(blank=True)
    sg_cmts = models.TextField(blank=True)

    nonlin_present = models.CharField(max_length=1, choices=_choices_ynu)
    nonlin_when0s = models.DateField(blank=True)
    nonlin_when0e = models.DateField(blank=True)
    nonlin_when1s = models.DateField(blank=True)
    nonlin_when1e = models.DateField(blank=True)
    nonlin_when2s = models.DateField(blank=True)
    nonlin_when2e = models.DateField(blank=True)
    nonlin_when3s = models.DateField(blank=True)
    nonlin_when3e = models.DateField(blank=True)
    nonlin_when4s = models.DateField(blank=True)
    nonlin_when4e = models.DateField(blank=True)
    nonlin_when5s = models.DateField(blank=True)
    nonlin_when5e = models.DateField(blank=True)
    nonlin_when6s = models.DateField(blank=True)
    nonlin_when6e = models.DateField(blank=True)
    nonlin_when7s = models.DateField(blank=True)
    nonlin_when7e = models.DateField(blank=True)
    nonlin_when8s = models.DateField(blank=True)
    nonlin_when8e = models.DateField(blank=True)
    nonlin_when9s = models.DateField(blank=True)
    nonlin_when9e = models.DateField(blank=True)
    nonlin_cmts = models.TextField(blank=True)

    additional_cmts = models.TextField(blank=True)
