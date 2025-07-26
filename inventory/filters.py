import django_filters
from django.db import models
from django.utils import timezone
import datetime
from .models import SuratTransferStokItems, SuratLainItems, SPG, SPK, SJ, SuratTransferStok, SuratLain, Stock


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


class StockInfoReportFilter(django_filters.FilterSet):
    """
    FilterSet for the Stock Information report.
    Allows filtering by warehouse, supplier, and category.
    """
    # Filters by the ID of the related warehouse
    warehouse = django_filters.NumberFilter(field_name='warehouse__id')

    # Filters by the ID of the product's supplier
    supplier = django_filters.NumberFilter(field_name='product__supplier__id')

    # Filters by the ID of the product's category
    category = django_filters.NumberFilter(field_name='product__category__id')

    class Meta:
        model = Stock
        fields = ['warehouse', 'supplier', 'category']


class StockTransferReportFilter(django_filters.FilterSet):
    """
    FilterSet for the stock transfer report.
    """
    start_date = AwareDateTimeFilter(
        field_name='surat_transfer_stok__transaction_date',
        lookup_expr='gte'
    )
    end_date = AwareDateTimeFilter(
        field_name='surat_transfer_stok__transaction_date',
        lookup_expr='lte',
        adjust_for_end_date=True
    )

    # Filters by the ID of the document's source warehouse
    source_warehouse = django_filters.NumberFilter(field_name='surat_transfer_stok__source_warehouse__id')

    # Filters by the ID of the document's destination warehouse
    destination_warehouse = django_filters.NumberFilter(field_name='surat_transfer_stok__destination_warehouse__id')

    # Filters by the ID of the item's product's supplier
    supplier = django_filters.NumberFilter(field_name='product__supplier__id')

    # Filters by the ID of the item's product's category
    category = django_filters.NumberFilter(field_name='product__category__id')

    class Meta:
        model = SuratTransferStokItems
        fields = [
            'start_date',
            'end_date',
            'source_warehouse',
            'destination_warehouse',
            'supplier',
            'category'
        ]


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
    # Filters by the ID of the document's warehouse
    warehouse = django_filters.NumberFilter(field_name='surat_lain__warehouse__id')

       # Filters by the ID of the item's product's supplier
    supplier = django_filters.NumberFilter(field_name='product__supplier__id')

       # Filters by the ID of the item's product's category
    category = django_filters.NumberFilter(field_name='product__category__id')

    class Meta:
        model = SuratLainItems
        fields = ['start_date', 'end_date', 'warehouse', 'supplier', 'category']


class SPGFilter(django_filters.FilterSet):
    """FilterSet for the SPG ViewSet."""
    start_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='gte')
    end_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='lte', adjust_for_end_date=True)
    warehouse = django_filters.NumberFilter(field_name='warehouse__id')
    document_number = django_filters.CharFilter(field_name='document_number', lookup_expr='icontains')

    class Meta:
        model = SPG
        fields = ['start_date', 'end_date', 'warehouse', 'document_number']


class SPKFilter(django_filters.FilterSet):
    """FilterSet for the SPK ViewSet."""
    start_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='gte')
    end_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='lte', adjust_for_end_date=True)
    document_number = django_filters.CharFilter(field_name='document_number', lookup_expr='icontains')

    class Meta:
        model = SPK
        fields = ['start_date', 'end_date', 'document_number']


class SJFilter(django_filters.FilterSet):
    """FilterSet for the SJ ViewSet."""
    start_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='gte')
    end_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='lte', adjust_for_end_date=True)
    warehouse = django_filters.NumberFilter(field_name='warehouse__id')
    document_number = django_filters.CharFilter(field_name='document_number', lookup_expr='icontains')

    class Meta:
        model = SJ
        fields = ['start_date', 'end_date', 'warehouse', 'document_number']


class SuratTransferStokFilter(django_filters.FilterSet):
    """FilterSet for the SuratTransferStok ViewSet."""
    start_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='gte')
    end_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='lte', adjust_for_end_date=True)
    # For this model, we can filter by either source or destination warehouse
    source_warehouse = django_filters.NumberFilter(field_name='source_warehouse__id')
    destination_warehouse = django_filters.NumberFilter(field_name='destination_warehouse__id')
    document_number = django_filters.CharFilter(field_name='document_number', lookup_expr='icontains')

    class Meta:
        model = SuratTransferStok
        fields = ['start_date', 'end_date', 'source_warehouse', 'destination_warehouse', 'document_number']


class SuratLainFilter(django_filters.FilterSet):
    """FilterSet for the SuratLain ViewSet."""
    start_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='gte')
    end_date = AwareDateTimeFilter(field_name='transaction_date', lookup_expr='lte', adjust_for_end_date=True)
    warehouse = django_filters.NumberFilter(field_name='warehouse__id')
    document_number = django_filters.CharFilter(field_name='document_number', lookup_expr='icontains')

    class Meta:
        model = SuratLain
        fields = ['start_date', 'end_date', 'warehouse', 'document_number']
