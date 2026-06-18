from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F


class DocumentSequence(models.Model):
    family = models.CharField(max_length=50)
    period_key = models.CharField(max_length=20)
    current_value = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['family', 'period_key'],
                name='unique_document_sequence_family_period',
            )
        ]


def _next_document_sequence(family, period_key):
    with transaction.atomic():
        sequence, created = DocumentSequence.objects.select_for_update().get_or_create(
            family=family,
            period_key=period_key,
            defaults={'current_value': 0},
        )
        sequence.current_value += 1
        sequence.save(update_fields=['current_value', 'updated_at'])
        return sequence.current_value

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort_order = models.PositiveIntegerField(default=99, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

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
    code = models.CharField(max_length=50)
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
    upline = models.CharField(max_length=200, null=True, blank=True)
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
    notes = models.TextField(null=True, blank=True)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    transaction_date = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def soft_delete(self):
        """
        Marks the SPG as deleted and reverts the stock additions.
        """
        with transaction.atomic():
            for item in self.items.all():
                Stock.objects.filter(
                    product=item.product,
                    warehouse=self.warehouse
                ).update(
                    carton_quantity=F('carton_quantity') - item.carton_quantity,
                    pack_quantity=F('pack_quantity') - item.pack_quantity
                )
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save()

    def restore(self):
        """
        Restores a soft-deleted SPG and re-applies the stock additions.
        """
        with transaction.atomic():
            for item in self.items.all():
                Stock.objects.filter(
                    product=item.product,
                    warehouse=self.warehouse
                ).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )
            self.is_deleted = False
            self.deleted_at = None
            self.save()

    def save(self, *args, **kwargs):
        if not self.document_number:
            now = timezone.now()
            doc_type = self.document_type

            if doc_type == 'IMPORT':
                sequence = _next_document_sequence('SPG:IMPORT', str(now.year))
                self.document_number = f"{now.strftime('%y')}-{sequence:03d}/KA"

            else:
                prefix = ""
                if doc_type == 'BAWANG':
                    prefix = f"{now.strftime('%Y-%m')}/SPG-B"
                elif doc_type == 'KAWAT':
                    prefix = f"{now.strftime('%Y-%m')}/SPG-K"
                elif doc_type == 'LAIN-LAIN':
                    prefix = f"{now.strftime('%Y-%m')}/SPG"

                sequence = _next_document_sequence(f'SPG:{doc_type}', now.strftime('%Y-%m'))
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
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.document_number:
            now = timezone.now()
            sequence = _next_document_sequence('SPK', now.strftime('%Y-%m'))
            self.document_number = f"{now.strftime('%Y-%m')}/SPK/{sequence:03d}"

        super().save(*args, **kwargs)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class SPKItems(models.Model):
    spk = models.ForeignKey(SPK,  related_name='items', on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SJ(models.Model):
    SJ_TYPE_CHOICES = [
        ('KA', 'KA'),
        ('KA-SJ', 'KA-SJ'),
        ('SO/B', 'SO/B'),
        ('SO/K', 'SO/K'),
        ('P-B', 'P-B'),
        ('P-K', 'P-K'),
    ]

    document_number = models.CharField(max_length=100, blank=True)

    sequence_number = models.PositiveIntegerField(editable=False, db_index=True, null=True)

    spk = models.ForeignKey(SPK, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)

    sj_type = models.CharField(max_length=10, choices=SJ_TYPE_CHOICES)

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True)
    non_customer_name = models.CharField(max_length=200, blank=True)

    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    vehicle_type = models.CharField(max_length=50)
    vehicle_number = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)

    transaction_date = models.DateTimeField(default=timezone.now)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """
        Generates a document number based on a yearly resetting sequence.
        """
        if not self.pk: # Check if the object is new
            now = timezone.now()
            year = now.strftime('%Y')
            month_year = now.strftime('%m%Y')
            self.sequence_number = _next_document_sequence('SJ', str(now.year))
            sequence_str = f"{self.sequence_number:03d}"

            if self.sj_type in ['KA', 'KA-SJ']:
                warehouse_name = self.warehouse.name.upper()
                warehouse_code = 'O'
                if 'ROYAL' in warehouse_name: warehouse_code = 'R'
                elif 'SALEM' in warehouse_name: warehouse_code = 'S'

                if self.sj_type == 'KA': self.document_number = f"{year}/KA-{warehouse_code}/{sequence_str}"
                elif self.sj_type == 'KA-SJ': self.document_number = f"{year}/KA-SJ-{warehouse_code}/{sequence_str}"

            elif self.sj_type in ['SO/B', 'SO/K', 'P-B', 'P-K']:
                if self.sj_type in ['SO/B', 'SO/K']: self.document_number = f"{sequence_str}-{self.sj_type}/{month_year}"
                elif self.sj_type in ['P-B', 'P-K']: self.document_number = f"{sequence_str}/{self.sj_type}/{month_year}"

        super().save(*args, **kwargs)

    def soft_delete(self):
        """
        Marks the SJ as deleted and ADDS the stock back to the warehouse.
        """
        with transaction.atomic():
            for item in self.items.all():
                Stock.objects.filter(product=item.product, warehouse=self.warehouse).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save()

    def restore(self):
        """
        Restores a soft-deleted SJ and SUBTRACTS the stock from the warehouse again.
        """
        with transaction.atomic():
            for item in self.items.all():
                Stock.objects.filter(product=item.product, warehouse=self.warehouse).update(
                    carton_quantity=F('carton_quantity') - item.carton_quantity,
                    pack_quantity=F('pack_quantity') - item.pack_quantity
                )
            self.is_deleted = False
            self.deleted_at = None
            self.save()


class SJItems(models.Model):
    sj = models.ForeignKey(SJ, related_name='items', on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    carton_quantity = models.IntegerField(default=0)
    pack_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SuratLain(models.Model):
    # Expanded document type choices
    DOCUMENT_TYPE_CHOICES = [
        ('STB', 'STB'),
        ('SPB', 'SPB'),
        ('RETUR_PEMBELIAN', 'Retur Pembelian'),
        ('RETUR_PENJUALAN', 'Retur Penjualan'), # Added new type
    ]
    # Define which types are for incoming stock
    INCOMING_TYPES = ['STB', 'RETUR_PENJUALAN']

    document_number = models.CharField(max_length=100, blank=True)
    document_type = models.CharField(max_length=100, choices=DOCUMENT_TYPE_CHOICES)
    sj_number = models.CharField(max_length=100, blank=True) # Make optional
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)

    # Add soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    transaction_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.document_number:
            now = timezone.now()
            year_month = now.strftime('%Y-%m')
            doc_prefix_map = {
                'STB': 'STB',
                'SPB': 'SPB',
                'RETUR_PEMBELIAN': 'RPB',
                'RETUR_PENJUALAN': 'RPJ',
            }
            prefix = doc_prefix_map.get(self.document_type, 'SL')
            sequence = _next_document_sequence(f'SURAT_LAIN:{self.document_type}', year_month)
            self.document_number = f"{year_month}/{prefix}/{sequence:03d}"

        super().save(*args, **kwargs)

    def soft_delete(self):
        with transaction.atomic():
            for item in self.items.all():
                # If it was an incoming type, deleting it subtracts stock.
                if self.document_type in self.INCOMING_TYPES:
                    Stock.objects.filter(product=item.product, warehouse=self.warehouse).update(
                        carton_quantity=F('carton_quantity') - item.carton_quantity,
                        pack_quantity=F('pack_quantity') - item.pack_quantity
                    )
                # If it was an outgoing type, deleting it adds stock back.
                else:
                    Stock.objects.filter(product=item.product, warehouse=self.warehouse).update(
                        carton_quantity=F('carton_quantity') + item.carton_quantity,
                        pack_quantity=F('pack_quantity') + item.pack_quantity
                    )
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save()

    def restore(self):
        with transaction.atomic():
            for item in self.items.all():
                # Re-apply the original transaction
                if self.document_type in self.INCOMING_TYPES:
                    Stock.objects.filter(product=item.product, warehouse=self.warehouse).update(
                        carton_quantity=F('carton_quantity') + item.carton_quantity,
                        pack_quantity=F('pack_quantity') + item.pack_quantity
                    )
                else: # Outgoing
                    Stock.objects.filter(product=item.product, warehouse=self.warehouse).update(
                        carton_quantity=F('carton_quantity') - item.carton_quantity,
                        pack_quantity=F('pack_quantity') - item.pack_quantity
                    )
            self.is_deleted = False
            self.deleted_at = None
            self.save()

class SuratLainItems(models.Model):
    surat_lain = models.ForeignKey(SuratLain, related_name='items', on_delete=models.PROTECT)
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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')
        # Get the new warehouses from the request, falling back to the instance's values if not provided.
        new_source_warehouse = validated_data.get('source_warehouse', instance.source_warehouse)
        new_destination_warehouse = validated_data.get('destination_warehouse', instance.destination_warehouse)

        with transaction.atomic():
            # --- Step 1: Revert the original stock transfer ---
            # This moves stock from the original destination back to the original source.
            for item in instance.items.all():
                # Add stock back to the ORIGINAL source warehouse
                Stock.objects.filter(
                    product=item.product,
                    warehouse=instance.source_warehouse
                ).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )
                # Remove stock from the ORIGINAL destination warehouse
                Stock.objects.filter(
                    product=item.product,
                    warehouse=instance.destination_warehouse
                ).update(
                    carton_quantity=F('carton_quantity') - item.carton_quantity,
                    pack_quantity=F('pack_quantity') - item.pack_quantity
                )

            # --- Step 2: Apply the new stock transfer ---
            # This moves stock from the NEW source to the NEW destination.
            for item_data in items_data:
                # Subtract stock from the NEW source warehouse
                Stock.objects.filter(
                    product=item_data['product'],
                    warehouse=new_source_warehouse
                ).update(
                    carton_quantity=F('carton_quantity') - item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') - item_data.get('pack_quantity', 0)
                )
                # Add stock to the NEW destination warehouse
                Stock.objects.filter(
                    product=item_data['product'],
                    warehouse=new_destination_warehouse
                ).update(
                    carton_quantity=F('carton_quantity') + item_data.get('carton_quantity', 0),
                    pack_quantity=F('pack_quantity') + item_data.get('pack_quantity', 0)
                )

            # --- Step 3: Update the transfer document itself and its items ---
            # Remove read-only fields before calling super().update()
            validated_data.pop('transaction_date', None)
            instance = super().update(instance, validated_data) # This updates the instance's warehouses to the new ones

            # Re-create the items for the updated transfer document
            instance.items.all().delete()
            for item_data in items_data:
                SuratTransferStokItems.objects.create(surat_transfer_stok=instance, **item_data)

        return instance

    def save(self, *args, **kwargs):
        if not self.document_number:
            now = timezone.now()
            sequence = _next_document_sequence('SURAT_TRANSFER_STOK', now.strftime('%Y-%m'))
            self.document_number = f"{now.strftime('%Y')}/TRS/{sequence:03d}"

        super().save(*args, **kwargs)

    def soft_delete(self):
        """
        Marks the transfer as deleted and reverts the stock transfer.
        (Adds stock back to source, removes from destination)
        """
        with transaction.atomic():
            for item in self.surattransferstokitems_set.all():
                # Add back to source
                Stock.objects.filter(product=item.product, warehouse=self.source_warehouse).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )
                # Remove from destination
                Stock.objects.filter(product=item.product, warehouse=self.destination_warehouse).update(
                    carton_quantity=F('carton_quantity') - item.carton_quantity,
                    pack_quantity=F('pack_quantity') - item.pack_quantity
                )
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save()

    def restore(self):
        """
        Restores a soft-deleted transfer and re-applies the stock transfer.
        (Removes stock from source, adds to destination)
        """
        with transaction.atomic():
            for item in self.surattransferstokitems_set.all():
                # Remove from source
                Stock.objects.filter(product=item.product, warehouse=self.source_warehouse).update(
                    carton_quantity=F('carton_quantity') - item.carton_quantity,
                    pack_quantity=F('pack_quantity') - item.pack_quantity
                )
                # Add to destination
                Stock.objects.filter(product=item.product, warehouse=self.destination_warehouse).update(
                    carton_quantity=F('carton_quantity') + item.carton_quantity,
                    pack_quantity=F('pack_quantity') + item.pack_quantity
                )
            self.is_deleted = False
            self.deleted_at = None
            self.save()

class SuratTransferStokItems(models.Model):
    surat_transfer_stok = models.ForeignKey(SuratTransferStok, related_name='items', on_delete=models.PROTECT)
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


class StockAdjustment(models.Model):
    document_number = models.CharField(max_length=100, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    reason = models.TextField()
    transaction_date = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.document_number:
            now = timezone.now()
            sequence = _next_document_sequence('STOCK_ADJUSTMENT', now.strftime('%Y-%m'))
            self.document_number = f"{now.strftime('%Y-%m')}/SA/{sequence:03d}"

        super().save(*args, **kwargs)


class StockAdjustmentItem(models.Model):
    stock_adjustment = models.ForeignKey(StockAdjustment, related_name='items', on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    old_carton_quantity = models.IntegerField()
    old_pack_quantity = models.IntegerField()
    new_carton_quantity = models.IntegerField()
    new_pack_quantity = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
