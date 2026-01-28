from django.apps import AppConfig


class ProductsConfig(AppConfig):
    """
    Configuration for the Products app.
    Demonstrates complete CRUD operations with Django REST Framework.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Product Management'
