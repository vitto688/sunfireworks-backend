from rest_framework import serializers
from django.db import transaction

from .models import (
    Customer,
    SPG,
    SPGItems,
    SJ,
    SJItems,
    SPK,
    SPKItems,
    Stock,
    StockAdjustment,
    StockAdjustmentItem,
    SuratLain,
    SuratLainItems,
    SuratTransferStok,
    SuratTransferStokItems,
)
from .serializers_base import (
    FlexDateTimeField,
    _aggregate_existing_item_totals,
    _aggregate_item_totals,
    _apply_stock_deltas,
    _build_locked_stock_map,
    _build_spk_fulfillment_map,
    _build_spk_item_map,
    _build_stock_map,
    _ensure_stock_deltas_fit,
    _merge_stock_delta,
)

class SPGItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)

    packaging_size = serializers.CharField(max_length=50, required=False, allow_blank=True)
    inn = serializers.CharField(max_length=10, required=False, allow_blank=True)
    out = serializers.CharField(max_length=10, required=False, allow_blank=True)
    pjg = serializers.CharField(max_length=10, required=False, allow_blank=True)
    warehouse_size = serializers.CharField(max_length=50, required=False, allow_blank=True)
    packaging_weight = serializers.CharField(max_length=10, required=False, allow_blank=True)
    warehouse_weight = serializers.CharField(max_length=10, required=False, allow_blank=True)
    production_code = serializers.CharField(max_length=50, required=False, allow_blank=True)

    packing = serializers.ReadOnlyField(source='product.packing')
    supplier_name = serializers.ReadOnlyField(source='product.supplier.name')

    class Meta:
        model = SPGItems
        fields = [
            'id',
            'product',
            'product_name',
            'product_code',
            'carton_quantity',
            'pack_quantity',
            'packaging_size',
            'inn',
            'out',
            'pjg',
            'warehouse_size',
            'packaging_weight',
            'warehouse_weight',
            'production_code',
            'created_at',
            'updated_at',
            'packing',
            'supplier_name',
        ]
        read_only_fields = [
            'id',
            'product_name',
            'product_code',
            'created_at',
            'updated_at'
        ]


class SPGSerializer(serializers.ModelSerializer):
    items = SPGItemsSerializer(many=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    container_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    vehicle_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    start_unload = serializers.CharField(max_length=50, required=False, allow_blank=True)
    finish_load = serializers.CharField(max_length=50, required=False, allow_blank=True)

    transaction_date = FlexDateTimeField(required=False, format="%Y-%m-%d")

    class Meta:
        model = SPG
        fields = [
            'id',
            'document_number',
            'document_type',
            'warehouse',
            'warehouse_name',
            'container_number',
            'vehicle_number',
            'sj_number',
            'start_unload',
            'finish_load',
            'user',
            'user_username',
            'transaction_date',
            'notes',
            'created_at',
            'updated_at',
            'items'
        ]
        read_only_fields = [
            'id',
            'document_number',
            'user',
            'user_username',
            'warehouse_name',
            'created_at',
            'updated_at',
            'document_type'
        ]

    def validate(self, attrs):
        """
        Conditionally require fields only for 'IMPORT' document type.
        """
        # Get the document_type from the context passed by the view
        document_type = self.context.get('document_type')

        if document_type == 'IMPORT':
            required_fields = [
                'container_number', 'vehicle_number', 'start_unload', 'finish_load'
            ]
            errors = {}
            for field in required_fields:
                if not attrs.get(field):
                    errors[field] = ["This field is required for IMPORT documents."]

            item_errors = []
            required_item_fields = [
                'inn', 'out', 'pjg', 'warehouse_size', 'packaging_weight',
                'warehouse_weight', 'production_code', 'packaging_size'
            ]
            for item_data in attrs.get('items', []):
                current_item_errors = {}
                for field in required_item_fields:
                    if not item_data.get(field):
                        current_item_errors[field] = ["This field is required for IMPORT documents."]
                if current_item_errors:
                    item_errors.append(current_item_errors)
                else:
                    item_errors.append({}) # Keep order consistent

            if item_errors and any(item_errors):
                errors['items'] = item_errors

            if errors:
                raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
            items_data = validated_data.pop('items')
            with transaction.atomic():
                spg = SPG.objects.create(**validated_data)
                stock_deltas = {}
                for item_data in items_data:
                    SPGItems.objects.create(spg=spg, **item_data)
                    _merge_stock_delta(
                        stock_deltas,
                        item_data['product'].id,
                        spg.warehouse_id,
                        item_data.get('carton_quantity', 0),
                        item_data.get('pack_quantity', 0),
                    )
                _apply_stock_deltas(stock_deltas)
            return spg

    def update(self, instance, validated_data):
            items_data = validated_data.pop('items')

            with transaction.atomic():
                stock_deltas = {}
                for item in instance.items.all():
                    _merge_stock_delta(
                        stock_deltas,
                        item.product_id,
                        instance.warehouse_id,
                        -item.carton_quantity,
                        -item.pack_quantity,
                    )

                instance.document_number = validated_data.get('document_number', instance.document_number)
                instance.warehouse = validated_data.get('warehouse', instance.warehouse)
                instance.container_number = validated_data.get('container_number', instance.container_number)
                instance.vehicle_number = validated_data.get('vehicle_number', instance.vehicle_number)
                instance.sj_number = validated_data.get('sj_number', instance.sj_number)
                instance.start_unload = validated_data.get('start_unload', instance.start_unload)
                instance.finish_load = validated_data.get('finish_load', instance.finish_load)
                instance.notes = validated_data.get('notes', instance.notes)
                instance.save()

                instance.items.all().delete()
                for item_data in items_data:
                    SPGItems.objects.create(spg=instance, **item_data)
                    _merge_stock_delta(
                        stock_deltas,
                        item_data['product'].id,
                        instance.warehouse_id,
                        item_data.get('carton_quantity', 0),
                        item_data.get('pack_quantity', 0),
                    )

                _apply_stock_deltas(stock_deltas)

            return instance


class SuratTransferStokItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)

    packing = serializers.ReadOnlyField(source='product.packing')
    supplier_name = serializers.ReadOnlyField(source='product.supplier.name')

    class Meta:
        model = SuratTransferStokItems
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'carton_quantity', 'pack_quantity', 'packing', 'supplier_name'
        ]
        read_only_fields = ['id', 'product_name', 'product_code']


class SuratTransferStokSerializer(serializers.ModelSerializer):
    items = SuratTransferStokItemsSerializer(many=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    source_warehouse_name = serializers.CharField(source='source_warehouse.name', read_only=True)
    destination_warehouse_name = serializers.CharField(source='destination_warehouse.name', read_only=True)
    transaction_date = FlexDateTimeField(required=False, format="%Y-%m-%d")

    class Meta:
        model = SuratTransferStok
        fields = [
            'id', 'document_number', 'source_warehouse', 'source_warehouse_name',
            'destination_warehouse', 'destination_warehouse_name', 'user', 'user_username',
            'is_deleted', 'deleted_at', 'transaction_date', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'user', 'user_username',
            'source_warehouse_name', 'destination_warehouse_name',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]

    def validate(self, data):
        """
        Validates the stock transfer, checking for sufficient stock.
        """
        source_warehouse = data.get('source_warehouse')
        destination_warehouse = data.get('destination_warehouse')
        items = data.get('items')
        item_totals = _aggregate_item_totals(items)
        original_item_totals = {}

        # Rule: Source and destination cannot be the same
        if source_warehouse == destination_warehouse:
            raise serializers.ValidationError("Source and destination warehouses cannot be the same.")

        product_ids = list(item_totals.keys())
        stock_map = _build_stock_map(source_warehouse, product_ids)

        # For updates, the instance is available in the context
        is_update = self.instance is not None
        if is_update:
            original_item_totals = _aggregate_existing_item_totals(self.instance.items.all())

        for item_total in item_totals.values():
            product = item_total['product']
            stock_at_source = stock_map.get(product.id)

            if stock_at_source is None:
                raise serializers.ValidationError(f"Stock record for {product.name} at {source_warehouse.name} not found.")

            original_carton_qty = 0
            original_pack_qty = 0
            if is_update and self.instance.source_warehouse == source_warehouse:
                original_item = original_item_totals.get(product.id)
                if original_item:
                    original_carton_qty = original_item['carton_quantity']
                    original_pack_qty = original_item['pack_quantity']

            if (stock_at_source.carton_quantity + original_carton_qty) < item_total['carton_quantity']:
                raise serializers.ValidationError(f"Insufficient carton stock for {product.name} at {source_warehouse.name}.")
            if (stock_at_source.pack_quantity + original_pack_qty) < item_total['pack_quantity']:
                raise serializers.ValidationError(f"Insufficient pack stock for {product.name} at {source_warehouse.name}.")

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            transfer = SuratTransferStok.objects.create(**validated_data)
            item_totals = _aggregate_item_totals(items_data)
            stock_deltas = {}
            for item_total in item_totals.values():
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    transfer.source_warehouse_id,
                    -item_total['carton_quantity'],
                    -item_total['pack_quantity'],
                )
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    transfer.destination_warehouse_id,
                    item_total['carton_quantity'],
                    item_total['pack_quantity'],
                )
            _ensure_stock_deltas_fit(_build_locked_stock_map(stock_deltas), stock_deltas)
            for item_data in items_data:
                SuratTransferStokItems.objects.create(surat_transfer_stok=transfer, **item_data)
            _apply_stock_deltas(stock_deltas)
        return transfer

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        new_source_warehouse = validated_data.get('source_warehouse', instance.source_warehouse)
        new_destination_warehouse = validated_data.get('destination_warehouse', instance.destination_warehouse)

        with transaction.atomic():
            stock_deltas = {}
            for item in instance.items.all():
                _merge_stock_delta(
                    stock_deltas,
                    item.product_id,
                    instance.source_warehouse_id,
                    item.carton_quantity,
                    item.pack_quantity,
                )
                _merge_stock_delta(
                    stock_deltas,
                    item.product_id,
                    instance.destination_warehouse_id,
                    -item.carton_quantity,
                    -item.pack_quantity,
                )

            item_totals = _aggregate_item_totals(items_data)
            for item_total in item_totals.values():
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    new_source_warehouse.id,
                    -item_total['carton_quantity'],
                    -item_total['pack_quantity'],
                )
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    new_destination_warehouse.id,
                    item_total['carton_quantity'],
                    item_total['pack_quantity'],
                )

            _ensure_stock_deltas_fit(_build_locked_stock_map(stock_deltas), stock_deltas)
            _apply_stock_deltas(stock_deltas)

            instance.source_warehouse = new_source_warehouse
            instance.destination_warehouse = new_destination_warehouse
            instance.save()

            # Re-create the items for the transfer
            instance.items.all().delete()
            for item_data in items_data:
                SuratTransferStokItems.objects.create(surat_transfer_stok=instance, **item_data)

        return instance


class SPKItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)

    packing = serializers.ReadOnlyField(source='product.packing')
    supplier_name = serializers.ReadOnlyField(source='product.supplier.name')

    unfulfilled_carton_quantity = serializers.SerializerMethodField()
    unfulfilled_pack_quantity = serializers.SerializerMethodField()

    class Meta:
        model = SPKItems
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'carton_quantity', 'pack_quantity', 'packing', 'supplier_name',
            'unfulfilled_carton_quantity',
            'unfulfilled_pack_quantity',
        ]
        read_only_fields = ['id', 'product_name', 'product_code']

    def _get_fulfilled_totals(self, obj):
        cache = getattr(self, '_fulfilled_totals_cache', None)
        if cache is None:
            cache = {}
            self._fulfilled_totals_cache = cache

        if obj.pk not in cache:
            cache[obj.pk] = SJItems.objects.filter(
                sj__spk=obj.spk,
                product=obj.product,
                sj__is_deleted=False
            ).aggregate(
                carton_total=Coalesce(Sum('carton_quantity'), 0),
                pack_total=Coalesce(Sum('pack_quantity'), 0),
            )

        return cache[obj.pk]

    def get_unfulfilled_carton_quantity(self, obj):
        """
        Calculates the remaining carton quantity by subtracting all fulfilled SJ items.
        'obj' here is an instance of SPKItems.
        """
        totals = self._get_fulfilled_totals(obj)
        return obj.carton_quantity - totals['carton_total']

    def get_unfulfilled_pack_quantity(self, obj):
        """
        Calculates the remaining pack quantity by subtracting all fulfilled SJ items.
        """
        totals = self._get_fulfilled_totals(obj)
        return obj.pack_quantity - totals['pack_total']


class SPKSerializer(serializers.ModelSerializer):
    items = SPKItemsSerializer(many=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_address = serializers.CharField(source='customer.address', read_only=True)
    customer_upline = serializers.CharField(source='customer.upline', read_only=True)
    transaction_date = FlexDateTimeField(required=False, format="%Y-%m-%d")

    class Meta:
        model = SPK
        fields = [
            'id', 'document_number',
            'customer', 'customer_name', 'customer_address', 'customer_upline', 'notes', 'user', 'user_username',
            'is_deleted', 'deleted_at', 'transaction_date', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'user', 'user_username', 'customer_name', 'is_deleted',
            'deleted_at', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            spk = SPK.objects.create(**validated_data)
            for item_data in items_data:
                SPKItems.objects.create(spk=spk, **item_data)
        return spk

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)

        if items_data is not None:
            with transaction.atomic():
                instance.items.all().delete()
                for item_data in items_data:
                    SPKItems.objects.create(spk=instance, **item_data)
        return instance


class SJItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)

    packing = serializers.ReadOnlyField(source='product.packing')
    supplier_name = serializers.ReadOnlyField(source='product.supplier.name')

    class Meta:
        model = SJItems
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'carton_quantity', 'pack_quantity', 'packing', 'supplier_name'
        ]
        read_only_fields = ['id', 'product_name', 'product_code']


class SJSerializer(serializers.ModelSerializer):
    items = SJItemsSerializer(many=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_address = serializers.CharField(source='customer.address', read_only=True)
    customer_upline = serializers.CharField(source='customer.upline', read_only=True)
    spk_document_number = serializers.CharField(source='spk.document_number', read_only=True)
    transaction_date = FlexDateTimeField(required=False, format="%Y-%m-%d")

    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)

    class Meta:
        model = SJ
        fields = [
            'id',
            'document_number',
            'spk',
            'spk_document_number',
            'warehouse',
            'warehouse_name',
            'sj_type',
            'customer',
            'customer_name',
            'customer_address',
            'customer_upline',
            'non_customer_name',
            'vehicle_type',
            'vehicle_number',
            'notes',
            'user',
            'user_username',
            'transaction_date',
            'is_deleted',
            'deleted_at',
            'created_at',
            'updated_at',
            'items',
        ]
        read_only_fields = [
            'id',
            'document_number',
            'user',
            'user_username',
            'warehouse_name',
            'customer_name',
            'spk_document_number',
            'is_deleted',
            'deleted_at',
            'created_at',
            'updated_at',
        ]

    def validate(self, data):
        """
        Custom validation for:
        1. Conditional customer vs. non-customer fields.
        2. Sufficient stock in the source warehouse.
        3. Ensuring SJ quantities do not exceed the unfulfilled quantities from the parent SPK.
        """
        # --- Get the SPK and items from the request data ---
        # On a create, 'spk' will be in data. On an update, it's on the instance.
        spk = data.get('spk') or (self.instance and self.instance.spk)
        items_data = data.get('items')
        item_totals = _aggregate_item_totals(items_data)

        if not spk:
            raise serializers.ValidationError({"spk": "An SPK must be specified."})

        product_ids = list(item_totals.keys())
        spk_item_map = _build_spk_item_map(spk, product_ids)
        fulfilled_map = _build_spk_fulfillment_map(
            spk,
            product_ids,
            exclude_sj_id=self.instance.pk if self.instance else None,
        )
        original_item_totals = {}
        if self.instance:
            original_item_totals = _aggregate_existing_item_totals(self.instance.items.all())

        for item_total in item_totals.values():
            product = item_total['product']

            # --- Validation 1: Check if the product is in the original SPK ---
            spk_item = spk_item_map.get(product.id)
            if spk_item is None:
                raise serializers.ValidationError({
                    f"product_{product.id}": f"Product '{product.name}' is not listed in the original SPK ({spk.document_number})."
                })

            # --- Validation 2: Check if the quantity exceeds the unfulfilled amount ---
            fulfilled_totals = fulfilled_map.get(product.id, {'carton_total': 0, 'pack_total': 0})

            original_cartons = 0
            original_packs = 0
            original_item = original_item_totals.get(product.id)
            if original_item:
                original_cartons = original_item['carton_quantity']
                original_packs = original_item['pack_quantity']

            unfulfilled_cartons = spk_item.carton_quantity - fulfilled_totals['carton_total'] + original_cartons
            unfulfilled_packs = spk_item.pack_quantity - fulfilled_totals['pack_total'] + original_packs

            if item_total['carton_quantity'] > unfulfilled_cartons:
                raise serializers.ValidationError({
                    f"product_{product.id}": f"Carton quantity for '{product.name}' ({item_total['carton_quantity']}) exceeds the unfulfilled quantity on the SPK ({unfulfilled_cartons})."
                })

            if item_total['pack_quantity'] > unfulfilled_packs:
                raise serializers.ValidationError({
                    f"product_{product.id}": f"Pack quantity for '{product.name}' ({item_total['pack_quantity']}) exceeds the unfulfilled quantity on the SPK ({unfulfilled_packs})."
                })

        # --- Stock Validation ---
        warehouse = data.get('warehouse') or (self.instance and self.instance.warehouse)
        is_update = self.instance is not None
        product_ids = list(item_totals.keys())
        stock_map = _build_stock_map(warehouse, product_ids)
        original_item_totals = {}
        if is_update:
            original_item_totals = _aggregate_existing_item_totals(self.instance.items.all())

        for item_total in item_totals.values():
            product = item_total['product']
            stock = stock_map.get(product.id)
            if stock is None:
                raise serializers.ValidationError(f"Stock record for {product.name} at {warehouse.name} not found.")

            original_carton = 0
            original_pack = 0
            if is_update:
                original_item = original_item_totals.get(product.id)
                if original_item:
                    original_carton = original_item['carton_quantity']
                    original_pack = original_item['pack_quantity']

            if (stock.carton_quantity + original_carton) < item_total['carton_quantity']:
                raise serializers.ValidationError(f"Insufficient carton stock for {product.name} at {warehouse.name}.")
            if (stock.pack_quantity + original_pack) < item_total['pack_quantity']:
                raise serializers.ValidationError(f"Insufficient pack stock for {product.name} at {warehouse.name}.")

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            sj = SJ.objects.create(**validated_data)
            item_totals = _aggregate_item_totals(items_data)
            stock_deltas = {}
            for item_total in item_totals.values():
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    sj.warehouse_id,
                    -item_total['carton_quantity'],
                    -item_total['pack_quantity'],
                )
            _ensure_stock_deltas_fit(_build_locked_stock_map(stock_deltas), stock_deltas)
            for item_data in items_data:
                SJItems.objects.create(sj=sj, **item_data)
            _apply_stock_deltas(stock_deltas)
        return sj

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        # Get the new warehouse from the request, falling back to the instance's current warehouse if not provided.
        new_warehouse = validated_data.get('warehouse', instance.warehouse)

        with transaction.atomic():
            stock_deltas = {}
            # --- Step 1: Revert the old stock from the OLD warehouse ---
            # This is critical. It adds the quantities back to the original source warehouse.
            original_item_totals = _aggregate_existing_item_totals(instance.items.all())
            for item_total in original_item_totals.values():
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    instance.warehouse_id,  # Use the ORIGINAL warehouse here
                    item_total['carton_quantity'],
                    item_total['pack_quantity'],
                )

            # --- Step 2: Apply the new stock to the NEW warehouse ---
            # This subtracts the new quantities from the potentially new warehouse.
            item_totals = _aggregate_item_totals(items_data)
            for item_total in item_totals.values():
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    new_warehouse.id,  # Use the NEW warehouse here
                    -item_total['carton_quantity'],
                    -item_total['pack_quantity'],
                )

            # --- Step 3: Update the SJ instance itself and its items ---
            # Remove read-only fields before calling super().update()
            validated_data.pop('transaction_date', None)
            _ensure_stock_deltas_fit(_build_locked_stock_map(stock_deltas), stock_deltas)
            instance = super().update(instance, validated_data) # This updates instance.warehouse to new_warehouse
            # Re-create the items for the updated SJ
            instance.items.all().delete()
            for item_data in items_data:
                SJItems.objects.create(sj=instance, **item_data)

            _apply_stock_deltas(stock_deltas)

        return instance


class SuratLainItemsSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)

    packing = serializers.ReadOnlyField(source='product.packing')
    supplier_name = serializers.ReadOnlyField(source='product.supplier.name')

    class Meta:
        model = SuratLainItems
        fields = ['id', 'product', 'product_name', 'product_code', 'packing', 'supplier_name', 'carton_quantity', 'pack_quantity']
        read_only_fields = ['id', 'product_name', 'product_code']


class SuratLainSerializer(serializers.ModelSerializer):
    items = SuratLainItemsSerializer(many=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    transaction_date = FlexDateTimeField(required=False, format="%Y-%m-%d")

    class Meta:
        model = SuratLain
        fields = [
            'id', 'document_number', 'document_type', 'sj_number', 'warehouse',
            'warehouse_name', 'user', 'user_username', 'notes', 'is_deleted',
            'deleted_at', 'transaction_date', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'document_type', 'user', 'user_username',
            'warehouse_name', 'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        ]

    def validate(self, data):
        """
        Custom validation for:
        1. Sufficient stock for OUTGOING document types (SPB, RETUR_PEMBELIAN).
        """
        doc_type = self.context.get('document_type')

        # --- Stock Validation for Outgoing Types ---
        # This check only runs for types that are NOT considered incoming.
        if doc_type not in SuratLain.INCOMING_TYPES:
            # Get the warehouse from the incoming data, or from the existing instance on updates.
            warehouse = data.get('warehouse') or (self.instance and self.instance.warehouse)
            items_data = data.get('items', [])
            item_totals = _aggregate_item_totals(items_data)
            product_ids = list(item_totals.keys())
            stock_map = _build_stock_map(warehouse, product_ids)
            is_update = self.instance is not None
            original_item_totals = {}
            if is_update:
                original_item_totals = _aggregate_existing_item_totals(self.instance.items.all())

            for item_total in item_totals.values():
                product = item_total['product']
                stock = stock_map.get(product.id)
                if stock is None:
                    raise serializers.ValidationError(f"Stock record for {product.name} at {warehouse.name} not found.")

                # On update, we can "use" the stock from the original document
                # before checking if the new amount is available.
                original_carton = 0
                original_pack = 0
                if is_update:
                    original_item = original_item_totals.get(product.id)
                    if original_item:
                        original_carton = original_item['carton_quantity']
                        original_pack = original_item['pack_quantity']

                # Check if available stock is sufficient for the new outgoing amount
                if (stock.carton_quantity + original_carton) < item_total['carton_quantity']:
                    raise serializers.ValidationError(f"Insufficient carton stock for {product.name} at {warehouse.name}.")
                if (stock.pack_quantity + original_pack) < item_total['pack_quantity']:
                    raise serializers.ValidationError(f"Insufficient pack stock for {product.name} at {warehouse.name}.")

        # If all validation passes, return the data.
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        doc_type = self.context.get('document_type')
        item_totals = _aggregate_item_totals(items_data)

        with transaction.atomic():
            surat = SuratLain.objects.create(document_type=doc_type, **validated_data)
            stock_deltas = {}
            for item_total in item_totals.values():
                if doc_type in SuratLain.INCOMING_TYPES:
                    carton_delta = item_total['carton_quantity']
                    pack_delta = item_total['pack_quantity']
                else: # Outgoing
                    carton_delta = -item_total['carton_quantity']
                    pack_delta = -item_total['pack_quantity']
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    surat.warehouse_id,
                    carton_delta,
                    pack_delta,
                )
            _ensure_stock_deltas_fit(_build_locked_stock_map(stock_deltas), stock_deltas)
            for item_data in items_data:
                SuratLainItems.objects.create(surat_lain=surat, **item_data)
            _apply_stock_deltas(stock_deltas)
        return surat

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        new_warehouse = validated_data.get('warehouse', instance.warehouse)
        item_totals = _aggregate_item_totals(items_data)

        with transaction.atomic():
            stock_deltas = {}
            # Revert old stock movements
            instance.soft_delete() # This flips is_deleted=True, so we must flip it back
            instance.is_deleted = False
            instance.deleted_at = None

            # Apply new stock movements
            for item_total in item_totals.values():
                if instance.document_type in SuratLain.INCOMING_TYPES:
                    carton_delta = item_total['carton_quantity']
                    pack_delta = item_total['pack_quantity']
                else: # Outgoing
                    carton_delta = -item_total['carton_quantity']
                    pack_delta = -item_total['pack_quantity']
                _merge_stock_delta(
                    stock_deltas,
                    item_total['product'].id,
                    new_warehouse.id,
                    carton_delta,
                    pack_delta,
                )

            _ensure_stock_deltas_fit(_build_locked_stock_map(stock_deltas), stock_deltas)

            # Update the instance itself
            instance = super().update(instance, validated_data)

            # Re-create items and save the instance's final state
            instance.items.all().delete()
            for item_data in items_data:
                SuratLainItems.objects.create(surat_lain=instance, **item_data)
            instance.save()
            _apply_stock_deltas(stock_deltas)

        return instance
