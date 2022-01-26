from django.shortcuts import render
from django.views import View

from .forms import QcReportForm


# Create your views here.
class EditQcFormView(View):
    def get(self, request):
        context = {'qcform': QcReportForm()}
        f = context['qcform']
        print(f.sections()[1])
        return render(request, 'qcform/edit_qc_report.html', context=context)