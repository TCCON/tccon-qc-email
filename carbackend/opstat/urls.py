from django.urls import path
from . import views

app_name = 'opstat'
urlpatterns = [
    path('', views.index, name='index'),
    path('car', views.car, name='car'),
    path('update/<str:site_id>', views.update, name='update'),
    path('submitupdate/<str:site_id>', views.submitupdate, name='submitupdate'),
    path('history/<str:site_id>', views.history, name='history'),
    path('all_history', views.all_site_history, name='all_history'),
    path('api_docs', views.api_docs, name='api_docs'),
    path('api/getstatusall/byid', views.api_get_all_statuses_by_id, name='api-all-byid'),
    path('api/getstatusall/byname', views.api_get_all_statuses_by_name, name='api-all-byname'),
    path('api/getstatus/byid/<str:site_id>', views.api_get_status_by_id, name='api-one-byid'),
    path('api/getstatus/byname/<str:name>', views.api_get_status_by_name, name='api-one-byname')
]