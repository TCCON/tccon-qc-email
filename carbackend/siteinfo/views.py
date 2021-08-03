from django.conf import settings
from django.http import Http404
from django.views import View
from django.shortcuts import render

import json
import re


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

        # TODO: ensure that the standard attributes are in a fixed order
        return render(request, 'siteinfo/view_site_info.html', context={'site_id': site_id, 'info': site_info})
