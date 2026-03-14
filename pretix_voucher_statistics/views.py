import json
from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from pretix.base.models import Event, Order, OrderPosition, Voucher

ACTIVE_STATUSES = [Order.STATUS_PAID, Order.STATUS_PENDING]


# ---------------------------------------------------------------------------
# Permission mixins
# ---------------------------------------------------------------------------

class EventVoucherViewMixin:
    """Requires the user to have can_view_vouchers for the current event."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('control:auth.login') + '?next=' + request.get_full_path())
        if not hasattr(request, 'event'):
            raise Http404
        if not request.user.has_event_permission(
            request.organizer, request.event, 'can_view_vouchers', request
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class OrganizerAdminMixin:
    """Requires the user to have can_change_organizer_settings for the organizer."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('control:auth.login') + '?next=' + request.get_full_path())
        if not hasattr(request, 'organizer'):
            raise Http404
        if not request.user.has_organizer_permission(
            request.organizer, 'can_change_organizer_settings', request
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _positions_qs(event=None, voucher=None):
    """Base queryset for active order positions."""
    qs = OrderPosition.objects.filter(order__status__in=ACTIVE_STATUSES)
    if event is not None:
        qs = qs.filter(order__event=event)
    if voucher is not None:
        qs = qs.filter(voucher=voucher)
    return qs


def _timeline_data(positions_qs):
    """Return daily + cumulative ticket counts from a positions queryset."""
    by_date = (
        positions_qs
        .annotate(date=TruncDate('order__datetime'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    labels = []
    daily = []
    cumulative = []
    total = 0
    for row in by_date:
        labels.append(row['date'].isoformat())
        daily.append(row['count'])
        total += row['count']
        cumulative.append(total)
    return {'labels': labels, 'daily': daily, 'cumulative': cumulative}


def _get_attendee_name(position):
    parts = position.attendee_name_parts or {}
    if parts:
        return ' '.join(filter(None, [parts.get('given_name', ''), parts.get('family_name', '')])) or parts.get('_legacy', '')
    return position.attendee_name or ''


def _get_invoice_address(order):
    try:
        return order.invoice_address
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Voucher list view  (event level)
# ---------------------------------------------------------------------------

class VoucherStatisticsListView(EventVoucherViewMixin, TemplateView):
    template_name = 'pretix_voucher_statistics/voucher_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.request.event

        sort = self.request.GET.get('sort', 'ticket_count')
        direction = self.request.GET.get('dir', 'desc')

        allowed_sorts = {
            'code': 'code',
            'tag': 'tag',
            'ticket_count': 'ticket_count',
        }
        sort_field = allowed_sorts.get(sort, 'ticket_count')
        order_expr = f'-{sort_field}' if direction == 'desc' else sort_field

        vouchers = (
            Voucher.objects.filter(event=event)
            .annotate(
                ticket_count=Count(
                    'orderposition',
                    filter=Q(orderposition__order__status__in=ACTIVE_STATUSES),
                )
            )
            .order_by(order_expr, 'code')
        )

        ctx['vouchers'] = vouchers
        ctx['sort'] = sort
        ctx['direction'] = direction
        ctx['event'] = event
        return ctx


# ---------------------------------------------------------------------------
# Voucher detail view  (event level)
# ---------------------------------------------------------------------------

class ChartCSPMixin:
    """Allow Chart.js to apply inline styles (it sets style= on canvas elements)."""

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response['Content-Security-Policy'] = "style-src 'unsafe-inline'"
        return response


class VoucherDetailView(EventVoucherViewMixin, ChartCSPMixin, TemplateView):
    template_name = 'pretix_voucher_statistics/voucher_detail.html'

    def get_voucher(self):
        return get_object_or_404(
            Voucher, pk=self.kwargs['pk'], event=self.request.event
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        voucher = self.get_voucher()
        event = self.request.event

        # --- Sorting for the orders table ---
        sort = self.request.GET.get('sort', 'order__datetime')
        direction = self.request.GET.get('dir', 'asc')

        allowed_sorts = {
            'order_code': 'order__code',
            'order_datetime': 'order__datetime',
            'customer_email': 'order__email',
            'attendee_name': 'attendee_name_cached',
            'attendee_email': 'attendee_email',
            'item': 'item__name',
        }
        sort_field = allowed_sorts.get(sort, 'order__datetime')
        order_expr = f'-{sort_field}' if direction == 'desc' else sort_field

        positions = (
            _positions_qs(event=event, voucher=voucher)
            .select_related('order', 'item', 'variation')
            .order_by(order_expr, 'pk')
        )

        # Build row data including invoice address (one extra query per page is
        # avoided by fetching all invoice addresses for visible orders at once)
        page_number = self.request.GET.get('page', 1)
        paginator = Paginator(positions, 50)
        page_obj = paginator.get_page(page_number)

        # Pre-fetch invoice addresses for this page's orders
        order_pks = {pos.order_id for pos in page_obj}
        from pretix.base.models import InvoiceAddress
        addr_map = {
            ia.order_id: ia
            for ia in InvoiceAddress.objects.filter(order_id__in=order_pks)
        }

        rows = []
        for pos in page_obj:
            addr = addr_map.get(pos.order_id)
            addr_name = ''
            if addr:
                parts = addr.name_parts or {}
                addr_name = (
                    ' '.join(filter(None, [parts.get('given_name', ''), parts.get('family_name', '')]))
                    or parts.get('_legacy', '')
                    or addr.company
                )

            rows.append({
                'position': pos,
                'order': pos.order,
                'attendee_name': _get_attendee_name(pos),
                'item_name': str(pos.item.name) if pos.item else '',
                'variation_name': str(pos.variation.value) if pos.variation else '',
                'addr': addr,
                'addr_name': addr_name,
            })

        # Summary stats
        total_tickets = _positions_qs(event=event, voucher=voucher).count()

        ctx.update({
            'voucher': voucher,
            'event': event,
            'rows': rows,
            'page_obj': page_obj,
            'paginator': paginator,
            'total_tickets': total_tickets,
            'sort': sort,
            'direction': direction,
            'active_tab': self.request.GET.get('tab', 'orders'),
        })
        return ctx


# ---------------------------------------------------------------------------
# Voucher Excel export  (event level)
# ---------------------------------------------------------------------------

class VoucherExportView(EventVoucherViewMixin, View):
    def get(self, request, *args, **kwargs):
        from io import BytesIO

        import openpyxl
        from pretix.base.models import Checkin, InvoiceAddress

        voucher = get_object_or_404(Voucher, pk=self.kwargs['pk'], event=request.event)
        event = request.event

        positions = list(
            _positions_qs(event=event, voucher=voucher)
            .select_related('order', 'item', 'variation')
            .order_by('order__datetime', 'pk')
        )
        position_pks = [pos.pk for pos in positions]

        order_pks = {pos.order_id for pos in positions}
        addr_map = {
            ia.order_id: ia
            for ia in InvoiceAddress.objects.filter(order_id__in=order_pks)
        }

        # Fetch all successful entry check-ins for these positions in one query
        checkin_map = defaultdict(list)
        for ci in (
            Checkin.objects
            .filter(position_id__in=position_pks, type=Checkin.TYPE_ENTRY, successful=True)
            .select_related('list')
            .order_by('datetime')
        ):
            checkin_map[ci.position_id].append(ci)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Orders'

        ws.append([
            'Order', 'Order Date', 'Status', 'Customer Email',
            'Invoice Name / Company', 'Street', 'ZIP', 'City', 'Country',
            'Attendee Name', 'Attendee Email', 'Ticket Type', 'Variation',
            'Checked In', 'Check-in Date/Time', 'Check-in List',
        ])

        status_labels = {
            Order.STATUS_PAID: 'Paid',
            Order.STATUS_PENDING: 'Pending',
            Order.STATUS_EXPIRED: 'Expired',
            Order.STATUS_CANCELED: 'Cancelled',
        }

        for pos in positions:
            addr = addr_map.get(pos.order_id)
            addr_name = ''
            if addr:
                parts = addr.name_parts or {}
                addr_name = (
                    ' '.join(filter(None, [parts.get('given_name', ''), parts.get('family_name', '')]))
                    or parts.get('_legacy', '')
                    or addr.company
                    or ''
                )

            checkins = checkin_map.get(pos.pk, [])
            checked_in = 'Yes' if checkins else 'No'
            checkin_times = ', '.join(ci.datetime.strftime('%Y-%m-%d %H:%M') for ci in checkins)
            checkin_lists = ', '.join(ci.list.name for ci in checkins)

            ws.append([
                pos.order.code,
                pos.order.datetime.strftime('%Y-%m-%d %H:%M'),
                status_labels.get(pos.order.status, pos.order.status),
                pos.order.email or '',
                addr_name,
                addr.street if addr else '',
                addr.zipcode if addr else '',
                addr.city if addr else '',
                str(addr.country) if addr else '',
                _get_attendee_name(pos),
                pos.attendee_email or '',
                str(pos.item.name) if pos.item else '',
                str(pos.variation.value) if pos.variation else '',
                checked_in,
                checkin_times,
                checkin_lists,
            ])

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f'voucher-{voucher.code}-orders.xlsx'
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# ---------------------------------------------------------------------------
# Voucher chart data endpoints  (AJAX, event level)
# ---------------------------------------------------------------------------

class VoucherTimelineDataView(EventVoucherViewMixin, View):
    def get(self, request, *args, **kwargs):
        voucher = get_object_or_404(
            Voucher, pk=self.kwargs['pk'], event=request.event
        )
        data = _timeline_data(_positions_qs(event=request.event, voucher=voucher))
        return JsonResponse(data)


class VoucherRampupDataView(EventVoucherViewMixin, View):
    """Daily ticket counts for every voucher in the event, day by day for 30 days before the event."""

    def get(self, request, *args, **kwargs):
        voucher = get_object_or_404(Voucher, pk=self.kwargs['pk'], event=request.event)
        event = request.event

        if not event.date_from:
            return JsonResponse({'vouchers': []})

        event_start = event.date_from.date()
        window_start = event_start - timedelta(days=30)

        rows = (
            _positions_qs(event=event)
            .filter(
                voucher__isnull=False,
                order__datetime__date__gte=window_start,
                order__datetime__date__lte=event_start,
            )
            .annotate(date=TruncDate('order__datetime'))
            .values('voucher_id', 'voucher__code', 'voucher__tag', 'date')
            .annotate(count=Count('id'))
            .order_by('voucher_id', 'date')
        )

        voucher_data = defaultdict(lambda: {'code': '', 'tag': '', 'dates': {}})
        for row in rows:
            vid = row['voucher_id']
            voucher_data[vid]['code'] = row['voucher__code']
            voucher_data[vid]['tag'] = row['voucher__tag'] or ''
            voucher_data[vid]['dates'][row['date']] = row['count']

        result = []
        for vid, vdata in voucher_data.items():
            points = []
            for days_before in range(30, -1, -1):
                date = event_start - timedelta(days=days_before)
                points.append({'x': -days_before, 'y': vdata['dates'].get(date, 0)})
            result.append({
                'code': vdata['code'],
                'tag': vdata['tag'],
                'is_this': vid == voucher.pk,
                'points': points,
            })

        return JsonResponse({'vouchers': result})


class VoucherComparisonDataView(EventVoucherViewMixin, View):
    def get(self, request, *args, **kwargs):
        voucher = get_object_or_404(
            Voucher, pk=self.kwargs['pk'], event=request.event
        )
        event = request.event
        all_qs = _positions_qs(event=event)

        this_qs = all_qs.filter(voucher=voucher)
        other_qs = all_qs.filter(voucher__isnull=False).exclude(voucher=voucher)
        no_voucher_qs = all_qs.filter(voucher__isnull=True)

        def by_date_dict(qs):
            rows = (
                qs.annotate(date=TruncDate('order__datetime'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )
            return {row['date'].isoformat(): row['count'] for row in rows}

        this_dict = by_date_dict(this_qs)
        other_dict = by_date_dict(other_qs)
        no_dict = by_date_dict(no_voucher_qs)

        all_dates = sorted(set(list(this_dict) + list(other_dict) + list(no_dict)))

        return JsonResponse({
            'labels': all_dates,
            'this_voucher': [this_dict.get(d, 0) for d in all_dates],
            'other_vouchers': [other_dict.get(d, 0) for d in all_dates],
            'no_voucher': [no_dict.get(d, 0) for d in all_dates],
        })


# ---------------------------------------------------------------------------
# Organizer-level statistics view
# ---------------------------------------------------------------------------

class OrgStatisticsView(OrganizerAdminMixin, ChartCSPMixin, TemplateView):
    template_name = 'pretix_voucher_statistics/org_statistics.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        organizer = self.request.organizer

        all_events = (
            Event.objects.filter(organizer=organizer)
            .order_by('-date_from')
        )

        selected_slugs = self.request.GET.getlist('events')
        if selected_slugs:
            selected_events = all_events.filter(slug__in=selected_slugs)
        else:
            selected_events = all_events[:6]

        ctx['all_events'] = all_events
        ctx['selected_events'] = list(selected_events)
        ctx['selected_slugs'] = [e.slug for e in ctx['selected_events']]
        ctx['selected_slugs_json'] = json.dumps(ctx['selected_slugs'])
        return ctx


class OrgStatisticsDataView(OrganizerAdminMixin, View):
    """Returns all chart data as JSON for the org statistics page."""

    def get(self, request, *args, **kwargs):
        organizer = request.organizer
        selected_slugs = request.GET.getlist('events')

        events_qs = Event.objects.filter(organizer=organizer)
        if selected_slugs:
            events_qs = events_qs.filter(slug__in=selected_slugs)
        else:
            events_qs = events_qs.order_by('-date_from')[:6]

        chart_type = request.GET.get('type', 'timeline')

        if chart_type == 'timeline':
            return JsonResponse(self._orders_over_time(events_qs))
        elif chart_type == 'leaderboard':
            return JsonResponse(self._voucher_leaderboard(events_qs))
        elif chart_type == 'days_before':
            return JsonResponse(self._days_before_event(events_qs))
        else:
            return JsonResponse({'error': 'unknown type'}, status=400)

    def _orders_over_time(self, events):
        result = {}
        for event in events:
            data = _timeline_data(_positions_qs(event=event))
            result[event.slug] = {
                'name': str(event.name),
                'labels': data['labels'],
                'cumulative': data['cumulative'],
                'daily': data['daily'],
            }
        return result

    def _voucher_leaderboard(self, events):
        result = {}
        for event in events:
            top = (
                Voucher.objects.filter(event=event)
                .annotate(
                    ticket_count=Count(
                        'orderposition',
                        filter=Q(orderposition__order__status__in=ACTIVE_STATUSES),
                    )
                )
                .filter(ticket_count__gt=0)
                .order_by('-ticket_count')[:10]
            )
            total = _positions_qs(event=event).count()
            result[event.slug] = {
                'name': str(event.name),
                'total': total,
                'vouchers': [
                    {
                        'code': v.code,
                        'tag': v.tag or '',
                        'count': v.ticket_count,
                        'pct': round(v.ticket_count / total * 100, 1) if total else 0,
                    }
                    for v in top
                ],
            }
        return result

    def _days_before_event(self, events):
        """
        For each event, return cumulative ticket count at each day from -30 to 0
        relative to the event start date, so events can be compared on the same axis.
        """
        result = {}
        for event in events:
            if not event.date_from:
                continue

            event_start = event.date_from.date()
            window_start = event_start - timedelta(days=30)

            rows = (
                _positions_qs(event=event)
                .filter(
                    order__datetime__date__gte=window_start,
                    order__datetime__date__lte=event_start,
                )
                .annotate(date=TruncDate('order__datetime'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )

            date_counts = {row['date']: row['count'] for row in rows}

            points = []
            for days_before in range(30, -1, -1):  # 30 down to 0
                date = event_start - timedelta(days=days_before)
                points.append({'x': -days_before, 'y': date_counts.get(date, 0)})

            result[event.slug] = {
                'name': str(event.name),
                'date_from': event_start.isoformat(),
                'points': points,
            }
        return result
