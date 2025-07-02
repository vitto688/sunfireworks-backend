from sys import modules
from django.db.models.signals import post_save
from django.db.transaction import non_atomic_requests
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


class SPG(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('IMPORT', 'Import'),
        ('BAWANG', 'Bawang'),
        ('KAWAT', 'Kawat'),
        ('LAIN-LAIN', 'Lain-lain'),
    ]

    document_number = models.CharField(max_length=100, blank=True)
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPE_CHOICES)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    container_number = models.CharField(max_length=50)
    vehicle_number = models.CharField(max_length=50)
    sj_number = models.CharField(max_length=100)
    start_unload = models.CharField(max_length=50)
    finish_load = models.CharField(max_length=50)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.document_number:
            now = timezone.now()
            doc_type = self.document_type
            sequence = 1

            if doc_type == 'IMPORT':
                last_spg = SPG.objects.filter(
                    document_type=doc_type,
                    created_at__year=now.year
                ).order_by('document_number').last()

                if last_spg:
                    # Extract number from 'YY-XXX/KA'
                    last_seq = int(last_spg.document_number.split('/')[0].split('-')[1])
                    sequence = last_seq + 1

                self.document_number = f"{now.strftime('%y')}-{sequence:03d}/KA"

            else:
                last_spg = SPG.objects.filter(
                    document_type=doc_type,
                    created_at__year=now.year,
                    created_at__month=now.month
                ).order_by('document_number').last()

                if last_spg:
                    last_seq = int(last_spg.document_number.split('/')[-1])
                    sequence = last_seq +  1

                prefix = ""
                if doc_type == 'BAWANG':
                    prefix = f"{now.strftime('%Y-%m')}/SPG-B"
                elif doc_type == 'KAWAT':
                    prefix = f"{now.strftime('%Y-%m')}/SPG-K"
                elif doc_type == 'LAIN-LAIN':
                    prefix = f"{now.strftime('%Y-%m')}/SPG"

                self.document_number = f"{prefix}/{sequence:03d}"

        super().save(*args, **kwargs)


class SPGItems(models.Model):
    spg = models.ForeignKey(SPG, related_name='items', on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    packaging_size = models.CharField(max_length=50)
    inn = models.CharField(max_length=10)
    out = models.CharField(max_length=10)
    pjg = models.CharField(max_length=10)
    warehouse_size = models.CharField(max_length=50)
    packaging_weight = models.CharField(max_length=10)
    warehouse_weight = models.CharField(max_length=10)
    production_code = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SPK(models.Model):
    document_number = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class SPKItems(models.Model):
    sj = models.ForeignKey(SPK, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SJ(models.Model):
    document_number = models.CharField(max_length=100)
    spk = models.ForeignKey(SPK, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    vehicle_type = models.CharField(max_length=50)
    vehicle_number = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class SJItems(models.Model):
    sj = models.ForeignKey(SJ, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SuratLain(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('STB', 'STB'),
        ('SPB', 'SPB'),
        ('RETUR_PEMBELIAN', 'Retur Pembelian'),
    ]

    document_number = models.CharField(max_length=100)
    document_type = models.CharField(max_length=100, choices=DOCUMENT_TYPE_CHOICES)
    sj_number = models.CharField(max_length=100)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class SuratLainItems(models.Model):
    surat_lain = models.ForeignKey(SuratLain, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SuratTransferStok(models.Model):
    document_number = models.CharField(max_length=100)
    source_warehouse = models.ForeignKey(Warehouse, related_name='source_transfers', on_delete=models.PROTECT)
    destination_warehouse = models.ForeignKey(Warehouse, related_name='destination_transfers', on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class SuratTransferStokItems(models.Model):
    surat_transfer_stok = models.ForeignKey(SuratTransferStok, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@receiver(post_save, sender=Product)
def create_product_stocks(sender, instance, created, **kwargs):
    if created:
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
    if created:
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
