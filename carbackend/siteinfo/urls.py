from django.urls import path
from . import views

app_name = 'siteinfo'
urlpatterns = [
    path('', views.SiteInfoList.as_view(), name='index'),
    path('view/<str:site_id>/', views.ViewSiteInfo.as_view(), name='view'),
]