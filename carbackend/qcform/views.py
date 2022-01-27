from django.shortcuts import render, Http404, HttpResponse
from django.views import View

from. models import QCReport
from .forms import QcReportForm

import re

# Next step: see if I can install a small version of latex on tccondata, make a template that can be filled out for it
# and write the PDF downloading view. That is the minimum functionality. More todos:
#  TODO: allow deleting forms
#  TODO: allow uploading existing PDF forms and converting
#  TODO: validate that at least one date is provided when needed
#  TODO: give it some style
#  TODO: direct to logins if needed.

def _string_to_oneline(s, max_length=None):
    s = re.sub('\r?\n?', ' ', s)
    if max_length is not None and len(s) > max_length:
        return s[:max_length-3] + '...'
    else:
        return s


# Create your views here.
class FormListView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            # TODO: redirect to log in page
            raise Http404('Must be logged in')

        my_reports = QCReport.objects.filter(reviewer=request.user.get_username())
        table_rows = []
        for report in my_reports:
            table_rows.append({
                'id': report.id,
                'site': report.site,
                'nc_files': _string_to_oneline(report.netcdf_files, max_length=32)
            })

        return render(request, 'qcform/qcform_list.html', context={'form_table': table_rows})


class EditQcFormView(View):
    def get(self, request, form_id=-1):
        print('form_id =', form_id)
        if not request.user.is_authenticated:
            # TODO: redirect to log in page
            raise Http404('Must be logged in')
        if form_id < 0:
            form = QcReportForm(initial={'reviewer': request.user.get_username()})
        else:
            report = QCReport.objects.get(id=form_id)
            form = QcReportForm(instance=report)
        context = {'qcform': form, 'form_id': form_id}
        # f = context['qcform']
        # print(f.sections()[1])
        return render(request, 'qcform/edit_qc_report.html', context=context)

    def post(self, request):
        if not request.user.is_authenticated:
            # TODO: redirect to log in page?
            raise Http404('Must be logged in')

        # We store the form id in a hidden input, if it is >0 that means we need to update an existing form
        form_id = int(request.POST.get('form_id', -1))
        if form_id > 0:
            existing_report = QCReport.objects.get(id=form_id)
        else:
            existing_report = None
        form = QcReportForm(request.POST, instance=existing_report)

        if form.is_valid():
            form.save()
            return HttpResponse('Success!'.encode('utf8'), content_type='text/plain')
        else:
            print(form.errors)
            return render(request, 'qcform/edit_qc_report.html', context={'qcform': form})