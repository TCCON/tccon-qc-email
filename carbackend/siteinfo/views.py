from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.views import View
from django.shortcuts import render, reverse, HttpResponseRedirect

from datetime import datetime as dt
import json
import re

from .forms import SiteInfoUpdateForm, ReleaseFlagUpdateForm
from .models import SiteInfoUpdate, InfoFileLocks
from . import utils


class SiteInfoList(View):
    def get(self, request):
        with open(settings.SITE_INFO_FILE) as f:
            all_site_info = json.load(f)

        sites_can_edit = self.get_sites_can_edit(request.user)
        print(sites_can_edit)

        sites = [{'id': k, 'name': v['long_name'], 'can_edit': k in sites_can_edit or 'all' in sites_can_edit} for k, v in all_site_info.items()]
        sites.sort(key=lambda s: s['id'])

        sites_can_edit = [s for s in sites if s['can_edit']]
        sites_cannot_edit = [s for s in sites if not s['can_edit']]

        context = {
            'user': request.user,
            'sites_can_edit': sites_can_edit,
            'sites_cannot_edit': sites_cannot_edit,
            'has_sites': len(sites_can_edit) > 0,
            'has_other_sites': len(sites_cannot_edit) > 0,
            'can_edit_flags': request.user.is_staff
        }

        return render(request, 'siteinfo/site_list.html', context=context)

    @staticmethod
    def get_sites_can_edit(user):
        if user.is_staff:
            return {'all'}
        permissions = user.get_all_permissions()
        sites = set()
        for perm in permissions:
            match = re.match(r'opstat.([a-z]{2})_status', perm)
            if match:
                sites.add(match.group(1))
        return sites


# Create your views here.
class ViewSiteInfo(View):
    _top_messages = {'success': 'Metadata updated successfully!'}

    def get(self, request, site_id):
        with open(settings.SITE_INFO_FILE) as f:
            all_site_info = json.load(f)

        try:
            site_info = all_site_info[site_id]
        except KeyError:
            raise Http404('No existing site information for site "{}"'.format(site_id))

        msg_key = request.GET.get('msg', None)
        msg = self._top_messages.get(msg_key, '')

        context = {
            'site_id': site_id,
            'info': site_info,
            'can_edit': _can_edit_site(request.user, site_id),
            'msg': msg
        }
        return render(request, 'siteinfo/view_site_info.html', context=context)


class EditSiteInfo(View):
    # TODOs:
    #   - Actually submit the form (need to add form tags), validate the data, update the json, and update the database
    #   - Add an edit button to the view page if the user has that permission
    #   - Replace the Http404 error below with a redirect to a "You don't have that permission" page
    #   - Have confirmation page after saving changes (maybe redirect to the view page?)
    #   - Might also be nice if going back to main without saving put a message "Changes not saved" at the top
    #   - Add a column to the front page to view the release flags as well.
    #       * Don't know if those should be editable, maybe only by admins?
    def get(self, request, site_id):
        user = request.user
        if not _can_edit_site(user, site_id):
            # TODO: replace
            raise Http404('You cannot edit this site!')

        site_info = _get_site_info(site_id)
        form = SiteInfoUpdateForm(initial=site_info)
        context = self._make_context(form, site_id, site_info)
        return render(request, 'siteinfo/edit_site_info.html', context=context)

    def post(self, request, site_id):
        form = SiteInfoUpdateForm(request.POST)
        if form.is_valid():
            # form.save(user=request.user, site_info=self._get_site_info(site_id))
            site_info = _get_site_info(site_id)
            update = form.save(commit=False)
            update.user_updated = request.user
            update.site_id = site_id
            for field in form.fixed_fields():
                setattr(update, field, site_info[field])

            with transaction.atomic():
                self._write_site_info(update, site_id)
                update.save()
            url = '{}/?msg=success'.format(reverse('siteinfo:view', args=(site_id,)).rstrip('?').rstrip('/'))
            return HttpResponseRedirect(url)
        else:
            context = self._make_context(form, site_id)
            return render(request, 'siteinfo/edit_site_info.html', context=context)

    @staticmethod
    def _write_site_info(update, site_id):
        all_site_info = InfoFileLocks.read_json_file(settings.SITE_INFO_FILE)
        site_info = all_site_info.setdefault(site_id, dict())
        for key in SiteInfoUpdate.standard_fields():
            site_info[key] = str(getattr(update, key))

        utils.backup_file_rolling(settings.SITE_INFO_FILE)
        InfoFileLocks.write_json_file(settings.SITE_INFO_FILE, all_site_info, indent=4)

    def _make_context(self, form, site_id, site_info=None):
        if site_info is None:
            site_info = _get_site_info(site_id)

        fixed_fields = SiteInfoUpdateForm.fixed_fields()
        fixed_values = {f: {'value': site_info[f], 'name': self._pretty_name(f)} for f in fixed_fields}

        context = {
            'form': form,
            'fixed_values': fixed_values,
            'long_name': site_info.get('long_name', '??'),
            'site_id': site_id,
            'contact': utils.get_contact()
        }
        return context

    @staticmethod
    def _pretty_name(field):
        field = field.replace('_', ' ').capitalize()
        field = re.sub(r'\b[Dd][Oo][Ii]\b', 'DOI', field)
        return field


class ViewReleaseFlags(View):
    _messages = {
        'edited': 'Updated flag number {flag_id} for site {site_id}',
        'deleted': 'Deleted flag number {flag_id} for site {site_id}',
        'deletefailed': 'Failed to delete {flag_id} for site {site_id}'
    }

    def get(self, request, site_id):
        with open(settings.SITE_INFO_FILE) as f:
            all_info = json.load(f)
            long_name = all_info.get(site_id, dict()).get('long_name', '?')
        with open(settings.RELEASE_FLAGS_FILE) as f:
            all_flags = json.load(f)
        with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
            flag_defs = {v: k for k, v in json.load(f)['definitions'].items()}

        site_flags = []
        for k, v in all_flags.items():
            if not k.startswith(site_id):
                continue

            _, n, start_str, end_str = k.split('_')
            flag_value = v['value']
            v.setdefault('name', flag_defs[flag_value])
            v.setdefault('comment', '')

            meta = dict()
            meta['n'] = int(n)
            meta['n_str'] = str(meta['n'])
            meta['start_date'] = dt.strptime(start_str, '%Y%m%d').date()
            meta['end_date'] = dt.strptime(end_str, '%Y%m%d').date()

            site_flags.append({'info': v, 'meta': meta})

        site_flags.sort(key=lambda el: el['meta']['n'])

        msg_key = request.GET.get('msg', None)
        if msg_key:
            flag_id = request.GET.get('flag', '??')
            msg = self._messages.get(msg_key, '??').format(site_id=site_id, flag_id=flag_id)
        else:
            msg = ''

        context = {
            'site_id': site_id,
            'long_name': long_name,
            'msg': msg,
            'has_flags': len(site_flags) > 0,
            'flags': site_flags,
            'can_edit_flags': request.user.is_staff
        }

        return render(request, 'siteinfo/view_release_flags.html', context=context)


class DeleteReleaseFlags(View):
    def post(self, request, site_id, flag_id):
        if not _can_edit_site(request.user, site_id):
            return Http404('You do not have permission to edit site "{}"'.format(site_id))

        flag_dict = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_FILE)
        try:
            key = _find_flag_key(site_id, flag_id, flag_dict)
        except Http404:
            url = '{}/?msg=deletefailed&flag={}'.format(reverse('siteinfo:flags', args=(site_id,)).rstrip('?').rstrip('/'), flag_id)
            return HttpResponseRedirect(url)

        flag_dict.pop(key)
        ReleaseFlagUpdateForm.update_flag_file(flag_dict)
        url = '{}/?msg=deleted&flag={}'.format(reverse('siteinfo:flags', args=(site_id,)).rstrip('?').rstrip('/'), flag_id)
        return HttpResponseRedirect(url)


class EditReleaseFlags(View):
    def get(self, request, site_id, flag_id):
        if not _can_edit_site(request.user, site_id):
            return Http404('You do not have permission to edit site "{}"'.format(site_id))

        if flag_id == 'new':
            form = ReleaseFlagUpdateForm()
            flag_id = self._get_next_flag_id(site_id)
        elif re.match(r'\d+', flag_id):
            form = ReleaseFlagUpdateForm(initial=self._get_current_flag_info(site_id, flag_id))
        else:
            raise Http404('Invalid flag ID')
        context = self._make_context(form, site_id, flag_id)
        return render(request, 'siteinfo/edit_release_flags.html', context=context)

    def post(self, request, site_id, flag_id):
        if not _can_edit_site(request.user, site_id):
            return Http404('You do not have permission to edit site "{}"'.format(site_id))

        form = ReleaseFlagUpdateForm(request.POST)
        if form.is_valid():
            form.save_to_json(site_id, flag_id)
            url = '{}/?msg=edited&flag={}'.format(reverse('siteinfo:flags', args=(site_id,)).rstrip('?').rstrip('/'), flag_id)
            return HttpResponseRedirect(url)
        else:
            context = self._make_context(form, site_id, flag_id)
            return render(request, 'siteinfo/edit_release_flags.html', context=context)

    @staticmethod
    def _make_context(form, site_id, flag_id):
        site_info = _get_site_info(site_id)

        return {
            'site_id': site_id,
            'flag_id': flag_id,
            'long_name': site_info.get('long_name', '??'),
            'form': form
        }

    @staticmethod
    def _get_current_flag_info(site_id, flag_id):
        flag_dict = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_FILE)
        key = _find_flag_key(site_id, flag_id, flag_dict)
        _, _, start_str, end_str = key.split('_')
        flag = flag_dict[key]
        flag['start'] = dt.strptime(start_str, '%Y%m%d').date()
        flag['end'] = dt.strptime(end_str, '%Y%m%d').date()
        return flag

    @staticmethod
    def _get_next_flag_id(site_id):
        flag_dict = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_FILE)
        n = 0
        for key in flag_dict:
            if key.startswith(site_id):
                _, key_n, _, _ = key.split('_')
                key_n = int(key_n)
                if key_n > n:
                    n = key_n
        return str(n + 1)


def _can_edit_site(user, site_id):
    return user.has_perm('opstat.{}_status'.format(site_id)) or user.is_staff


def _get_site_info(site_id):
    all_site_info = InfoFileLocks.read_json_file(settings.SITE_INFO_FILE)
    try:
        return all_site_info[site_id]
    except KeyError:
        raise Http404('No existing site information for site "{}"'.format(site_id))


def _find_flag_key(site_id, flag_id, flag_dict):
    key_regex = re.compile(r'{}_0*{}'.format(site_id, int(flag_id)))
    for key in flag_dict:
        if key_regex.match(key):
            return key

    raise Http404('Unable to find flag for site "{}" flag number "{}"'.format(site_id, flag_id))