from rest_framework import serializers
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, SPG, SPGItems, SuratTransferStok, SuratTransferStokItems, SPK, SPKItems, SJ, SJItems, SuratLain, SuratLainItems, StockAdjustment, StockAdjustmentItem
from django.db import transaction
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.utils import timezone
import datetime


def _build_stock_map(warehouse, product_ids, lock=False):
    queryset = Stock.objects.filter(
        warehouse=warehouse,
        product_id__in=product_ids,
    )
    if lock:
        queryset = queryset.select_for_update()
    return {
        stock.product_id: stock
        for stock in queryset
    }


def _aggregate_item_totals(items_data):
    totals = {}
    for item_data in items_data:
        product = item_data['product']
        key = product.id

        if key not in totals:
            totals[key] = {
                'product': product,
                'carton_quantity': 0,
                'pack_quantity': 0,
            }

        totals[key]['carton_quantity'] += item_data.get('carton_quantity', 0)
        totals[key]['pack_quantity'] += item_data.get('pack_quantity', 0)

    return totals


def _aggregate_existing_item_totals(items):
    totals = {}
    for item in items:
        key = item.product_id

        if key not in totals:
            totals[key] = {
                'carton_quantity': 0,
                'pack_quantity': 0,
            }

        totals[key]['carton_quantity'] += item.carton_quantity
        totals[key]['pack_quantity'] += item.pack_quantity

    return totals


def _ensure_stock_deltas_fit(stock_map, stock_deltas):
    for (product_id, warehouse_id), delta in stock_deltas.items():
        if delta['carton_quantity'] >= 0 and delta['pack_quantity'] >= 0:
            continue

        stock = stock_map.get((product_id, warehouse_id))
        if stock is None:
            raise serializers.ValidationError(
                f"Stock record for product {product_id} at warehouse {warehouse_id} not found."
            )

        if (stock.carton_quantity + delta['carton_quantity']) < 0:
            raise serializers.ValidationError(
                f"Insufficient carton stock for product {product_id} at warehouse {warehouse_id}."
            )
        if (stock.pack_quantity + delta['pack_quantity']) < 0:
            raise serializers.ValidationError(
                f"Insufficient pack stock for product {product_id} at warehouse {warehouse_id}."
            )


def _build_locked_stock_map(stock_deltas):
    stock_keys = list(stock_deltas.keys())
    if not stock_keys:
        return {}

    product_ids = [key[0] for key in stock_keys]
    warehouse_ids = [key[1] for key in stock_keys]

    stocks = Stock.objects.filter(
        product_id__in=product_ids,
        warehouse_id__in=warehouse_ids,
    ).order_by('product_id', 'warehouse_id').select_for_update()
    return {
        (stock.product_id, stock.warehouse_id): stock
        for stock in stocks
    }


def _build_spk_fulfillment_map(spk, product_ids, exclude_sj_id=None):
    queryset = SJItems.objects.filter(
        sj__spk=spk,
        product_id__in=product_ids,
        sj__is_deleted=False,
    )
    if exclude_sj_id is not None:
        queryset = queryset.exclude(sj_id=exclude_sj_id)

    rows = queryset.values('product_id').annotate(
        carton_total=Coalesce(Sum('carton_quantity'), 0),
        pack_total=Coalesce(Sum('pack_quantity'), 0),
    )
    return {
        row['product_id']: row
        for row in rows
    }


def _build_spk_item_map(spk, product_ids):
    items = SPKItems.objects.filter(
        spk=spk,
        product_id__in=product_ids,
    )
    return {
        item.product_id: item
        for item in items
    }


def _apply_stock_deltas(deltas):
    for (product_id, warehouse_id), delta in deltas.items():
        Stock.objects.filter(product_id=product_id, warehouse_id=warehouse_id).update(
            carton_quantity=F('carton_quantity') + delta['carton_quantity'],
            pack_quantity=F('pack_quantity') + delta['pack_quantity'],
        )


def _merge_stock_delta(deltas, product_id, warehouse_id, carton_quantity, pack_quantity):
    key = (product_id, warehouse_id)
    if key not in deltas:
        deltas[key] = {'carton_quantity': 0, 'pack_quantity': 0}

    deltas[key]['carton_quantity'] += carton_quantity
    deltas[key]['pack_quantity'] += pack_quantity


class FlexDateTimeField(serializers.DateTimeField):
    """
    A custom DateTimeField that can accept a date-only string (YYYY-MM-DD)
    and automatically set the time to the beginning of the day (00:00:00).
    """
    def to_internal_value(self, value):
        try:
            date_obj = datetime.datetime.strptime(value, '%Y-%m-%d').date()
            datetime_obj = datetime.datetime.combine(date_obj, datetime.time.min)
            return timezone.make_aware(datetime_obj, timezone.get_current_timezone())
        except (ValueError, TypeError):
            return super().to_internal_value(value)


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
    product_category = serializers.CharField(source='product.category.name', read_only=True)
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
            'product_category',
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
        stocks = Stock.objects.filter(product=obj).select_related('warehouse')
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
