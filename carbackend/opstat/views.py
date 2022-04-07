import traceback

from django.db import transaction, Error as DBError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone as tz
from .models import SiteStatus, SiteStatusHistory, PageNews


# Create your views here.
def index(request):
    # this retrieves the value of the status parameter in the URL, e.g. /opstat/?status=needlogin
    # https://www.dev2qa.com/how-to-pass-multiple-parameters-via-url-in-django/
    status = request.GET.get('status', None)
    site_id = request.GET.get('site', None)
    site_info = SiteStatus.objects.all()

    # Get the newest page news, check if we should show it
    news = PageNews.objects.last()
    if news is None:
        show_news = False
    else:
        show_news = (news.display == PageNews.DISPLAY_ALWAYS) or (news.display == PageNews.DISPLAY_UNTIL and tz.now().date() < news.hide_after)

    context = {'site_info': site_info, 'date': tz.now(), 'user': request.user, 'show_news': show_news, 'news': news}
    if status == 'goodupdate':
        updated_site = request.GET.get('site', '')
        context['message'] = '{} successfully updated'.format(updated_site)
    elif status == 'needlogin':
        context['message'] = 'You must log in to update a site status'
    elif status == 'missingperm':
        context['message'] = 'You do not have permission to update {} site status'.format(site_id)
    return render(request, 'opstat/index.html', context=context)


def car(request):
    site_info = SiteStatus.objects.all()
    lines = []
    for info in site_info:
        if info.status == 'r':
            # Do not display "retired" sites by default
            continue

        s = '{name}::{status}::{descr} [{user} {date}]'.format(
            name=info.sitename, status=info.pretty_status, descr=info.description, user=info.username, date=info.date.strftime('%Y%m%d')
        )
        lines.append(s)
    data = '\n'.join(lines)
    return HttpResponse(data.encode('utf8'), content_type='text/plain')


def history(request, site_id):
    order = request.GET.get('order', 'newest')
    order_by = 'date' if order == 'oldest' else '-date'
    statuses = SiteStatusHistory.objects.filter(site=site_id).order_by(order_by)
    info = SiteStatus.objects.get(siteid=site_id)
    context = {'site': site_id, 'sitename': info.sitename, 'statuses': statuses, 'oldest_first': order == 'oldest'}
    return render(request, 'opstat/site_history.html', context=context)


def submitupdate(request, site_id, error_message=None):
    #import pdb; pdb.set_trace()
    req_perm = 'opstat.{}_status'.format(site_id)
    if not request.user.is_authenticated:
        url = '{}?status=needlogin'.format(reverse('opstat:index'))
        return redirect(url)
    elif not request.user.has_perm(req_perm):
        url = '{}?status=missingperm&site={}'.format(reverse('opstat:index'), site_id)
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
    username = request.user.get_username()
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
            site_info.username = username
            site_info.save()

            new_hist = SiteStatusHistory(site=site_info, date=now, status=status, description=description, username=username)
            new_hist.save()
    except DBError as err:
        context = {'siteid': site_id, 'error': traceback.format_exception_only(type(err), err)[-1].strip()}
        return render(request, 'opstat/updatefailed.html', context=context)
    else:
        url = '{}?status=goodupdate&site={}'.format(reverse('opstat:index'), site_info.sitename)
        return HttpResponseRedirect(url)


def api_get_all_statuses_by_id(request):
    site_info = SiteStatus.objects.all()
    data = dict()
    for info in site_info:
        if info.status == 'r':
            # Do not display "retired" sites by default
            continue

        data[info.siteid] = _status_obj_to_dict(info)
    return JsonResponse(data, status=200)


def api_get_all_statuses_by_name(request):
    site_info = SiteStatus.objects.all()
    data = dict()
    for info in site_info:
        if info.status == 'r':
            # Do not display "retired" sites by default
            continue

        data[info.sitename] = _status_obj_to_dict(info)
    return JsonResponse(data, status=200)


def api_get_status_by_id(request, site_id):
    try:
        site_info = SiteStatus.objects.get(siteid=site_id)
    except SiteStatus.DoesNotExist:
        data = {'error': 'No side with ID={sid} found'.format(sid=site_id)}
        return JsonResponse(data, status=406)
    else:
        return JsonResponse(_status_obj_to_dict(site_info), status=200)


def api_get_status_by_name(request, name):
    try:
        # Some sites have multiple instruments with the same name, e.g. Lauder has lh, ll, and lr
        # all under "Lauder", but only one should have a status other than "retired".
        site_info = SiteStatus.objects.get(sitename=name, status__in='yn')
    except SiteStatus.DoesNotExist:
        data = {'error': 'No side with name={name} found'.format(name=name)}
        return JsonResponse(data, status=406)
    except SiteStatus.MultipleObjectsReturned:
        data = {'error': 'Multiple sites with name={name} found'.format(name=name)}
        return JsonResponse(data, status=406)
    else:
        return JsonResponse(_status_obj_to_dict(site_info), status=200)


def _status_obj_to_dict(obj):
    return {
        'id': obj.siteid,
        'name': obj.sitename,
        'status': obj.pretty_status,
        'descr': obj.description,
        'user': obj.username,
        'date': obj.date.strftime('%Y%m%d'),
        'display_descr': '{descr} [{user} {date}]'.format(descr=obj.description, user=obj.username, date=obj.date.strftime('%Y%m%d'))
    }