from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PluginConfig


class PluginApp(PluginConfig):
    name = 'pretix_voucher_statistics'
    verbose_name = 'Voucher Statistics'

    class PretixPluginMeta:
        name = _('Voucher Statistics')
        author = 'Your Name'
        description = _('Detailed statistics and analytics for pretix vouchers, including per-voucher order tables, timeline graphs, and organizer-level event comparisons.')
        visible = True
        version = '1.0.0'
        category = 'FEATURE'
        compatibility = 'pretix>=2026.1.1'

    def ready(self):
        from . import signals  # noqa
