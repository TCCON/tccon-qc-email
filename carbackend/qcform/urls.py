from django.urls import path
from . import views

app_name = 'qcform'
urlpatterns = [
    path('', views.FormListView.as_view(), name='index'),
    path('edit/', views.EditQcFormView.as_view(), name='edit'),
    path('edit/<int:form_id>/', views.EditQcFormView.as_view(), name='edit'),
    path('savedraft/', views.SaveDraftQcFormView.as_view(), name='savedraft'),
    path('delete/<int:form_id>/', views.DeleteQcForm.as_view(), name='delete'),
    path('deletedraft/<int:draft_id>/', views.DeleteDraft.as_view(), name='deletedraft'),
    path('makepdf/<int:form_id>/', views.RenderPdfForm.as_view(), name='pdf'),
    path('reviewers/', views.ViewEditorsReviewers.as_view(), name='reviewers'),
    path('setreviewers/', views.SetEditorsReviewers.as_view(), name='setreviewers')
]