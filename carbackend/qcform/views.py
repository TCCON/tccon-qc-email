from django.shortcuts import render, reverse, Http404, HttpResponse, HttpResponseRedirect, get_object_or_404
from django.contrib.auth.models import User
from django.template import loader
from django.views import View

from. models import QCReport, DraftQcReport
from .forms import QcReportForm, QcFilterForm

from copy import copy
import io
import re
import xhtml2pdf.pisa as pisa

# Next step: see if I can install a small version of latex on tccondata, make a template that can be filled out for it
# and write the PDF downloading view. Also need to add errors to the form. That is the minimum functionality.
# More todos:
#  TODO: allow uploading existing PDF forms and converting
#  TODO: give it some style
#  TODO: make mod times local
#  TODO: direct to logins if needed.

# https://github.com/vincentdoerig/latex-css
#
# HTML to PDF:
# https://github.com/xhtml2pdf/xhtml2pdf
def _string_to_oneline(s, max_length=None):
    s = re.sub('[\r\n]+', ' ', s)
    if max_length is not None and len(s) > max_length:
        return s[:max_length-3] + '...'
    else:
        return s


# Create your views here.
class FormListView(View):
    def get(self, request):
        # The

        if request.user.is_authenticated:
            username = request.user.get_username()
            my_reports = QCReport.objects.filter(reviewer=username)
            other_reports = QCReport.objects.exclude(reviewer=username)
            my_drafts = DraftQcReport.objects.filter(reviewer=username)
        else:
            my_reports = None
            my_drafts = None
            other_reports = QCReport.objects.all()

        user_filter = self._build_filter(request)
        print(user_filter)
        if user_filter:
            other_reports = other_reports.filter(**user_filter)
            if my_reports:
                # don't filter on reviewer for the users' reports
                my_rep_filter = {k: v for k, v in user_filter.items() if 'reviewer' not in k}
                my_reports = my_reports.filter(**my_rep_filter)

        context = {
            'user': request.user,
            'message': request.GET.get('msg', None),
            'is_auth': request.user.is_authenticated,
            'my_reports': self._reports_to_table(my_reports),
            'my_drafts': self._reports_to_table(my_drafts),
            'other_reports': self._reports_to_table(other_reports),
            'filter_form': QcFilterForm(request.GET)
        }

        return render(request, 'qcform/qcform_list.html', context=context)

    def _build_filter(self, request):
        site = request.GET.get('site', '')
        reviewer = request.GET.get('reviewer', '')
        min_date = request.GET.get('modified_after', None)
        max_date = request.GET.get('modified_before', None)

        filter_dict = dict()
        if site:
            filter_dict['site'] = site
        if reviewer:
            filter_dict['reviewer__icontains'] = reviewer
        if min_date:
            min_date = min_date.replace('/', '-') + ' 00:00'
            filter_dict['modification_time__gte'] = min_date
        if max_date:
            max_date = max_date.replace('/', '-') + ' 00:00'
            filter_dict['modification_time__lte'] = max_date

        return filter_dict

    def _reports_to_table(self, reports):
        if reports is None:
            return None

        table_rows = []
        for report in reports:
            if isinstance(report, DraftQcReport):
                draft_id = report.id
                report_id = None if report.report is None else report.report.id
                site = report.draft_data.get('site', '')
                nc_files = report.draft_data.get('netcdf_files', '')
            else:
                draft_id = None
                report_id = report.id
                site = report.site
                nc_files = report.netcdf_files

            table_rows.append({
                'id': report_id,
                'draft_id': draft_id,
                'user': report.reviewer,
                'site': site,
                'nc_files': _string_to_oneline(nc_files, max_length=32),
                'mod_time': report.modification_time.strftime('%Y-%m-%d %H:%M:%S %Z')
            })
        return table_rows


class EditQcFormView(View):
    def get(self, request, form_id=-1):
        if not request.user.is_authenticated:
            # TODO: redirect to log in page
            raise Http404('Must be logged in')

        draft_id = int(request.GET.get('draft_id', -1))
        # There are four possible cases:
        #   1. Wholly new form (not editing existing form or draft)
        #   2. Editing existing draft (that has no corresponding saved form)
        #   3. Editing submitted form, no draft.
        #   4. Editing a draft modification to an existing form.
        if form_id < 0 and draft_id < 0:
            form = QcReportForm(initial={'reviewer': request.user.get_username()})
        elif form_id < 0 and draft_id >= 0:
            data = DraftQcReport.objects.get(id=draft_id).to_dict()
            form = QcReportForm(initial=data)
        elif form_id >= 0 and draft_id < 0:
            report = QCReport.objects.get(id=form_id)
            form = QcReportForm(instance=report)
        else:
            report = QCReport.objects.get(id=form_id)
            draft_data = DraftQcReport.objects.get(id=draft_id).to_dict()
            form = QcReportForm(instance=report, initial=draft_data)

        context = {'qcform': form, 'form_id': form_id, 'draft_id': draft_id, 'has_draft': draft_id >= 0}
        # f = context['qcform']
        # print(f.sections()[1])
        return render(request, 'qcform/edit_qc_report.html', context=context)

    def post(self, request):
        if not request.user.is_authenticated:
            # TODO: redirect to log in page?
            raise Http404('Must be logged in')

        # We store the form id in a hidden input, if it is >0 that means we need to update an existing form
        try:
            form_id = int(request.POST.get('form_id', -1))
        except ValueError:
            # should happen with new forms; no existing ID, so the value is an empty string
            form_id = -1

        try:
            draft_id = int(request.POST.get('draft_id', -1))
        except ValueError:
            draft_id = -1

        if form_id > 0:
            existing_report = QCReport.objects.get(id=form_id)
        else:
            existing_report = None
        form = QcReportForm(request.POST, instance=existing_report)

        if form.is_valid():
            if form.cleaned_data['reviewer'] != request.user.get_username():
                # Just a little precaution in case someone tries to mess with their POST data
                raise ValueError('Form reviewer does not match username')

            form.save()

            # Once the form saved successfully, it's safe to delete the draft we were editing,
            # assuming one existed.
            if draft_id >= 0:
                draft = DraftQcReport.objects.get(id=draft_id)
                if not draft.reviewer == request.user.get_username():
                    raise ValueError('Draft reviewer does not match username')

                draft.delete()

            url = '{}/?msg=success'.format(reverse('qcform:index').rstrip('?').rstrip('/'))
            return HttpResponseRedirect(url)
        else:
            return render(request, 'qcform/edit_qc_report.html', context={'qcform': form, 'form_id': form_id})


class SaveDraftQcFormView(View):
    def get(self, request):
        raise Http404('Wrong request type!')

    def post(self, request):
        new_draft = DraftQcReport.from_post(request)
        new_draft.save()
        url = '{}/?msg=draft-success'.format(reverse('qcform:index').rstrip('?').rstrip('/'))
        return HttpResponseRedirect(url)


class DeleteQcForm(View):
    def post(self, request, form_id):
        if not request.user.is_authenticated:
            raise Http404('Must be logged in')

        report = QCReport.objects.get(id=form_id)
        if not report.reviewer == request.user.get_username():
            raise ValueError('Form reviewer does not match username')

        report.delete()

        url = '{}/?msg=deleted'.format(reverse('qcform:index').rstrip('?').rstrip('/'))
        return HttpResponseRedirect(url)


class DeleteDraft(View):
    def post(self, request, draft_id):
        if not request.user.is_authenticated:
            raise Http404('Must be logged in')

        draft = DraftQcReport.objects.get(id=draft_id)
        if not draft.reviewer == request.user.get_username():
            raise ValueError('Draft reviewer does not match username')

        draft.delete()

        url = '{}/?msg=deleted-draft'.format(reverse('qcform:index').rstrip('?').rstrip('/'))
        return HttpResponseRedirect(url)


class RenderPdfForm(View):
    def get(self, request, form_id):
        report = get_object_or_404(QCReport, id=form_id)

        try:
            reviewer = User.objects.get(username=report.reviewer)
        except User.DoesNotExist:
            reviewer_full_name = ''
        else:
            if reviewer.first_name or reviewer.last_name:
                reviewer_full_name = f'{reviewer.first_name} {reviewer.last_name}'
            else:
                reviewer_full_name = ''

        context = {
            'report': report,
            'site': report.get_site_display(),
            'reviewer_full_name': reviewer_full_name,
            'reviewer_user_name': report.reviewer,
            'brief': True
        }

        template = loader.get_template('qcform/qc_pdf_form.html')
        html = template.render(context, request)
        pdf = io.BytesIO(b'')
        pisa.CreatePDF(io.StringIO(html), pdf)
        pdf.seek(0)

        # return render(request, 'qcform/qc_pdf_form.html', context=context)
        return HttpResponse(pdf, content_type='application/pdf')
