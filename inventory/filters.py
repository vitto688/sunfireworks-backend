import django_filters
from django.db import models
from django.utils import timezone
from .models import SuratTransferStokItems, SuratLainItems

class AwareDateTimeFilter(django_filters.DateTimeFilter):
    """
    Custom DateTimeFilter that ensures the filtered value is timezone-aware.
    """
    def filter(self, qs, value):
        if value:
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone.get_current_timezone())
        return super().filter(qs, value)

class StockTransferReportFilter(django_filters.FilterSet):
    """
    FilterSet for the stock transfer report.
    Allows filtering by a date range for the transaction_date.
    """
    start_date = AwareDateTimeFilter(
        field_name='surat_transfer_stok__created_at',
        lookup_expr='gte' # Greater than or equal to
    )
    end_date = AwareDateTimeFilter(
        field_name='surat_transfer_stok__created_at',
        lookup_expr='lte' # Less than or equal to
    )

    class Meta:
        model = SuratTransferStokItems
        fields = ['start_date', 'end_date']


class ReturnReportFilter(django_filters.FilterSet):
    """
    FilterSet for the return reports (pembelian and penjualan).
    Allows filtering by a date range for the transaction_date.
    """
    start_date = AwareDateTimeFilter(
        field_name='surat_lain__transaction_date',
        lookup_expr='gte' # Greater than or equal to
    )
    end_date = AwareDateTimeFilter(
        field_name='surat_lain__transaction_date',
        lookup_expr='lte' # Less than or equal to
    )

    class Meta:
        model = SuratLainItems
        fields = ['start_date', 'end_date']
