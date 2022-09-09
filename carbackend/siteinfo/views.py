from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.views import View
from django.shortcuts import render, reverse, HttpResponseRedirect

from datetime import datetime as dt
import json
from pathlib import Path
import re

from .forms import SiteInfoUpdateForm, SiteInfoUpdateStaffForm, ReleaseFlagUpdateForm
from .models import SiteInfoUpdate, InfoFileLocks
from . import utils, forms


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


class MissingPermission(View):
    def get(self, request):
        msg = request.GET.get('msg', None)
        site_id = request.GET.get('site', '??')
        what = request.GET.get('what', 'that')

        if msg == 'lackperm':
            msg = 'You do not have permissions to edit {what} for site {site}.'
        elif msg == 'notloggedin':
            msg = 'You need to be logged in to edit {what}.'
        elif msg == 'getnotallowed':
            msg = 'You tried to directly visit a URL only used to update {what} - this does nothing. You must use the correct form on this website.'
        else:
            msg = 'You are not allowed to edit {what} for site {site}.'

        msg = msg.format(what=what, site=site_id)
        context = {
            'msg': msg,
            'is_logged_in': request.user.is_authenticated
        }
        return render(request, 'siteinfo/missing_permission.html', context=context)


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

        metadata_json_file = _site_metadata_file(site_id, site_info['long_name'])
        metadata_info = InfoFileLocks.read_metadata_file(metadata_json_file)

        msg_key = request.GET.get('msg', None)
        msg = self._top_messages.get(msg_key, '')

        context = {
            'site_id': site_id,
            'is_auth': request.user.is_authenticated,
            'info': site_info,
            'doi_tables': self._metadata_to_tables(metadata_info),
            'can_edit': _can_edit_site(request.user, site_id),
            'msg': msg
        }

        return render(request, 'siteinfo/view_site_info.html', context=context)

    @classmethod
    def _metadata_to_tables(cls, metadata_info):
        formset_classes = {
            'Site location': forms.SiteDoiForm,
            'Creators': forms.CreatorFormset,
            'Contributors': forms.ContributorFormset,
            'Related identifiers': forms.RelatedIdFormset,
            'Funding references': forms.FundingReferenceFormset
        }

        tables = dict()
        for key, klass in formset_classes.items():
            if len(metadata_info) == 0:
                tables[key] = None
                continue

            if key == 'Site location':
                loc_info = forms.SiteDoiForm.json_to_dict(metadata_info)
                info_list = [loc_info] if len(loc_info) > 0 else []
            else:
                info_list = klass.cite_schema_to_list(metadata_info)

            if len(info_list) == 0:
                tables[key] = None
                continue

            columns = list(info_list[0].keys())
            table = [[row.get(c, '') for c in columns] for row in info_list]
            tables[key] = {'columns': [cls._pretty_column_name(c, klass) for c in columns], 'table': table}

        return tables

    @staticmethod
    def _pretty_column_name(colname, formset_class):
        colname = colname.replace('_', ' ').capitalize()
        colname = formset_class.prettify_column_name(colname)
        return colname


class EditSiteInfo(View):
    # TODOs:
    #   - Replace the Http404 error below with a redirect to a "You don't have that permission" page
    #   - Might also be nice if going back to main without saving put a message "Changes not saved" at the top
    def get(self, request, site_id):
        user = request.user
        if not _can_edit_site(user, site_id):
            return _redirect_for_lack_of_permission(request, site_id, 'public metadata')

        site_info = _get_site_info(site_id)
        netcdf_form = self._get_netcdf_form(user, site_id)
        site_doi_form = self._get_site_doi_form(user, site_id)
        # These will be put into context as {key}_formset
        doi_formsets = self._make_doi_formset_dict(request, site_id)

        # import pdb; pdb.set_trace()

        context = self._make_context(
            user=user,
            is_post=False,
            netcdf_form=netcdf_form,
            site_doi_form=site_doi_form,
            doi_formsets=doi_formsets,
            site_id=site_id,
            site_info=site_info,
        )
        return render(request, 'siteinfo/edit_site_info.html', context=context)

    def post(self, request, site_id):
        # TODO: confirm before deleting a filled form (JS)?
        if not _can_edit_site(request.user, site_id):
            return _redirect_for_lack_of_permission(request, site_id, 'public metadata')

        netcdf_form = self._get_netcdf_form(request.user, site_id, post_data=request.POST)
        site_doi_form = self._get_site_doi_form(request.user, site_id, post_data=request.POST)
        doi_formsets = self._make_doi_formset_dict(request, site_id, with_post=True)

        # Only submit changes if all the various forms are valid
        # import pdb; pdb.set_trace()
        if netcdf_form.is_valid() and site_doi_form.is_valid() and all(fs.is_valid() for fs in doi_formsets.values()):
            updated_site_info = self._save_netcdf_metadata(request, netcdf_form, site_id)
            self._save_doi_metadata(request, updated_site_info, site_doi_form, doi_formsets, site_id)
            url = '{}/?msg=success'.format(reverse('siteinfo:view', args=(site_id,)).rstrip('?').rstrip('/'))
            return HttpResponseRedirect(url)
        else:
            context = self._make_context(
                user=request.user,
                is_post=True,
                netcdf_form=netcdf_form,
                site_doi_form=site_doi_form,
                doi_formsets=doi_formsets,
                site_id=site_id
            )
            return render(request, 'siteinfo/edit_site_info.html', context=context)

    def _save_netcdf_metadata(self, request, form, site_id):
        # form.save(user=request.user, site_info=self._get_site_info(site_id))
        site_info = _get_site_info(site_id)
        update = form.save(commit=False)
        update.user_updated = request.user
        update.site_id = site_id
        for field in form.fixed_fields():
            setattr(update, field, site_info[field])

        with transaction.atomic():
            self._write_site_info(update, site_id)
            update.save()  # UNDO

        return update

    @classmethod
    def _save_doi_metadata(cls, request, site_nc_info, site_doi_form, doi_formsets, site_id):
        # TODO: add in derived or static metadata
        doi_metadata = {k: v.to_list() for k, v in doi_formsets.items()}
        site_doi_form.add_form_to_json(doi_metadata, site_nc_info.data_revision)

        # This avoids a Git error from trying to commit with no changes - happens if the user
        # submits the existing data.
        doi_metadata['__last_modified__'] = f'{timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")} by {request.user}'
        metadata_json_file = _site_metadata_file(site_id, site_nc_info.long_name)
        InfoFileLocks.update_metadata_repo(metadata_json_file, doi_metadata, request.user)

    @staticmethod
    def _get_netcdf_form(user, site_id, post_data=None):
        if post_data is None:
            site_info = _get_site_info(site_id)
            if _can_edit_all_site_info(user, site_id):
                return SiteInfoUpdateStaffForm(initial=site_info)
            elif _can_edit_site(user, site_id):
                return SiteInfoUpdateForm(initial=site_info)
            else:
                raise Http404('Sorry, you cannot access the information form for site "{}"'.format(site_id))
        else:
            if _can_edit_all_site_info(user, site_id):
                return SiteInfoUpdateStaffForm(post_data)
            elif _can_edit_site(user, site_id):
                return SiteInfoUpdateForm(post_data)
            else:
                raise Http404('Sorry, you cannot access the information form for site "{}"'.format(site_id))

    @staticmethod
    def _get_site_doi_form(user, site_id, post_data=None):
        if _can_edit_site(user, site_id):
            if post_data is not None:
                return forms.SiteDoiForm(post_data)

            metadata_file = _site_metadata_file(site_id)
            doi_metadata = InfoFileLocks.read_metadata_file(metadata_file)
            if doi_metadata:
                return forms.SiteDoiForm.get_form_from_json(doi_metadata)
            else:
                return forms.SiteDoiForm()
        else:
            raise Http404('Sorry you cannot access the information form for site "{}"'.format(site_id))

    @classmethod
    def _make_doi_formset_dict(cls, request, site_id, with_post=False):
        if with_post:
            post_data = request.POST
        else:
            post_data = None

        doi_formsets = {
            forms.CreatorFormset.cls_key: cls._get_doi_formset(request.user, site_id, forms.CreatorFormset, post_data=post_data),
            forms.ContributorFormset.cls_key: cls._get_doi_formset(request.user, site_id, forms.ContributorFormset, post_data=post_data),
            forms.RelatedIdFormset.cls_key: cls._get_doi_formset(request.user, site_id, forms.RelatedIdFormset, post_data=post_data),
            forms.FundingReferenceFormset.cls_key: cls._get_doi_formset(request.user, site_id, forms.FundingReferenceFormset, post_data=post_data)
        }

        return doi_formsets

    @classmethod
    def _get_doi_formset(cls, user, site_id, formset_cls, post_data=None):
        if not _can_edit_all_site_info(user, site_id) and not _can_edit_site(user, site_id):
            raise Http404('Sorry, you cannot access the information form for site "{}"'.format(site_id))

        metadata_file = _site_metadata_file(site_id)
        try:
            cite_schema = InfoFileLocks.read_metadata_file(metadata_file)
        except FileNotFoundError:
            creators_list = None
        else:
            creators_list = formset_cls.cite_schema_to_list(cite_schema)

        if post_data is None:
            return formset_cls(initial=creators_list)
        else:
            return formset_cls(post_data, initial=creators_list)

    @staticmethod
    def _write_site_info(update, site_id):
        all_site_info = InfoFileLocks.read_json_file(settings.SITE_INFO_FILE)
        site_info = all_site_info.setdefault(site_id, dict())
        for key in SiteInfoUpdate.standard_fields():
            site_info[key] = str(getattr(update, key))

        utils.backup_file_rolling(settings.SITE_INFO_FILE)
        InfoFileLocks.write_json_file(settings.SITE_INFO_FILE, all_site_info, indent=4)

    def _make_context(self, user, is_post, netcdf_form, site_doi_form, doi_formsets, site_id, site_info=None, ror_list=None):
        if site_info is None:
            site_info = _get_site_info(site_id)

        if ror_list is None:
            ror_list = self._make_ror_list()

        fixed_fields = netcdf_form.fixed_fields()
        fixed_values = {f: {'value': site_info[f], 'name': self._pretty_name(f)} for f in fixed_fields}
        std_fixed_fields = SiteInfoUpdateForm.fixed_fields()

        if is_post:
            nc_invalid = not netcdf_form.is_valid()
            sd_invalid = not site_doi_form.is_valid()
            fs_invalid = not all(fs.is_valid() for fs in doi_formsets.values())
        else:
            nc_invalid = False
            sd_invalid = False
            fs_invalid = False

        context = {
            'netcdf_form': netcdf_form,
            'site_doi_form': site_doi_form,
            'fixed_values': fixed_values,
            'std_fixed_fields': {'n': len(std_fixed_fields), 'fields': _grammatical_join(std_fixed_fields)},
            'long_name': site_info.get('long_name', '??'),
            'site_id': site_id,
            'contact': utils.get_contact(),
            'can_edit_all': _can_edit_all_site_info(user, site_id),
            'forms_invalid': {'any': nc_invalid or sd_invalid or fs_invalid, 'common': nc_invalid, 'doi': sd_invalid or fs_invalid},
            'common_ror_list': ror_list
        }

        # Add all the extra DOI formsets directly into the context dictionary
        for key, formset in doi_formsets.items():
            context[f'{key}_formset'] = formset
        return context

    def _make_ror_list(self):
        ror_file = Path(__file__).parent / 'ror_id_list.txt'
        ror_list = []
        with open(ror_file) as f:
            for line in f:
                if line.startswith('#'):
                    continue

                affil, aid = line.split(':', maxsplit=1)
                ror_list.append((affil, aid))

        return ror_list

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

            plot = v.get('plot', None)  # handle either missing or null plot
            meta = dict()
            meta['n'] = int(n)
            meta['n_str'] = str(meta['n'])
            meta['start_date'] = dt.strptime(start_str, '%Y%m%d').date()
            meta['end_date'] = dt.strptime(end_str, '%Y%m%d').date()
            meta['plot_path'] = settings.FLAG_PLOT_URL + plot if plot is not None else None

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
            'can_edit_flags': request.user.is_staff,
            'contact': utils.get_contact()
        }

        return render(request, 'siteinfo/view_release_flags.html', context=context)


class DeleteReleaseFlags(View):
    def get(self, request, site_id, flag_id):
        return _redirect_for_lack_of_permission(request, site_id, 'release flags', 'getnotallowed')

    def post(self, request, site_id, flag_id):
        if not _can_edit_site_flags(request.user, site_id):
            return _redirect_for_lack_of_permission(request, site_id, 'release flags')

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
        if not _can_edit_site_flags(request.user, site_id):
            return _redirect_for_lack_of_permission(request, site_id, 'release flags')

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
        if not _can_edit_site_flags(request.user, site_id):
            return _redirect_for_lack_of_permission(request, site_id)

        form = ReleaseFlagUpdateForm(request.POST, request.FILES)
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


class EditBibtexCitation(View):
    _citation_names = {'siteref': 'site reference', 'dataref': 'data reference'}

    def get(self, request, site_id, citation):
        user = request.user
        if not _can_edit_site(user, site_id):
            return _redirect_for_lack_of_permission(request, site_id, f'{citation} bibtex')

        context = {
            'site_id': site_id,
            'citation': citation,
            'citation_name': self._citation_names.get(citation, citation),
            'form_types': forms.BibtexFormMixin.get_form_instances_as_bibtex_type_dict(),
            'form_type_mapping': forms.BibtexFormMixin.get_bibtex_dropdown_dict()
        }

        print(context['form_types'].keys())

        return render(request, 'siteinfo/edit_bibtex.html', context=context)


def _can_edit_site(user, site_id):
    return user.has_perm('opstat.{}_status'.format(site_id)) or user.is_staff


def _can_edit_all_site_info(user, site_id):
    return user.is_staff


def _can_edit_site_flags(user, site_id):
    return user.is_staff


def _get_site_info(site_id):
    all_site_info = InfoFileLocks.read_json_file(settings.SITE_INFO_FILE)
    try:
        return all_site_info[site_id]
    except KeyError:
        raise Http404('No existing site information for site "{}"'.format(site_id))


def _site_metadata_file(site_id, site_long_name=None):
    if site_long_name is None:
        site_info = _get_site_info(site_id)
        site_long_name = site_info['long_name']

    return f'{site_id}_{site_long_name}.json'


def _find_flag_key(site_id, flag_id, flag_dict):
    key_regex = re.compile(r'{}_0*{}'.format(site_id, int(flag_id)))
    for key in flag_dict:
        if key_regex.match(key):
            return key

    raise Http404('Unable to find flag for site "{}" flag number "{}"'.format(site_id, flag_id))


def _redirect_for_lack_of_permission(request, site_id, what, why='permission'):
    base_url = reverse('siteinfo:missingperm').rstrip('?').rstrip('/')
    if why == 'permission':
        reason = 'lacksperm' if request.user.is_authenticated else 'notloggedin'
    else:
        reason = why
    url = '{}/?msg={}&site={}&what={}'.format(base_url, reason, site_id, what)
    return HttpResponseRedirect(url)


def _grammatical_join(seq, conjunction='and'):
    if len(seq) == 1:
        return seq[0]
    elif len(seq) == 2:
        return '{} {} {}'.format(seq[0], conjunction, seq[1])
    else:
        s = ', '.join(seq[:-1])
        return '{}, {} {}'.format(s, conjunction, seq[-1])
