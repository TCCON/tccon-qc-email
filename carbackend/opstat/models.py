from django.db import models


def _format_status(status):
    if status == 'y':
        return 'Yes'
    elif status == 'n':
        return 'No'
    elif status == 'r':
        return 'Replaced/retired'


# Create your models here.
class SiteStatus(models.Model):
    siteid = models.CharField(max_length=2, primary_key=True)
    sitename = models.CharField(max_length=30)
    username = models.CharField(max_length=30, null=True)
    date = models.DateTimeField(null=True)
    status = models.CharField(max_length=1, choices=(('y', 'Yes'), ('n', 'No')))
    description = models.CharField(max_length=150, null=True)

    class Meta:
        verbose_name_plural = 'site statuses'
        permissions = [
            ("ae_status", "Can update the Ascension Island site status"),
            ("an_status", "Can update the Anmyeondo site status"),
            ("bi_status", "Can update the Bialystok site status"),
            ("br_status", "Can update the Bremen site status"),
            ("bu_status", "Can update the Burgos site status"),
            ("ci_status", "Can update the Caltech/Pasadena site status"),
            ("db_status", "Can update the Darwin site status"),
            ("df_status", "Can update the Dryden site status"),
            ("et_status", "Can update the East Trout Lake site status"),
            ("eu_status", "Can update the Eureka site status"),
            ("fc_status", "Can update the Four Corners site status"),
            ("gm_status", "Can update the Garmisch site status"),
            ("ht_status", "Can update the Arrival Heights site status"),
            ("hw_status", "Can update the Harwell site status"),
            ("if_status", "Can update the Indianapolis site status"),
            ("iz_status", "Can update the Izana site status"),
            ("jf_status", "Can update the JPL site status"),
            ("js_status", "Can update the Saga site status"),
            ("jx_status", "Can update the JPL site status"),
            ("ka_status", "Can update the Karlsruhe site status"),
            ("lh_status", "Can update the Lauder site status"),
            ("ll_status", "Can update the Lauder site status"),
            ("lr_status", "Can update the Lauder site status"),
            ("ma_status", "Can update the Manaus site status"),
            ("ni_status", "Can update the Nicosia site status"),
            ("ny_status", "Can update the Ny-Alesund site status"),
            ("oc_status", "Can update the Lamont site status"),
            ("or_status", "Can update the Orleans site status"),
            ("pa_status", "Can update the Park Falls site status"),
            ("pr_status", "Can update the Paris site status"),
            ("ra_status", "Can update the Reunion Island site status"),
            ("rj_status", "Can update the Rikubetsu site status"),
            ("so_status", "Can update the Sodankyla site status"),
            ("tk_status", "Can update the Tsukuba site status"),
            ("we_status", "Can update the Jena site status"),
            ("wg_status", "Can update the Wollongong site status"),
            ("yk_status", "Can update the Yekaterinburg site status"),
            ("zs_status", "Can update the Zugspitze site status"),
        ]

    @property
    def pretty_status(self):
        return _format_status(self.status)


class SiteStatusHistory(models.Model):
    class Meta:
        verbose_name_plural = 'site status history'
    site = models.ForeignKey(SiteStatus, on_delete=models.PROTECT)
    username = models.CharField(max_length=30, null=True)
    date = models.DateTimeField(null=True)
    status = models.CharField(max_length=1, choices=(('y', 'Yes'), ('n', 'No')))
    description = models.CharField(max_length=150, null=True)

    @property
    def pretty_status(self):
        return _format_status(self.status)


class PageNews(models.Model):
    class Meta:
        verbose_name_plural = 'page news'

    DISPLAY_ALWAYS = 'ALWAYS'
    DISPLAY_NEVER = 'NEVER'
    DISPLAY_UNTIL = 'UNTIL'
    DISPLAY_CHOICES = [
        (DISPLAY_UNTIL, 'Show until "hide after" date'),
        (DISPLAY_ALWAYS, 'Always show'),
        (DISPLAY_NEVER, 'Never show')
    ]

    message = models.TextField()
    author = models.CharField(max_length=64)
    date = models.DateTimeField(auto_now=True)
    hide_after = models.DateField(null=True)
    display = models.CharField(max_length=8, choices=DISPLAY_CHOICES, default=DISPLAY_UNTIL)
