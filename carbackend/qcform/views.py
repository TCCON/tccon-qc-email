from django.shortcuts import render, Http404, HttpResponse, get_object_or_404
from django.template import loader
from django.views import View

from. models import QCReport
from .forms import QcReportForm

import io
import re
import xhtml2pdf.pisa as pisa

# Next step: see if I can install a small version of latex on tccondata, make a template that can be filled out for it
# and write the PDF downloading view. Also need to add errors to the form. That is the minimum functionality.
# More todos:
#  TODO: allow deleting forms
#  TODO: allow uploading existing PDF forms and converting
#  TODO: validate that at least one date is provided when needed
#  TODO: give it some style
#  TODO: direct to logins if needed.

# https://github.com/vincentdoerig/latex-css
#
# HTML to PDF:
# https://github.com/xhtml2pdf/xhtml2pdf
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


class RenderPdfForm(View):
    def get(self, request, form_id):
        report = get_object_or_404(QCReport, id=form_id)

        if request.user.first_name or request.user.last_name:
            reviewer_full_name = f'{request.user.first_name} {request.user.last_name}'
        else:
            reviewer_full_name = ''

        context = {
            'report': report,
            'site': report.get_site_display(),
            'reviewer_full_name': reviewer_full_name,
            'reviewer_user_name': request.user.get_username(),
            'brief': True
        }

        # This doesn't produce
        template = loader.get_template('qcform/qc_pdf_form.html')
        html = template.render(context, request)
        pdf = io.BytesIO(b'')
        pisa.CreatePDF(io.StringIO(html), pdf)
        pdf.seek(0)

        # return render(request, 'qcform/qc_pdf_form.html', context=context)
        return HttpResponse(pdf, content_type='application/pdf')
