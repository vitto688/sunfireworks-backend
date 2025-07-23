import django_filters
from django.db import models
from django.utils import timezone
import datetime
from .models import SuratTransferStokItems, SuratLainItems

class AwareDateTimeFilter(django_filters.DateTimeFilter):
    """
    Custom DateTimeFilter that handles timezone awareness and can adjust
    the end_date to include the entire day.
    """
    def __init__(self, *args, **kwargs):
        self.adjust_for_end_date = kwargs.pop('adjust_for_end_date', False)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone.get_current_timezone())

            if self.adjust_for_end_date:
                value = value + datetime.timedelta(days=1)
                self.lookup_expr = 'lt' # Use 'lt' (less than) instead of 'lte'

        return super().filter(qs, value)

class StockTransferReportFilter(django_filters.FilterSet):
    """
    FilterSet for the stock transfer report.
    """
    start_date = AwareDateTimeFilter(
        field_name='surat_transfer_stok__created_at',
        lookup_expr='gte'
    )
    end_date = AwareDateTimeFilter(
        field_name='surat_transfer_stok__created_at',
        lookup_expr='lte',
        adjust_for_end_date=True
    )

    class Meta:
        model = SuratTransferStokItems
        fields = ['start_date', 'end_date']


class ReturnReportFilter(django_filters.FilterSet):
    """
    FilterSet for the return reports (pembelian and penjualan).
    """
    start_date = AwareDateTimeFilter(
        field_name='surat_lain__transaction_date',
        lookup_expr='gte'
    )
    end_date = AwareDateTimeFilter(
        field_name='surat_lain__transaction_date',
        lookup_expr='lte',
        adjust_for_end_date=True
    )

    class Meta:
        model = SuratLainItems
        fields = ['start_date', 'end_date']
