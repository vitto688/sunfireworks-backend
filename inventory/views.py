from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, Transaction
from .serializers import (
    CategorySerializer,
    SupplierSerializer,
    ProductSerializer,
    ProductDetailSerializer,
    WarehouseSerializer,
    StockSerializer,
    CustomerSerializer,
    TransactionSerializer,
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
    queryset = Stock.objects.filter(product__is_deleted=False)
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only show stocks for non-deleted products
        return Stock.objects.filter(product__is_deleted=False)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'by_warehouse', 'by_product']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @action(detail=False, methods=['GET'])
    def by_warehouse(self, request):
        warehouse_id = request.query_params.get('warehouse_id')
        if warehouse_id:
            # Add filter for non-deleted products
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
            # First check if product exists and is not deleted
            try:
                product = Product.objects.get(id=product_id, is_deleted=False)
            except Product.DoesNotExist:
                return Response(
                    {"error": "Product not found or is deleted"},
                    status=status.HTTP_404_NOT_FOUND
                )

            stocks = self.get_queryset().filter(product_id=product_id)
            serializer = self.get_serializer(stocks, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "product_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, *args, **kwargs):
        stock = self.get_object()
        if stock.product.is_deleted:
            return Response(
                {"error": "Cannot update stock for deleted product"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        stock = self.get_object()
        if stock.product.is_deleted:
            return Response(
                {"error": "Cannot update stock for deleted product"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().partial_update(request, *args, **kwargs)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_deleted=False)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        view_type = self.request.query_params.get('view', 'active')

        if view_type == 'all':
            return Customer.objects.all()
        elif view_type == 'deleted':
            return Customer.objects.filter(is_deleted=True)
        else:
            return Customer.objects.filter(is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        customer.soft_delete()
        return Response(
            {'message': f'Customer {customer.name} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, pk=None):
        try:
            customer = Customer.objects.get(pk=pk, is_deleted=True)
            customer.restore()
            return Response(
                {'message': f'Customer {customer.name} has been restored'},
                status=status.HTTP_200_OK
            )
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = Transaction.objects.all().order_by('-created_at')

        # Filter by transaction type
        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by customer
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        # Filter by document type
        document_type = self.request.query_params.get('document_type')
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(transaction_date__date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(transaction_date__date__lte=date_to)
            except ValueError:
                pass

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(document_number__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(product__name__icontains=search)
            )

        return queryset
