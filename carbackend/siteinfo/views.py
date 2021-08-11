from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.views import View
from django.shortcuts import render, reverse, HttpResponseRedirect

from datetime import datetime as dt
import json
import re

from .forms import SiteInfoUpdateForm
from .models import SiteInfoUpdate, InfoFileLocks
from . import utils


class SiteInfoList(View):
    def get(self, request):
        with open(settings.SITE_INFO_FILE) as f:
            all_site_info = json.load(f)

        sites_can_edit = self.get_sites_can_edit(request.user)
        print(sites_can_edit)

        sites = [{'id': k, 'name': v['long_name'], 'can_edit': k in sites_can_edit} for k, v in all_site_info.items()]
        sites.sort(key=lambda s: s['id'])

        sites_can_edit = [s for s in sites if s['can_edit']]
        sites_cannot_edit = [s for s in sites if not s['can_edit']]

        context = {
            'user': request.user,
            'sites_can_edit': sites_can_edit,
            'sites_cannot_edit': sites_cannot_edit,
            'has_sites': len(sites_can_edit) > 0
        }

        return render(request, 'siteinfo/site_list.html', context=context)

    @staticmethod
    def get_sites_can_edit(user):
        permissions = user.get_all_permissions()
        sites = set()
        for perm in permissions:
            match = re.match(r'opstat.([a-z]{2})_status', perm)
            if match:
                sites.add(match.group(1))
        return sites


# Create your views here.
class ViewSiteInfo(View):
    def get(self, request, site_id):
        with open(settings.SITE_INFO_FILE) as f:
            all_site_info = json.load(f)

        try:
            site_info = all_site_info[site_id]
        except KeyError:
            raise Http404('No existing site information for site "{}"'.format(site_id))

        context = {
            'site_id': site_id,
            'info': site_info,
            'can_edit': _can_edit_site(request.user, site_id)
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

        site_info = self._get_site_info(site_id)
        form = SiteInfoUpdateForm(initial=site_info)
        context = self._make_context(form, site_id, site_info)
        return render(request, 'siteinfo/edit_site_info.html', context=context)

    def post(self, request, site_id):
        form = SiteInfoUpdateForm(request.POST)
        if form.is_valid():
            # form.save(user=request.user, site_info=self._get_site_info(site_id))
            site_info = self._get_site_info(site_id)
            update = form.save(commit=False)
            update.user_updated = request.user
            update.site_id = site_id
            for field in form.fixed_fields():
                setattr(update, field, site_info[field])

            with transaction.atomic():
                self._write_site_info(update, site_id)
                update.save()
            return HttpResponseRedirect(reverse('siteinfo:index'))
        else:
            print('Form not valid')
            context = self._make_context(form, site_id)
            return render(request, 'siteinfo/edit_site_info.html', context=context)

    @staticmethod
    def _get_site_info(site_id):
        all_site_info = InfoFileLocks.read_json_file(settings.SITE_INFO_FILE)
        try:
            return all_site_info[site_id]
        except KeyError:
            raise Http404('No existing site information for site "{}"'.format(site_id))

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
            site_info = self._get_site_info(site_id)

        fixed_fields = SiteInfoUpdateForm.fixed_fields()
        fixed_values = {f: {'value': site_info[f], 'name': self._pretty_name(f)} for f in fixed_fields}
        context = {
            'form': form,
            'fixed_values': fixed_values,
            'long_name': site_info.get('long_name', '??'),
            'site_id': site_id
        }
        return context

    @staticmethod
    def _pretty_name(field):
        field = field.replace('_', ' ').capitalize()
        field = re.sub(r'\b[Dd][Oo][Ii]\b', 'DOI', field)
        return field


class ViewReleaseFlags(View):
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
            meta['n'] = n
            meta['start_date'] = dt.strptime(start_str, '%Y%m%d').date()
            meta['end_date'] = dt.strptime(end_str, '%Y%m%d').date()

            site_flags.append({'info': v, 'meta': meta})

        site_flags.sort(key=lambda el: el['meta']['n'])

        context = {
            'site_id': site_id,
            'long_name': long_name,
            'has_flags': len(site_flags) > 0,
            'flags': site_flags
        }

        return render(request, 'siteinfo/view_release_flags.html', context=context)


def _can_edit_site(user, site_id):
    return user.has_perm('opstat.{}_status'.format(site_id)) or user.is_staff
