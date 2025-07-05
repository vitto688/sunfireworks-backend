from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, SPG, SuratTransferStok, SPK
from .serializers import (
    CategorySerializer,
    SupplierSerializer,
    ProductSerializer,
    ProductDetailSerializer,
    WarehouseSerializer,
    StockSerializer,
    CustomerSerializer,
    SPGSerializer,
    SuratTransferStokSerializer,
    SPKSerializer,
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


class SPGViewSet(viewsets.ModelViewSet):
    serializer_class = SPGSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        document_type = self.kwargs.get('document_type', '').upper()
        if document_type not in [choice[0] for choice in SPG.DOCUMENT_TYPE_CHOICES]:
            return SPG.objects.none()

        queryset = SPG.objects.filter(document_type=document_type)

        if self.action == 'restore':
            return queryset.filter(is_deleted=True)

        view_type = self.request.query_params.get('view', 'active')
        if view_type == 'deleted':
            return queryset.filter(is_deleted=True)
        elif view_type == 'all':
            return queryset
        return queryset.filter(is_deleted=False)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['document_type'] = self.kwargs.get('document_type', '').upper()
        return context

    def perform_create(self, serializer):
        document_type = self.kwargs.get('document_type', '').upper()

        if document_type not in [choice[0] for choice in SPG.DOCUMENT_TYPE_CHOICES]:
            raise serializers.ValidationError(f"Invalid document_type: {document_type}")

        serializer.save(user=self.request.user, document_type=document_type)

    def destroy(self, request, *args, **kwargs):
        spg = self.get_object()
        spg.soft_delete()
        return Response(
            {'message': f'SPG document {spg.document_number} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, *args, **kwargs):
        spg = self.get_object()
        spg.restore()
        return Response(
            {'message': f'SPG document {spg.document_number} has been restored'},
            status=status.HTTP_200_OK
        )


class SuratTransferStokViewSet(viewsets.ModelViewSet):
    serializer_class = SuratTransferStokSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = SuratTransferStok.objects.all()

        if self.action == 'restore':
            return queryset.filter(is_deleted=True)

        view_type = self.request.query_params.get('view', 'active')
        if view_type == 'deleted':
            return queryset.filter(is_deleted=True)
        elif view_type == 'all':
            return queryset
        return queryset.filter(is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        transfer = self.get_object()
        transfer.soft_delete()
        return Response(
            {'message': f'Transfer document {transfer.document_number} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, *args, **kwargs):
        transfer = self.get_object()
        transfer.restore()
        return Response(
            {'message': f'Transfer document {transfer.document_number} has been restored'},
            status=status.HTTP_200_OK
        )


class SPKViewSet(viewsets.ModelViewSet):
    serializer_class = SPKSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = SPK.objects.all()

        if self.action == 'restore':
            return queryset.filter(is_deleted=True)

        view_type = self.request.query_params.get('view', 'active')
        if view_type == 'deleted':
            return queryset.filter(is_deleted=True)
        elif view_type == 'all':
            return queryset
        return queryset.filter(is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        spk = self.get_object()
        spk.soft_delete()
        return Response(
            {'message': f'SPK document {spk.document_number} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, *args, **kwargs):
        spk = self.get_object()
        spk.restore()
        return Response(
            {'message': f'SPK document {spk.document_number} has been restored'},
            status=status.HTTP_200_OK
        )
