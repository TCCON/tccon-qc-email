from django.conf import settings
from django.http import Http404
from django.views import View
from django.shortcuts import render

import json


class SiteInfoList(View):
    def get(self, request):
        with open(settings.SITE_INFO_FILE) as f:
            all_site_info = json.load(f)

        sites = [{'id': k, 'name': v['long_name']} for k, v in all_site_info.items()]
        sites.sort(key=lambda s: s['id'])
        # TODO: limit which sites have the "edit" link active based on user permissions
        return render(request, 'siteinfo/site_list.html', context={'sites': sites})


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
