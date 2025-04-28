from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    SupplierViewSet,
    ProductViewSet,
    WarehouseViewSet,
    StockViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'products', ProductViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'stocks', StockViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
