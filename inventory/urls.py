from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    SupplierViewSet,
    ProductViewSet,
    WarehouseViewSet,
    StockViewSet,
    CustomerViewSet,
    SPGViewSet,
    SuratTransferStokViewSet,
    SPKViewSet,
    SJViewSet,
    SuratLainViewSet,
    StockInfoReportView,
    StockTransferReportView,
    ReturPenjualanReportView,
    ReturPembelianReportView,
    PenerimaanBarangReportView,
    PengeluaranBarangReportView,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'products', ProductViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'stock-transfers', SuratTransferStokViewSet, basename='stock-transfer')
router.register(r'spk', SPKViewSet, basename='spk')
router.register(r'sj', SJViewSet, basename='sj')
spg_list = SPGViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
spg_detail = SPGViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
spg_restore = SPGViewSet.as_view({
    'post': 'restore'
})

surat_lain_list = SuratLainViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
surat_lain_detail = SuratLainViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
surat_lain_restore = SuratLainViewSet.as_view({
    'post': 'restore'
})

urlpatterns = [
    path('', include(router.urls)),
    path('spg/<str:document_type>/', spg_list, name='spg-list'),
    path('spg/<str:document_type>/<int:pk>/', spg_detail, name='spg-detail'),
    path('spg/<str:document_type>/<int:pk>/restore/', spg_restore, name='spg-restore'),
    path('<str:document_type_slug>/', surat_lain_list, name='surat-lain-list'),
    path('<str:document_type_slug>/<int:pk>/', surat_lain_detail, name='surat-lain-detail'),
    path('<str:document_type_slug>/<int:pk>/restore/', surat_lain_restore, name='surat-lain-restore'),
    path('report/stock-info/', StockInfoReportView.as_view(), name='report-stock-info'),
    path('report/stock-transfer/', StockTransferReportView.as_view(), name='report-stock-transfer'),
    path('report/retur-pembelian/', ReturPembelianReportView.as_view(), name='report-retur-pembelian'),
    path('report/retur-penjualan/', ReturPenjualanReportView.as_view(), name='report-retur-penjualan'),
    path('report/penerimaan-barang/', PenerimaanBarangReportView.as_view(), name='report-penerimaan-barang'),
    path('report/pengeluaran-barang/', PengeluaranBarangReportView.as_view(), name='report-pengeluaran-barang'),
]
