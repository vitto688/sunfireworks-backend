from django.core.management.base import BaseCommand
from users.models import Role

class Command(BaseCommand):
    help = 'Create default roles'

    def handle(self, *args, **kwargs):
        roles = [
            {'name': Role.OWNER, 'description': 'Owner role with full access'},
            {'name': Role.FINANCE, 'description': 'Finance role for financial operations'},
            {'name': Role.WAREHOUSE, 'description': 'Warehouse role for inventory management'},
        ]

        for role_data in roles:
            Role.objects.get_or_create(
                name=role_data['name'],
                defaults={'description': role_data['description']}
            )

        self.stdout.write(self.style.SUCCESS('Successfully created roles'))
