from rest_framework import serializers

from .models import Stock, StockAdjustment, StockAdjustmentItem, SuratLainItems, SuratTransferStokItems
from .serializers_base import FlexDateTimeField

# --- REPORTING SERIALIZERS ---

class StockInfoReportSerializer(serializers.ModelSerializer):
    """
    Serializer for the main stock information report.
    Gathers detailed information for each stock record.
    """
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category = serializers.CharField(source='product.category.name', read_only=True)
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True)
    packing = serializers.CharField(source='product.packing', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = Stock
        fields = [
            'product_code',
            'product_name',
            'product_category',
            'supplier_name',
            'packing',
            'carton_quantity',
            'pack_quantity',
            'warehouse_name',
        ]


class StockTransferReportSerializer(serializers.ModelSerializer):
    """
    Serializer for the stock transfer report.
    Gathers summary data for each item in an active stock transfer.
    """
    document_number = serializers.CharField(source='surat_transfer_stok.document_number', read_only=True)
    transaction_date = serializers.DateTimeField(source='surat_transfer_stok.transaction_date', format="%Y-%m-%d")
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True)
    packing = serializers.CharField(source='product.packing', read_only=True)
    source_warehouse = serializers.CharField(source='surat_transfer_stok.source_warehouse.name', read_only=True)
    destination_warehouse = serializers.CharField(source='surat_transfer_stok.destination_warehouse.name', read_only=True)

    class Meta:
        model = SuratTransferStokItems
        fields = [
            'document_number',
            'transaction_date',
            'product_name',
            'supplier_name',
            'packing',
            'carton_quantity',
            'pack_quantity',
            'source_warehouse',
            'destination_warehouse',
        ]


class ReturnReportSerializer(serializers.ModelSerializer):
    """
    Serializer for the purchase and sales return reports.
    """
    document_number = serializers.CharField(source='surat_lain.document_number', read_only=True)
    transaction_date = serializers.DateTimeField(source='surat_lain.transaction_date', format="%Y-%m-%d")
    warehouse_name = serializers.CharField(source='surat_lain.warehouse.name', read_only=True)
    notes = serializers.CharField(source='surat_lain.notes', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True)
    packing = serializers.CharField(source='product.packing', read_only=True)

    class Meta:
        model = SuratLainItems
        fields = [
            'document_number',
            'transaction_date',
            'warehouse_name',
            'product_name',
            'supplier_name',
            'packing',
            'carton_quantity',
            'pack_quantity',
            'notes',
        ]


class DocumentSummaryReportSerializer(serializers.ModelSerializer):
    """
    A dynamic and generic serializer for document summary reports.
    It adjusts its fields based on the report type provided by the view.
    """
    document_number = serializers.CharField(source='surat_lain.document_number', read_only=True)
    transaction_date = serializers.DateTimeField(source='surat_lain.transaction_date', format="%Y-%m-%d")
    warehouse_name = serializers.CharField(source='surat_lain.warehouse.name', read_only=True)
    notes = serializers.CharField(source='surat_lain.notes', read_only=True, allow_blank=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    packing = serializers.CharField(source='product.packing', read_only=True)

    # --- Conditionally included fields ---
    sj_number = serializers.CharField(source='surat_lain.sj_number', read_only=True)
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True)

    class Meta:
        model = SuratLainItems
        fields = [
            'document_number',
            'transaction_date',
            'sj_number',          # Will be removed for return reports
            'supplier_name',      # Will be removed for STB/SPB reports
            'warehouse_name',
            'product_code',
            'product_name',
            'packing',
            'carton_quantity',
            'pack_quantity',
            'notes',
        ]

    def __init__(self, *args, **kwargs):
        """
        Override init to dynamically remove fields based on the report type.
        """
        # This must be called first
        super().__init__(*args, **kwargs)

        # Get the report_type from the context passed by the view
        report_type = self.context.get('report_type')

        if report_type == 'return':
            # For return reports, we don't need the sj_number
            self.fields.pop('sj_number')


class StockAdjustmentItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    # The 'old' quantities will be read-only, populated automatically.
    old_carton_quantity = serializers.IntegerField(read_only=True)
    old_pack_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockAdjustmentItem
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'old_carton_quantity', 'old_pack_quantity',
            'new_carton_quantity', 'new_pack_quantity'
        ]
        read_only_fields = ['id', 'product_name', 'product_code']


class StockAdjustmentSerializer(serializers.ModelSerializer):
    items = StockAdjustmentItemSerializer(many=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    transaction_date = FlexDateTimeField(required=False, format="%Y-%m-%d")

    class Meta:
        model = StockAdjustment
        fields = [
            'id', 'document_number', 'warehouse', 'warehouse_name',
            'user', 'user_email', 'reason', 'transaction_date',
            'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'user', 'user_email', 'warehouse_name',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        warehouse = validated_data.get('warehouse')

        with transaction.atomic():
            adjustment = StockAdjustment.objects.create(**validated_data)

            for item_data in items_data:
                product = item_data['product']

                # Get the current stock record, locking it for the transaction.
                stock = Stock.objects.select_for_update().get(product=product, warehouse=warehouse)

                # Populate old quantities from the current stock
                item_data['old_carton_quantity'] = stock.carton_quantity
                item_data['old_pack_quantity'] = stock.pack_quantity

                # Create the audit record (the adjustment item)
                StockAdjustmentItem.objects.create(stock_adjustment=adjustment, **item_data)

                # Update the actual stock level to the new quantities
                stock.carton_quantity = item_data['new_carton_quantity']
                stock.pack_quantity = item_data['new_pack_quantity']
                stock.save()

        return adjustment


class StockReportSerializer(serializers.Serializer):
    """
    Serializer for stock in/out reports.
    """
    product_code = serializers.CharField()
    product_name = serializers.CharField()
    packing = serializers.CharField()
    total_carton_quantity = serializers.IntegerField()
    total_pack_quantity = serializers.IntegerField()
