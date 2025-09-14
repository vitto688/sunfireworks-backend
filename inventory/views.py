from rest_framework import viewsets, status, serializers, generics, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Case, When, Value, IntegerField, Q, Sum, F
from django.db.models.functions import Lower
from .models import Category, Supplier, Product, Warehouse, Stock, Customer, SPG, SuratTransferStok, SPK, SJ, SuratLain, SuratTransferStokItems, SuratLainItems, StockAdjustment, SJItems, SPGItems
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
    SJSerializer,
    SuratLainSerializer,
    StockInfoReportSerializer,
    StockTransferReportSerializer,
    ReturnReportSerializer,
    DocumentSummaryReportSerializer,
    StockAdjustmentSerializer,
    StockReportSerializer,
)
from .filters import (
    StockInfoReportFilter,
    StockTransferReportFilter,
    ReturnReportFilter,
    SPGFilter,
    SPKFilter,
    SJFilter,
    SuratTransferStokFilter,
    SuratLainFilter,
    StockFilter,
    StockOutReportFilter,
    StockInReportFilter,
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

class StockViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Stock.objects.filter(product__is_deleted=False)
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = StockFilter

    def get_queryset(self):
        """
        Overrides the default queryset to apply a custom sort order.
        """
        # --- Custom Sort Logic ---
        category_order = Case(
            When(product__category__name='ROMAN CANDLE', then=Value(1)),
            When(product__category__name='SMALL ITEMS', then=Value(2)),
            When(product__category__name='CAKE', then=Value(3)),
            When(product__category__name='BAWANG', then=Value(4)),
            When(product__category__name='KAWAT', then=Value(5)),
            When(product__category__name='CAKE DISPLAY', then=Value(6)),
            When(product__category__name='SINGLE ROW', then=Value(7)),
            When(product__category__name='SINGLE SHOT', then=Value(8)),
            When(product__category__name='DAY FIREWORKS CAKE', then=Value(9)),
            When(product__category__name='DAY FIREWORKS SHELL', then=Value(10)),
            When(product__category__name='DISPLAY SHELL', then=Value(11)),
            When(product__category__name='LAIN LAIN', then=Value(12)),
            default=Value(12),
            output_field=IntegerField(),
        )

        queryset = Stock.objects.filter(product__is_deleted=False).annotate(
            category_order=category_order
        ).order_by('category_order', Lower('product__name'))

        return queryset

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


class OptionalPagination(CustomPagination):
    """
    A custom pagination class that allows disabling pagination via a query parameter.
    To disable pagination, add `?paginate=false` to the request URL.
    """
    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get('paginate', '').lower() == 'false':
            return None

        return super().paginate_queryset(queryset, request, view)


class SPGViewSet(viewsets.ModelViewSet):
    serializer_class = SPGSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = SPGFilter
    pagination_class = OptionalPagination

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
    filterset_class = SuratTransferStokFilter
    pagination_class = OptionalPagination

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
    filterset_class = SPKFilter
    pagination_class = OptionalPagination

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


class SJViewSet(viewsets.ModelViewSet):
    serializer_class = SJSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = SJFilter

    def get_queryset(self):
        queryset = SJ.objects.all()

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
        sj = self.get_object()
        sj.soft_delete()
        return Response(
            {'message': f'SJ document {sj.document_number} has been deleted'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['POST'])
    def restore(self, request, *args, **kwargs):
        sj = self.get_object()
        sj.restore()
        return Response(
            {'message': f'SJ document {sj.document_number} has been restored'},
            status=status.HTTP_200_OK
        )


class SuratLainViewSet(viewsets.ModelViewSet):
    serializer_class = SuratLainSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = SuratLainFilter
    pagination_class = OptionalPagination

    def get_queryset(self):
        """
        Gets the queryset for SuratLain, filtered by document type and view status.
        """
        doc_type_slug = self.kwargs.get('document_type_slug', '')

        # Corrected mapping from URL slug to the database value
        type_map = {
            'STB': 'STB',
            'SPB': 'SPB',
            'RETUR_PEMBELIAN': 'RETUR_PEMBELIAN',
            'RETUR_PENJUALAN': 'RETUR_PENJUALAN'
        }
        # Correctly transform the URL slug to match the map keys and model values
        lookup_key = doc_type_slug.upper().replace('-', '_')
        document_type = type_map.get(lookup_key)

        # If the slug from the URL is invalid, return an empty queryset
        if not document_type:
            return SuratLain.objects.none()

        # Start with the base queryset for the correct document type
        queryset = SuratLain.objects.filter(document_type=document_type)

        # For the 'restore' action, we must look in the deleted items
        if self.action == 'restore':
            return queryset.filter(is_deleted=True)

        # For all other actions, use the 'view' query parameter
        view_type = self.request.query_params.get('view', 'active')
        if view_type == 'deleted':
            return queryset.filter(is_deleted=True)
        elif view_type == 'all':
            return queryset

        # The default case for a standard GET request is to return active items
        return queryset.filter(is_deleted=False)

    def get_serializer_context(self):
        """
        Passes the correct document_type to the serializer for validation.
        """
        context = super().get_serializer_context()
        doc_type_slug = self.kwargs.get('document_type_slug', '')

        # Corrected mapping
        type_map = {
            'STB': 'STB',
            'SPB': 'SPB',
            'RETUR_PEMBELIAN': 'RETUR_PEMBELIAN',
            'RETUR_PENJUALAN': 'RETUR_PENJUALAN'
        }
        # Correctly transform the slug and pass the valid model value to the serializer
        lookup_key = doc_type_slug.upper().replace('-', '_')
        context['document_type'] = type_map.get(lookup_key)
        return context

    def perform_create(self, serializer):
        # This is correct. The document_type is handled in the serializer's create method.
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response({'message': f'Document {instance.document_number} has been deleted'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def restore(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.restore()
        return Response({'message': f'Document {instance.document_number} has been restored'}, status=status.HTTP_200_OK)


class StockInfoReportView(generics.ListAPIView):
    """
    Provides a report of all stock levels for all products in all warehouses.
    """
    serializer_class = StockInfoReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = StockInfoReportFilter

    def get_queryset(self):
        """
        Applies a custom sort order to the stock info report.
        """
        category_order = Case(
            When(product__category__name='ROMAN CANDLE', then=Value(1)),
            When(product__category__name='SMALL ITEMS', then=Value(2)),
            When(product__category__name='CAKE', then=Value(3)),
            When(product__category__name='BAWANG', then=Value(4)),
            When(product__category__name='KAWAT', then=Value(5)),
            When(product__category__name='CAKE DISPLAY', then=Value(6)),
            When(product__category__name='SINGLE ROW', then=Value(7)),
            When(product__category__name='SINGLE SHOT', then=Value(8)),
            When(product__category__name='DAY FIREWORKS CAKE', then=Value(9)),
            When(product__category__name='DAY FIREWORKS SHELL', then=Value(10)),
            When(product__category__name='DISPLAY SHELL', then=Value(11)),
            When(product__category__name='LAIN LAIN', then=Value(12)),
            default=Value(13),
            output_field=IntegerField(),
        )

        queryset = Stock.objects.filter(
            product__is_deleted=False
        ).filter(
            Q(carton_quantity__gt=0) | Q(pack_quantity__gt=0)
        ).annotate(
            category_order=category_order
        ).order_by('category_order', Lower('product__name'))

        return queryset


class StockTransferReportView(generics.ListAPIView):
    """
    Provides a summary report of all items in active (not deleted) stock transfers.
    """
    serializer_class = StockTransferReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = StockTransferReportFilter

    queryset = SuratTransferStokItems.objects.filter(surat_transfer_stok__is_deleted=False).order_by('-surat_transfer_stok__created_at')


class ReturPembelianReportView(generics.ListAPIView):
    serializer_class = DocumentSummaryReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = ReturnReportFilter
    queryset = SuratLainItems.objects.filter(
        surat_lain__document_type='RETUR_PEMBELIAN',
        surat_lain__is_deleted=False
    ).order_by('-surat_lain__transaction_date')

    def get_serializer_context(self):
        """Pass report_type to the serializer."""
        context = super().get_serializer_context()
        context['report_type'] = 'return'
        return context


class ReturPenjualanReportView(generics.ListAPIView):
    serializer_class = DocumentSummaryReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = ReturnReportFilter
    queryset = SuratLainItems.objects.filter(
        surat_lain__document_type='RETUR_PENJUALAN',
        surat_lain__is_deleted=False
    ).order_by('-surat_lain__transaction_date')

    def get_serializer_context(self):
        """Pass report_type to the serializer."""
        context = super().get_serializer_context()
        context['report_type'] = 'return'
        return context


class PenerimaanBarangReportView(generics.ListAPIView):
    serializer_class = DocumentSummaryReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = ReturnReportFilter
    queryset = SuratLainItems.objects.filter(
        surat_lain__document_type='STB',
        surat_lain__is_deleted=False
    ).order_by('-surat_lain__transaction_date')

    def get_serializer_context(self):
        """Pass report_type to the serializer."""
        context = super().get_serializer_context()
        context['report_type'] = 'document'
        return context


class PengeluaranBarangReportView(generics.ListAPIView):
    serializer_class = DocumentSummaryReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPagination
    filterset_class = ReturnReportFilter
    queryset = SuratLainItems.objects.filter(
        surat_lain__document_type='SPB',
        surat_lain__is_deleted=False
    ).order_by('-surat_lain__transaction_date')

    def get_serializer_context(self):
        """Pass report_type to the serializer."""
        context = super().get_serializer_context()
        context['report_type'] = 'document'
        return context


class StockAdjustmentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Handles the creation and viewing of Stock Adjustment documents.
    Updates and Deletes are not allowed to preserve the audit trail.
    """
    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    queryset = StockAdjustment.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StockOutReportView(generics.ListAPIView):
    """
    API view for the stock out report.
    """
    serializer_class = StockReportSerializer
    filterset_class = StockOutReportFilter
    pagination_class = OptionalPagination

    def get_queryset(self):
        """
        Aggregates the stock out data, excluding items from deleted SJ documents,
        and applies a custom sort order.
        """
        category_order = Case(
            When(product__category__name='ROMAN CANDLE', then=Value(1)),
            When(product__category__name='SMALL ITEMS', then=Value(2)),
            When(product__category__name='CAKE', then=Value(3)),
            When(product__category__name='BAWANG', then=Value(4)),
            When(product__category__name='KAWAT', then=Value(5)),
            When(product__category__name='CAKE DISPLAY', then=Value(6)),
            When(product__category__name='SINGLE ROW', then=Value(7)),
            When(product__category__name='SINGLE SHOT', then=Value(8)),
            When(product__category__name='DAY FIREWORKS CAKE', then=Value(9)),
            When(product__category__name='DAY FIREWORKS SHELL', then=Value(10)),
            When(product__category__name='DISPLAY SHELL', then=Value(11)),
            When(product__category__name='LAIN LAIN', then=Value(12)),
            default=Value(13), # Changed to 13 to avoid conflicts
            output_field=IntegerField(),
        )

        return SJItems.objects.filter(sj__is_deleted=False).annotate(
            product_code=F('product__code'),
            product_name=F('product__name'),
            packing=F('product__packing'),
            category_order=category_order # Add the custom order annotation
        ).values(
            'product_code', 'product_name', 'packing', 'category_order'
        ).annotate(
            total_carton_quantity=Sum('carton_quantity'),
            total_pack_quantity=Sum('pack_quantity')
        ).order_by('category_order', Lower('product__name'))


class StockInReportView(generics.ListAPIView):
    """
    API view for the stock in report.
    """
    serializer_class = StockReportSerializer
    filterset_class = StockInReportFilter
    pagination_class = OptionalPagination

    def get_queryset(self):
        """
        Aggregates the stock in data, excluding items from deleted SPG documents,
        and applies a custom sort order.
        """
        category_order = Case(
            When(product__category__name='ROMAN CANDLE', then=Value(1)),
            When(product__category__name='SMALL ITEMS', then=Value(2)),
            When(product__category__name='CAKE', then=Value(3)),
            When(product__category__name='BAWANG', then=Value(4)),
            When(product__category__name='KAWAT', then=Value(5)),
            When(product__category__name='CAKE DISPLAY', then=Value(6)),
            When(product__category__name='SINGLE ROW', then=Value(7)),
            When(product__category__name='SINGLE SHOT', then=Value(8)),
            When(product__category__name='DAY FIREWORKS CAKE', then=Value(9)),
            When(product__category__name='DAY FIREWORKS SHELL', then=Value(10)),
            When(product__category__name='DISPLAY SHELL', then=Value(11)),
            When(product__category__name='LAIN LAIN', then=Value(12)),
            default=Value(13), # Changed to 13 to avoid conflicts
            output_field=IntegerField(),
        )

        return SPGItems.objects.filter(spg__is_deleted=False).annotate(
            product_code=F('product__code'),
            product_name=F('product__name'),
            packing=F('product__packing'),
            category_order=category_order # Add the custom order annotation
        ).values(
            'product_code', 'product_name', 'packing', 'category_order'
        ).annotate(
            total_carton_quantity=Sum('carton_quantity'),
            total_pack_quantity=Sum('pack_quantity')
        ).order_by('category_order', Lower('product__name'))
