from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    SupplierViewSet,
    ProductViewSet,
    WarehouseViewSet,
    StockViewSet,
    CustomerViewSet,
    SPGViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'products', ProductViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'customers', CustomerViewSet)
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

urlpatterns = [
    path('', include(router.urls)),
    path('spg/<str:document_type>/', spg_list, name='spg-list'),
    path('spg/<str:document_type>/<int:pk>/', spg_detail, name='spg-detail'),
    path('spg/<str:document_type>/<int:pk>/restore/', spg_restore, name='spg-restore'),
]
