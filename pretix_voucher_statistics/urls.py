from django.urls import path

from . import views

# Mounted under /control/event/{organizer}/{event}/
event_patterns = [
    path('voucher-stats/', views.VoucherStatisticsListView.as_view(), name='voucher-list'),
    path('voucher-stats/<int:pk>/', views.VoucherDetailView.as_view(), name='voucher-detail'),
    path('voucher-stats/<int:pk>/data/timeline/', views.VoucherTimelineDataView.as_view(), name='voucher-timeline-data'),
    path('voucher-stats/<int:pk>/data/comparison/', views.VoucherComparisonDataView.as_view(), name='voucher-comparison-data'),
]

# Mounted under /control/organizer/{organizer}/
organizer_patterns = [
    path('voucher-stats/', views.OrgStatisticsView.as_view(), name='org-statistics'),
    path('voucher-stats/data/', views.OrgStatisticsDataView.as_view(), name='org-statistics-data'),
]
