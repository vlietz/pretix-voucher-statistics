from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event, nav_organizer


@receiver(nav_event, dispatch_uid='voucher_statistics_nav_event')
def nav_event_receiver(sender, request=None, **kwargs):
    if not request.user.has_event_permission(
        request.organizer, request.event, 'can_view_vouchers', request
    ):
        return []

    url = reverse(
        'plugins:pretix_voucher_statistics:voucher-list',
        kwargs={
            'organizer': request.event.organizer.slug,
            'event': request.event.slug,
        },
    )
    return [
        {
            'label': _('Voucher Statistics'),
            'url': url,
            'active': 'pretix_voucher_statistics' in request.resolver_match.namespaces,
            'icon': 'bar-chart',
            'parent': reverse(
                'control:event.vouchers',
                kwargs={
                    'organizer': request.event.organizer.slug,
                    'event': request.event.slug,
                },
            ),
        }
    ]


@receiver(nav_organizer, dispatch_uid='voucher_statistics_nav_organizer')
def nav_organizer_receiver(sender, request=None, **kwargs):
    if not request.user.has_organizer_permission(
        request.organizer, 'can_change_organizer_settings', request
    ):
        return []

    url = reverse(
        'plugins:pretix_voucher_statistics:org-statistics',
        kwargs={'organizer': request.organizer.slug},
    )
    return [
        {
            'label': _('Voucher Statistics'),
            'url': url,
            'active': 'pretix_voucher_statistics' in request.resolver_match.namespaces,
            'icon': 'bar-chart',
        }
    ]
