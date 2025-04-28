from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Category, Supplier, Product, Warehouse, Stock
from .serializers import (
    CategorySerializer,
    SupplierSerializer,
    ProductSerializer,
    ProductDetailSerializer,
    WarehouseSerializer,
    StockSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.filter(is_deleted=False)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get the requested view type from query parameters
        view_type = self.request.query_params.get('view', 'active')

        if view_type == 'all':
            return Supplier.objects.all()
        elif view_type == 'deleted':
            return Supplier.objects.filter(is_deleted=True)
        else:
            return Supplier.objects.filter(is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        supplier.soft_delete()
        return Response(
            {'message': f'Supplier {supplier.name} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, pk=None):
        try:
            supplier = Supplier.objects.get(pk=pk, is_deleted=True)
            supplier.restore()
            return Response(
                {'message': f'Supplier {supplier.name} has been restored'},
                status=status.HTTP_200_OK
            )
        except Supplier.DoesNotExist:
            return Response(
                {'error': 'Supplier not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_deleted=False)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        view_type = self.request.query_params.get('view', 'active')

        if view_type == 'all':
            return Product.objects.all()
        elif view_type == 'deleted':
            return Product.objects.filter(is_deleted=True)
        else:
            return Product.objects.filter(is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        product.soft_delete()
        return Response(
            {'message': f'Product {product.name} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk, is_deleted=True)
            product.restore()
            return Response(
                {'message': f'Product {product.name} has been restored'},
                status=status.HTTP_200_OK
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['GET'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if category_id:
            products = self.get_queryset().filter(category_id=category_id)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "category_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['GET'])
    def by_supplier(self, request):
        supplier_id = request.query_params.get('supplier_id')
        if supplier_id:
            products = self.get_queryset().filter(supplier_id=supplier_id)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "supplier_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'by_warehouse', 'by_product']:
            return [IsAuthenticated()]
        return [IsAdminUser()]  # For create, update, delete operations

    def get_queryset(self):
        # Only show stocks for non-deleted products
        return Stock.objects.filter(product__is_deleted=False)

    @action(detail=False, methods=['GET'])
    def by_warehouse(self, request):
        warehouse_id = request.query_params.get('warehouse_id')
        if warehouse_id:
            stocks = self.get_queryset().filter(warehouse_id=warehouse_id)
            serializer = self.get_serializer(stocks, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "warehouse_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['GET'])
    def by_product(self, request):
        product_id = request.query_params.get('product_id')
        if product_id:
            stocks = self.get_queryset().filter(product_id=product_id)
            serializer = self.get_serializer(stocks, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "product_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
