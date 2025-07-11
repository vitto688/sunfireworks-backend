from rest_framework import serializers
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, SPG, SPGItems, SuratTransferStok, SuratTransferStokItems, SPK, SPKItems
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
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = SPK
        fields = [
            'id', 'document_number', 'warehouse', 'warehouse_name',
            'customer', 'customer_name', 'notes', 'user', 'user_email',
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
