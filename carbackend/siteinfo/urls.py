from django.urls import path
from . import views

app_name = 'siteinfo'
urlpatterns = [
    path('', views.SiteInfoList.as_view(), name='index'),
    path('view/<str:site_id>/', views.ViewSiteInfo.as_view(), name='view'),
    path('edit/<str:site_id>/', views.EditSiteInfo.as_view(), name='edit'),
    path('flags/<str:site_id>/', views.ViewReleaseFlags.as_view(), name='flags'),
    path('editflags/<str:site_id>/<str:flag_id>/', views.EditReleaseFlags.as_view(), name='editflags')
]