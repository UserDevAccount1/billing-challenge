from django.urls import path
from . import views

urlpatterns = [
    path('account/', views.get_account, name='get_account'),
    path('deliver/', views.deliver_adjustment, name='deliver_adjustment'),
    path('run/', views.issue_run, name='issue_run'),
    path('adopt/', views.adopt_summaries, name='adopt_summaries'),
    path('statement/<str:period_key>/', views.get_statement, name='get_statement'),
    path('reset/', views.reset_account, name='reset_account'),
]
