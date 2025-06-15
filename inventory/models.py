from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    address = models.TextField()
    pic_name = models.CharField(max_length=100)
    pic_contact = models.CharField(max_length=100)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class Product(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    supplier_price = models.DecimalField(max_digits=10, decimal_places=2)
    packing = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class Warehouse(models.Model):
    name = models.CharField(max_length=50, unique=True)  # G1, G2, GLB
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'warehouse']

    def __str__(self):
        return f"{self.product.name} at {self.warehouse.name}"


class Customer(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    contact_number = models.CharField(max_length=50)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ('PO', 'Purchase Order'),
        ('SO', 'Sales Order'),
        ('DO', 'Delivery Order'),
        ('GRN', 'Goods Received Note'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    document_number = models.CharField(max_length=100)
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPE_CHOICES)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    pack_quantity = models.IntegerField(default=0)
    carton_quantity = models.IntegerField(default=0)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_number} - {self.customer.name} - {self.product.name}"

    class Meta:
        ordering = ['-created_at']

@receiver(post_save, sender=Product)
def create_product_stocks(sender, instance, created, **kwargs):
    if created:  # Only when a new product is created
        # Create stock records for all warehouses
        warehouses = Warehouse.objects.all()
        stock_objects = [
            Stock(
                product=instance,
                warehouse=warehouse,
                carton_quantity=0,
                pack_quantity=0
            )
            for warehouse in warehouses
        ]
        Stock.objects.bulk_create(stock_objects)

@receiver(post_save, sender=Warehouse)
def create_warehouse_stocks(sender, instance, created, **kwargs):
    if created:  # Only when a new warehouse is created
        # Create stock records for all products
        products = Product.objects.filter(is_deleted=False)
        stock_objects = [
            Stock(
                product=product,
                warehouse=instance,
                carton_quantity=0,
                pack_quantity=0
            )
            for product in products
        ]
        Stock.objects.bulk_create(stock_objects)
