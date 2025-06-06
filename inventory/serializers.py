from rest_framework import serializers
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, Transaction

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

    class Meta:
        model = Stock
        fields = [
            'id',
            'product',
            'product_name',
            'product_code',
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


class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'document_number',
            'document_type',
            'transaction_type',
            'status',
            'customer',
            'customer_name',
            'product',
            'product_name',
            'product_code',
            'user',
            'user_email',
            'pack_quantity',
            'carton_quantity',
            'transaction_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'user',
            'transaction_date',
            'created_at',
            'updated_at'
        ]
