from django.urls import path

from . import views

# Using urlpatterns (not event_patterns / organizer_patterns) so these are
# registered at the root level under the control panel paths.
# event_patterns / organizer_patterns are shop-frontend URLs and go through
# the "shop offline" middleware, which blocks access to deactivated events.
urlpatterns = [
    # Event-level views
    path('control/event/<str:organizer>/<str:event>/voucher-stats/',
         views.VoucherStatisticsListView.as_view(), name='voucher-list'),
    path('control/event/<str:organizer>/<str:event>/voucher-stats/<int:pk>/',
         views.VoucherDetailView.as_view(), name='voucher-detail'),
    path('control/event/<str:organizer>/<str:event>/voucher-stats/<int:pk>/data/timeline/',
         views.VoucherTimelineDataView.as_view(), name='voucher-timeline-data'),
    path('control/event/<str:organizer>/<str:event>/voucher-stats/<int:pk>/data/comparison/',
         views.VoucherComparisonDataView.as_view(), name='voucher-comparison-data'),
    path('control/event/<str:organizer>/<str:event>/voucher-stats/<int:pk>/data/rampup/',
         views.VoucherRampupDataView.as_view(), name='voucher-rampup-data'),

    # Organizer-level views
    path('control/organizer/<str:organizer>/voucher-stats/',
         views.OrgStatisticsView.as_view(), name='org-statistics'),
    path('control/organizer/<str:organizer>/voucher-stats/data/',
         views.OrgStatisticsDataView.as_view(), name='org-statistics-data'),
]
