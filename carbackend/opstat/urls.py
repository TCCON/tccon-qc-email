from django.urls import path
from . import views

app_name = 'opstat'
urlpatterns = [
    path('', views.index, name='index'),
    path('car', views.car, name='car'),
    path('update/<str:site_id>', views.update, name='update'),
    path('submitupdate/<str:site_id>', views.submitupdate, name='submitupdate'),
]