from django.urls import path
from . import views

app_name = 'qcform'
urlpatterns = [
    # path('', views.SiteInfoList.as_view(), name='index'),
    path('edit/', views.EditQcFormView.as_view(), name='edit'),
]