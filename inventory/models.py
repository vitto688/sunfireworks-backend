from sys import modules
from django.db.models.signals import post_save
from django.db.transaction import non_atomic_requests
from django.dispatch import receiver
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F

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
            last_spk = SPK.objects.filter(
                created_at__year=now.year,
                created_at__month=now.month
            ).order_by('document_number').last()

            sequence = 1
            if last_spk:
                last_seq = int(last_spk.document_number.split('/')[-1])
                sequence = last_seq + 1

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
    document_number = models.CharField(max_length=100, blank=True)
    spk = models.ForeignKey(SPK, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)

    is_customer = models.BooleanField(default=True)
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
        Override save to handle custom document number generation.
        """
        if not self.document_number:
            now = timezone.now()
            year = now.strftime('%Y')

            # Get the last SJ for the current year to determine the next sequence number
            last_sj = SJ.objects.filter(created_at__year=now.year).order_by('document_number').last()
            sequence = 1
            if last_sj:
                # Assumes the sequence number is always the last part after a '/'
                last_seq = int(last_sj.document_number.split('/')[-1])
                sequence = last_seq + 1

            # Determine the warehouse code
            warehouse_name = self.warehouse.name.upper()
            if 'ROYAL' in warehouse_name:
                warehouse_code = 'R'
            elif 'SALEM' in warehouse_name:
                warehouse_code = 'S'
            else:
                warehouse_code = 'O' # 'O' for Other

            # Generate the prefix based on whether it's for a customer
            if self.is_customer:
                # Format: YYYY/KA-W/XXX
                prefix = f"{year}/KA-{warehouse_code}"
            else:
                # Format: YYYY/KA-SJ-W/XXX
                prefix = f"{year}/KA-SJ-{warehouse_code}"

            self.document_number = f"{prefix}/{sequence:03d}"

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
            # (We would add a stock check here if needed, but typically restoring assumes it's valid)
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

            last_doc = SuratLain.objects.filter(
                document_type=self.document_type,
                created_at__year=now.year,
                created_at__month=now.month
            ).order_by('document_number').last()

            sequence = 1
            if last_doc:
                last_seq = int(last_doc.document_number.split('/')[-1])
                sequence = last_seq + 1

            doc_prefix_map = {
                'STB': 'STB',
                'SPB': 'SPB',
                'RETUR_PEMBELIAN': 'RPB',
                'RETUR_PENJUALAN': 'RPJ',
            }
            prefix = doc_prefix_map.get(self.document_type, 'SL')
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
            last_transfer = SuratTransferStok.objects.filter(
                created_at__year=now.year,
                created_at__month=now.month
            ).order_by('document_number').last()

            sequence = 1
            if last_transfer:
                last_seq = int(last_transfer.document_number.split('/')[-1])
                sequence = last_seq + 1

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
