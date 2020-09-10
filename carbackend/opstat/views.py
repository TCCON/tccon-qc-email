import traceback

from django.db import transaction, Error as DBError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone as tz
from .models import SiteStatus, SiteStatusHistory


# Create your views here.
def index(request):
    # this retrieves the value of the status parameter in the URL, e.g. /opstat/?status=needlogin
    status = request.GET.get('status', None)
    print('status =', status)
    site_info = SiteStatus.objects.all()
    context = {'site_info': site_info, 'date': tz.now(), 'user': request.user}
    if status == 'goodupdate':
        updated_site = request.GET.get('site', '')
        context['message'] = '{} successfully updated'.format(updated_site)
    elif status == 'needlogin':
        context['message'] = 'You must log in to update a site status'
    return render(request, 'opstat/index.html', context=context)


def car(request):
    site_info = SiteStatus.objects.all()
    lines = []
    for info in site_info:
        s = '{name}::{status}::{descr} [{user} {date}]'.format(
            name=info.sitename, status=info.status, descr=info.description, user=info.username, date=info.date.strftime('%Y%m%d')
        )
        lines.append(s)
    data = '\n'.join(lines)
    return HttpResponse(data.encode('utf8'), content_type='text/plain')


def submitupdate(request, site_id, error_message=None):
    #import pdb; pdb.set_trace()
    if not request.user.is_authenticated:
        url = '{}?status=needlogin'.format(reverse('opstat:index'))
        return redirect(url)
    curr_info = get_object_or_404(SiteStatus, pk=site_id)
    context = {'sitename': curr_info.sitename, 'siteid': curr_info.siteid}
    if error_message:
        context['error_message'] = error_message
    return render(request, 'opstat/submitupdate.html', context=context)


def update(request, site_id):
    if not request.user.is_authenticated:
        url = '{}?status=needlogin'.format(reverse('opstat:index'))
        return redirect(url)
    site_info = get_object_or_404(SiteStatus, pk=site_id)
    status = request.POST.get('status', None)
    description = request.POST.get('description', '')
    if status is None:
        return submitupdate(request, site_id, error_message='You must choose an option for the "Operational?" query')

    now = tz.now()
    try:
        # Update the status table and the history table at the same time. If something goes wrong, roll back those
        # changes that have already been executed. This *should* keep the two in sync. Also let the user know that
        # something went wrong.
        #
        # Not sure if this still introduces a race condition
        # see https://docs.djangoproject.com/en/3.1/ref/models/expressions/#avoiding-race-conditions-using-f
        with transaction.atomic():
            site_info.status = status
            site_info.description = description
            site_info.date = now
            site_info.save()

            new_hist = SiteStatusHistory(site=site_info, date=now, status=status, description=description)
            new_hist.save()
    except DBError as err:
        context = {'siteid': site_id, 'error': traceback.format_exception_only(type(err), err)[-1].strip()}
        return render(request, 'opstat/updatefailed.html', context=context)
    else:
        url = '{}?status=goodupdate&site={}'.format(reverse('opstat:index'), site_info.sitename)
        return HttpResponseRedirect(url)
