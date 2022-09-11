from django.urls import path
from . import views

app_name = 'siteinfo'
urlpatterns = [
    path('', views.SiteInfoList.as_view(), name='index'),
    path('view/<str:site_id>/', views.ViewSiteInfo.as_view(), name='view'),
    path('edit/<str:site_id>/', views.EditSiteInfo.as_view(), name='edit'),
    path('flags/<str:site_id>/', views.ViewReleaseFlags.as_view(), name='flags'),
    path('editflags/<str:site_id>/<str:flag_id>/', views.EditReleaseFlags.as_view(), name='editflags'),
    path('deleteflags/<str:site_id>/<str:flag_id>/', views.DeleteReleaseFlags.as_view(), name='deleteflags'),
    path('editbib/<str:site_id>/<str:citation>/', views.EditBibtexCitation.as_view(), name='editbib'),
    path('genbib/', views.GenLatex.as_view(), name='gentex'),
    path('bibgenerator/', views.GenBibtex.as_view(), name='bibgenerator'),
    path('tablegenerator/', views.GenLatexTable.as_view(), name='tablegenerator'),
    path('textcitation/', views.GenTextCitation.as_view(), name='textcite'),
    path('permission/', views.MissingPermission.as_view(), name='missingperm')
]