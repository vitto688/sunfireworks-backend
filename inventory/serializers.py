from rest_framework import serializers
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, SPG, SPGItems, SuratTransferStok, SuratTransferStokItems, SPK, SPKItems, SJ, SJItems, SuratLain, SuratLainItems
from django.db import transaction
from django.db.models import F

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'email',
            'address',
            'pic_name',
            'pic_contact',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'code',
            'name',
            'category',
            'category_name',
            'supplier',
            'supplier_name',
            'supplier_price',
            'packing',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    is_product_deleted = serializers.BooleanField(source='product.is_deleted', read_only=True)
    packing = serializers.ReadOnlyField(source='product.packing')
    supplier_name = serializers.ReadOnlyField(source='product.supplier.name')

    class Meta:
        model = Stock
        fields = [
            'id',
            'product',
            'product_name',
            'product_code',
            'packing',
            'supplier_name',
            'warehouse',
            'warehouse_name',
            'carton_quantity',
            'pack_quantity',
            'is_product_deleted',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if 'product' in data and data['product'].is_deleted:
            raise serializers.ValidationError(
                "Cannot perform operations on stock of deleted product"
            )
        return data

class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    stocks = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'code',
            'name',
            'category',
            'category_name',
            'supplier',
            'supplier_name',
            'supplier_price',
            'packing',
            'stocks',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_stocks(self, obj):
        if obj.is_deleted:
            return {}

        # Get all warehouses
        warehouses = Warehouse.objects.all()

        # Initialize stock data with all warehouses
        stock_data = {
            warehouse.name: {'pack': 0, 'carton': 0}
            for warehouse in warehouses
        }

        # Get and update stock quantities where they exist
        stocks = Stock.objects.filter(product=obj)
        for stock in stocks:
            warehouse_name = stock.warehouse.name
            stock_data[warehouse_name]['pack'] = stock.pack_quantity
            stock_data[warehouse_name]['carton'] = stock.carton_quantity

        return stock_data


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id',
            'name',
            'address',
            'contact_number',
            'upline',
            'is_deleted',
            'deleted_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['is_deleted', 'deleted_at', 'created_at', 'updated_at']


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
    user_email = serializers.CharField(source='user.email', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    container_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    vehicle_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    start_unload = serializers.CharField(max_length=50, required=False, allow_blank=True)
    finish_load = serializers.CharField(max_length=50, required=False, allow_blank=True)

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
            'user_email',
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
            'user_email',
            'warehouse_name',
            'transaction_date',
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
                for item_data in items_data:
                    SPGItems.objects.create(spg=spg, **item_data)
                    Stock.objects.filter(
                        product=item_data['product'],
                        warehouse=spg.warehouse
                    ).update(
                        carton_quantity=F('carton_quantity') + item_data.get('carton_quantity', 0),
                        pack_quantity=F('pack_quantity') + item_data.get('pack_quantity', 0)
                    )
            return spg

    def update(self, instance, validated_data):
            items_data = validated_data.pop('items')

            with transaction.atomic():
                for item in instance.items.all():
                    Stock.objects.filter(
                        product=item.product,
                        warehouse=instance.warehouse
                    ).update(
                        carton_quantity=F('carton_quantity') - item.carton_quantity,
                        pack_quantity=F('pack_quantity') - item.pack_quantity
                    )

                instance.document_number = validated_data.get('document_number', instance.document_number)
                instance.warehouse = validated_data.get('warehouse', instance.warehouse)
                instance.container_number = validated_data.get('container_number', instance.container_number)
                instance.vehicle_number = validated_data.get('vehicle_number', instance.vehicle_number)
                instance.sj_number = validated_data.get('sj_number', instance.sj_number)
                instance.start_unload = validated_data.get('start_unload', instance.start_unload)
                instance.finish_load = validated_data.get('finish_load', instance.finish_load)
                instance.save()

                instance.items.all().delete()
                for item_data in items_data:
                    SPGItems.objects.create(spg=instance, **item_data)
                    Stock.objects.filter(
                        product=item_data['product'],
                        warehouse=instance.warehouse
                    ).update(
                        carton_quantity=F('carton_quantity') + item_data.get('carton_quantity', 0),
                        pack_quantity=F('pack_quantity') + item_data.get('pack_quantity', 0)
                    )

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
    user_email = serializers.CharField(source='user.email', read_only=True)
    source_warehouse_name = serializers.CharField(source='source_warehouse.name', read_only=True)
    destination_warehouse_name = serializers.CharField(source='destination_warehouse.name', read_only=True)

    class Meta:
        model = SuratTransferStok
        fields = [
            'id', 'document_number', 'source_warehouse', 'source_warehouse_name',
            'destination_warehouse', 'destination_warehouse_name', 'user', 'user_email',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'user', 'user_email',
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

        # Rule: Source and destination cannot be the same
        if source_warehouse == destination_warehouse:
            raise serializers.ValidationError("Source and destination warehouses cannot be the same.")

        # For updates, the instance is available in the context
        is_update = self.instance is not None

        for item_data in items:
            product = item_data['product']

            try:
                stock_at_source = Stock.objects.get(product=product, warehouse=source_warehouse)

                # On update, we can "use" the stock from the original transfer
                # before checking if the new amount is available.
                original_carton_qty = 0
                original_pack_qty = 0
                if is_update and self.instance.source_warehouse == source_warehouse:
                    original_item = self.instance.items.filter(product=product).first()
                    if original_item:
                        original_carton_qty = original_item.carton_quantity
                        original_pack_qty = original_item.pack_quantity

                # Check if available stock is sufficient for the new transfer amount
                if (stock_at_source.carton_quantity + original_carton_qty) < item_data.get('carton_quantity', 0):
                    raise serializers.ValidationError(f"Insufficient carton stock for {product.name} at {source_warehouse.name}.")
                if (stock_at_source.pack_quantity + original_pack_qty) < item_data.get('pack_quantity', 0):
                     raise serializers.ValidationError(f"Insufficient pack stock for {product.name} at {source_warehouse.name}.")

            except Stock.DoesNotExist:
                raise serializers.ValidationError(f"Stock record for {product.name} at {source_warehouse.name} not found.")

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            transfer = SuratTransferStok.objects.create(**validated_data)
            for item_data in items_data:
                SuratTransferStokItems.objects.create(surat_transfer_stok=transfer, **item_data)
                # Subtract from source
                Stock.objects.filter(product=item_data['product'], warehouse=transfer.source_warehouse).update(
                    carton_quantity=F('carton_quantity') - item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') - item_data.get('pack_quantity', 0)
                )
                # Add to destination
                Stock.objects.filter(product=item_data['product'], warehouse=transfer.destination_warehouse).update(
                    carton_quantity=F('carton_quantity') + item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') + item_data.get('pack_quantity', 0)
                )
        return transfer

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        new_source_warehouse = validated_data.get('source_warehouse', instance.source_warehouse)
        new_destination_warehouse = validated_data.get('destination_warehouse', instance.destination_warehouse)

        with transaction.atomic():
            for item in instance.items.all():
                # Add back to original source
                Stock.objects.filter(product=item.product, warehouse=instance.source_warehouse).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )
                # Remove from original destination
                Stock.objects.filter(product=item.product, warehouse=instance.destination_warehouse).update(
                    carton_quantity=F('carton_quantity') - item.carton_quantity,
                    pack_quantity=F('pack_quantity') - item.pack_quantity
                )

            for item_data in items_data:
                # Subtract from new source
                Stock.objects.filter(product=item_data['product'], warehouse=new_source_warehouse).update(
                    carton_quantity=F('carton_quantity') - item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') - item_data.get('pack_quantity', 0)
                )
                # Add to new destination
                Stock.objects.filter(product=item_data['product'], warehouse=new_destination_warehouse).update(
                    carton_quantity=F('carton_quantity') + item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') + item_data.get('pack_quantity', 0)
                )

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

    class Meta:
        model = SPKItems
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'carton_quantity', 'pack_quantity', 'packing', 'supplier_name'
        ]
        read_only_fields = ['id', 'product_name', 'product_code']


class SPKSerializer(serializers.ModelSerializer):
    items = SPKItemsSerializer(many=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_description = serializers.CharField(source='warehouse.description', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_address = serializers.CharField(source='customer.address', read_only=True)
    customer_upline = serializers.CharField(source='customer.upline', read_only=True)

    class Meta:
        model = SPK
        fields = [
            'id', 'document_number', 'warehouse', 'warehouse_name', 'warehouse_description',
            'customer', 'customer_name', 'customer_address', 'customer_upline', 'notes', 'user', 'user_email',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'user', 'user_email',
            'warehouse_name', 'customer_name', 'is_deleted',
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

    class Meta:
        model = SJItems
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'carton_quantity', 'pack_quantity'
        ]
        read_only_fields = ['id', 'product_name', 'product_code']


class SJSerializer(serializers.ModelSerializer):
    items = SJItemsSerializer(many=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_upline = serializers.CharField(source='customer.upline', read_only=True)
    spk_document_number = serializers.CharField(source='spk.document_number', read_only=True)

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
            'is_customer',
            'customer',
            'customer_name',
            'customer_upline',
            'non_customer_name',
            'vehicle_type',
            'vehicle_number',
            'notes',
            'user',
            'user_email',
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
            'user_email',
            'warehouse_name',
            'customer_name',
            'spk_document_number',
            'transaction_date',
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
        """
        # --- Customer and Non-Customer Validation ---
        is_customer = data.get('is_customer')
        if is_customer is None and self.instance:
            is_customer = self.instance.is_customer

        if is_customer:
            if not data.get('customer'):
                if not (self.instance and self.instance.customer):
                    raise serializers.ValidationError({"customer": "This field is required when is_customer is true."})
            data['non_customer_name'] = ""
        else:
            if not data.get('non_customer_name'):
                if not (self.instance and self.instance.non_customer_name):
                    raise serializers.ValidationError({"non_customer_name": "This field is required when is_customer is false."})
            data['customer'] = None

        # --- Stock Validation ---
        warehouse = data.get('warehouse') or (self.instance and self.instance.warehouse)
        items_data = data.get('items', [])
        is_update = self.instance is not None

        for item_data in items_data:
            product = item_data['product']
            try:
                stock = Stock.objects.get(product=product, warehouse=warehouse)

                original_carton = 0
                original_pack = 0
                if is_update:
                    original_item = self.instance.items.filter(product=product).first()
                    if original_item:
                        original_carton = original_item.carton_quantity
                        original_pack = original_item.pack_quantity

                if (stock.carton_quantity + original_carton) < item_data.get('carton_quantity', 0):
                    raise serializers.ValidationError(f"Insufficient carton stock for {product.name} at {warehouse.name}.")
                if (stock.pack_quantity + original_pack) < item_data.get('pack_quantity', 0):
                    raise serializers.ValidationError(f"Insufficient pack stock for {product.name} at {warehouse.name}.")

            except Stock.DoesNotExist:
                raise serializers.ValidationError(f"Stock record for {product.name} at {warehouse.name} not found.")

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            sj = SJ.objects.create(**validated_data)
            for item_data in items_data:
                SJItems.objects.create(sj=sj, **item_data)
                Stock.objects.filter(product=item_data['product'], warehouse=sj.warehouse).update(
                    carton_quantity=F('carton_quantity') - item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') - item_data.get('pack_quantity', 0)
                )
        return sj

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        # Get the new warehouse from the request, falling back to the instance's current warehouse if not provided.
        new_warehouse = validated_data.get('warehouse', instance.warehouse)

        with transaction.atomic():
            # --- Step 1: Revert the old stock from the OLD warehouse ---
            # This is critical. It adds the quantities back to the original source warehouse.
            for item in instance.items.all():
                Stock.objects.filter(
                    product=item.product,
                    warehouse=instance.warehouse  # Use the ORIGINAL warehouse here
                ).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )

            # --- Step 2: Apply the new stock to the NEW warehouse ---
            # This subtracts the new quantities from the potentially new warehouse.
            for item_data in items_data:
                 Stock.objects.filter(
                    product=item_data['product'],
                    warehouse=new_warehouse  # Use the NEW warehouse here
                ).update(
                    carton_quantity=F('carton_quantity') - item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') - item_data.get('pack_quantity', 0)
                )

            # --- Step 3: Update the SJ instance itself and its items ---
            # Remove read-only fields before calling super().update()
            validated_data.pop('transaction_date', None)
            instance = super().update(instance, validated_data) # This updates instance.warehouse to new_warehouse

            # Re-create the items for the updated SJ
            instance.items.all().delete()
            for item_data in items_data:
                SJItems.objects.create(sj=instance, **item_data)

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
    user_email = serializers.CharField(source='user.email', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = SuratLain
        fields = [
            'id', 'document_number', 'document_type', 'sj_number', 'warehouse',
            'warehouse_name', 'user', 'user_email', 'notes', 'is_deleted',
            'deleted_at', 'transaction_date', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'document_number', 'document_type', 'user', 'user_email',
            'warehouse_name', 'is_deleted', 'deleted_at',
            'transaction_date', 'created_at', 'updated_at'
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
            is_update = self.instance is not None

            for item_data in items_data:
                product = item_data['product']
                try:
                    stock = Stock.objects.get(product=product, warehouse=warehouse)

                    # On update, we can "use" the stock from the original document
                    # before checking if the new amount is available.
                    original_carton = 0
                    original_pack = 0
                    if is_update:
                        original_item = self.instance.items.filter(product=product).first()
                        if original_item:
                            original_carton = original_item.carton_quantity
                            original_pack = original_item.pack_quantity

                    # Check if available stock is sufficient for the new outgoing amount
                    if (stock.carton_quantity + original_carton) < item_data.get('carton_quantity', 0):
                        raise serializers.ValidationError(f"Insufficient carton stock for {product.name} at {warehouse.name}.")
                    if (stock.pack_quantity + original_pack) < item_data.get('pack_quantity', 0):
                        raise serializers.ValidationError(f"Insufficient pack stock for {product.name} at {warehouse.name}.")

                except Stock.DoesNotExist:
                    raise serializers.ValidationError(f"Stock record for {product.name} at {warehouse.name} not found.")

        # If all validation passes, return the data.
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        doc_type = self.context.get('document_type')

        with transaction.atomic():
            surat = SuratLain.objects.create(document_type=doc_type, **validated_data)
            for item_data in items_data:
                SuratLainItems.objects.create(surat_lain=surat, **item_data)

                # Conditionally add or subtract stock
                if doc_type in SuratLain.INCOMING_TYPES:
                    op = F('carton_quantity') + item_data.get('carton_quantity', 0)
                    pack_op = F('pack_quantity') + item_data.get('pack_quantity', 0)
                else: # Outgoing
                    op = F('carton_quantity') - item_data.get('carton_quantity', 0)
                    pack_op = F('pack_quantity') - item_data.get('pack_quantity', 0)

                Stock.objects.filter(product=item_data['product'], warehouse=surat.warehouse).update(
                    carton_quantity=op, pack_quantity=pack_op
                )
        return surat

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        new_warehouse = validated_data.get('warehouse', instance.warehouse)

        with transaction.atomic():
            # Revert old stock movements
            instance.soft_delete() # This flips is_deleted=True, so we must flip it back
            instance.is_deleted = False
            instance.deleted_at = None

            # Update the instance itself
            instance = super().update(instance, validated_data)

            # Apply new stock movements
            for item_data in items_data:
                if instance.document_type in SuratLain.INCOMING_TYPES:
                    op = F('carton_quantity') + item_data.get('carton_quantity', 0)
                    pack_op = F('pack_quantity') + item_data.get('pack_quantity', 0)
                else: # Outgoing
                    op = F('carton_quantity') - item_data.get('carton_quantity', 0)
                    pack_op = F('pack_quantity') - item_data.get('pack_quantity', 0)

                Stock.objects.filter(product=item_data['product'], warehouse=new_warehouse).update(
                    carton_quantity=op, pack_quantity=pack_op
                )

            # Re-create items and save the instance's final state
            instance.items.all().delete()
            for item_data in items_data:
                SuratLainItems.objects.create(surat_lain=instance, **item_data)
            instance.save()

        return instance

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
    transaction_date = serializers.DateTimeField(source='surat_transfer_stok.created_at', format="%Y-%m-%d")
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
