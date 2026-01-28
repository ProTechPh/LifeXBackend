# Products CRUD Backend - Setup Guide

## Quick Start Guide

This guide will help you set up and run the complete CRUD backend implementation.

## Prerequisites

- Python 3.10 or higher
- PostgreSQL (or SQLite for development)
- pip (Python package manager)
- Virtual environment tool (venv or virtualenv)

## Installation Steps

### 1. Verify Installation

The products app has already been added to your Django project. Verify it's in your settings:

```python
# lifex/settings/base.py
INSTALLED_APPS = [
    ...
    'products',  # ✓ Already added
]
```

### 2. Database Migrations

The migrations have already been created and applied. To verify:

```bash
# Check migration status
python manage.py showmigrations products

# You should see:
# products
#  [X] 0001_initial
```

If migrations are not applied, run:

```bash
python manage.py migrate products
```

### 3. Create Sample Data (Optional)

Create a superuser for admin access:

```bash
python manage.py createsuperuser
```

Create sample data using Django shell:

```bash
python manage.py shell
```

Then run:

```python
from products.models import Category, Product
from django.contrib.auth import get_user_model

User = get_user_model()

# Get or create admin user
admin = User.objects.filter(is_staff=True).first()

# Create categories
electronics = Category.objects.create(
    name="Electronics",
    slug="electronics",
    description="Electronic devices and accessories"
)

books = Category.objects.create(
    name="Books",
    slug="books",
    description="Books and publications"
)

# Create products
Product.objects.create(
    name="Wireless Mouse",
    description="Ergonomic wireless mouse with 2.4GHz connectivity",
    short_description="Comfortable wireless mouse",
    price="29.99",
    cost_price="15.00",
    stock_quantity=100,
    low_stock_threshold=10,
    sku="WM-001",
    barcode="1234567890123",
    weight="0.15",
    status="active",
    is_featured=True,
    is_active=True,
    category=electronics,
    created_by=admin
)

Product.objects.create(
    name="Mechanical Keyboard",
    description="RGB mechanical keyboard with blue switches",
    short_description="Gaming mechanical keyboard",
    price="89.99",
    cost_price="45.00",
    stock_quantity=50,
    low_stock_threshold=5,
    sku="KB-001",
    barcode="1234567890124",
    weight="0.85",
    status="active",
    is_featured=True,
    is_active=True,
    category=electronics,
    created_by=admin
)

Product.objects.create(
    name="Python Programming Book",
    description="Complete guide to Python programming",
    short_description="Learn Python from scratch",
    price="39.99",
    cost_price="20.00",
    stock_quantity=30,
    low_stock_threshold=10,
    sku="BK-001",
    barcode="1234567890125",
    weight="0.50",
    status="active",
    is_featured=False,
    is_active=True,
    category=books,
    created_by=admin
)

print("Sample data created successfully!")
```

### 4. Run the Development Server

```bash
python manage.py runserver
```

The server will start at: `http://localhost:8000`

### 5. Access the API

#### API Endpoints
- Products API: `http://localhost:8000/api/products/`
- Categories API: `http://localhost:8000/api/categories/`
- Reviews API: `http://localhost:8000/api/reviews/`

#### API Documentation
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

#### Django Admin
- Admin Panel: `http://localhost:8000/admin/`
- Login with your superuser credentials

## Testing the API

### 1. Using cURL

#### List all products
```bash
curl http://localhost:8000/api/products/
```

#### Get a specific product
```bash
curl http://localhost:8000/api/products/1/
```

#### Create a product (requires authentication)
First, get an authentication token:
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your_password"}'
```

Then use the token to create a product:
```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "USB Cable",
    "description": "High-speed USB-C cable",
    "price": "12.99",
    "stock_quantity": 200,
    "sku": "USB-001",
    "status": "active",
    "category_id": 1
  }'
```

#### Update a product
```bash
curl -X PATCH http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"price": "27.99", "stock_quantity": 75}'
```

#### Delete a product
```bash
curl -X DELETE http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 2. Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Login to get token
login_response = requests.post(
    f"{BASE_URL}/auth/login/",
    json={"email": "admin@example.com", "password": "your_password"}
)
token = login_response.json()["access"]

# Set headers with token
headers = {"Authorization": f"Bearer {token}"}

# List products
products = requests.get(f"{BASE_URL}/products/").json()
print(f"Total products: {products['count']}")

# Create a product
new_product = {
    "name": "HDMI Cable",
    "description": "4K HDMI cable",
    "price": "15.99",
    "stock_quantity": 150,
    "sku": "HDMI-001",
    "status": "active"
}
response = requests.post(f"{BASE_URL}/products/", json=new_product, headers=headers)
print(f"Created product: {response.json()['name']}")

# Update a product
update_data = {"price": "14.99"}
response = requests.patch(f"{BASE_URL}/products/1/", json=update_data, headers=headers)
print(f"Updated price: {response.json()['price']}")

# Delete a product
response = requests.delete(f"{BASE_URL}/products/1/", headers=headers)
print(f"Delete status: {response.status_code}")
```

### 3. Using Swagger UI

1. Navigate to `http://localhost:8000/api/schema/swagger-ui/`
2. Click "Authorize" button
3. Enter your JWT token: `Bearer YOUR_ACCESS_TOKEN`
4. Try out different endpoints interactively

## Running Tests

Run all tests for the products app:

```bash
# Run all product tests
python manage.py test products

# Run specific test class
python manage.py test products.tests.ProductAPITest

# Run with verbose output
python manage.py test products --verbosity=2

# Run with coverage (if coverage.py is installed)
coverage run --source='products' manage.py test products
coverage report
```

Expected output:
```
Creating test database...
...............................................................
----------------------------------------------------------------------
Ran 40+ tests in X.XXXs

OK
```

## API Usage Examples

### Example 1: E-commerce Product Catalog

```python
# List featured products
GET /api/products/?is_featured=true

# Search for products
GET /api/products/?search=mouse

# Filter by category and price range
GET /api/products/?category=1&min_price=20&max_price=50

# Get low stock products
GET /api/products/low_stock/
```

### Example 2: Inventory Management

```python
# Update stock for a product
PATCH /api/products/1/update_stock/
{
  "stock_quantity": 150
}

# Bulk update product status
POST /api/products/bulk_update/
{
  "product_ids": [1, 2, 3],
  "status": "active",
  "is_featured": true
}

# Get products by status
GET /api/products/?status=out_of_stock
```

### Example 3: Review Management

```python
# Create a review (authenticated user)
POST /api/reviews/
{
  "product": 1,
  "rating": 5,
  "title": "Excellent product!",
  "comment": "This product exceeded my expectations."
}

# Approve a review (admin only)
POST /api/reviews/1/approve/

# Get reviews for a product
GET /api/reviews/?product=1

# Filter by rating
GET /api/reviews/?rating=5
```

## Common Issues & Solutions

### Issue 1: Migration Errors

**Problem:** `django.db.migrations.exceptions.InconsistentMigrationHistory`

**Solution:**
```bash
# Reset migrations (development only!)
python manage.py migrate products zero
python manage.py migrate products
```

### Issue 2: Permission Denied

**Problem:** 403 Forbidden when creating/updating resources

**Solution:**
- Ensure you're authenticated with a valid JWT token
- Check if your user has admin privileges (is_staff=True)
- Verify the Authorization header format: `Bearer <token>`

### Issue 3: Validation Errors

**Problem:** 400 Bad Request with validation errors

**Solution:**
- Check required fields are provided
- Verify data types match model definitions
- Ensure unique constraints (SKU, slug) are not violated
- Review validation rules in serializers

### Issue 4: Token Expired

**Problem:** 401 Unauthorized with "Token is invalid or expired"

**Solution:**
```bash
# Refresh your token
POST /api/auth/token/refresh/
{
  "refresh": "YOUR_REFRESH_TOKEN"
}
```

## Environment Configuration

### Development Settings

The app uses the existing Django settings. Key configurations:

```python
# lifex/settings/base.py

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
```

### Database Configuration

The app works with any Django-supported database:

- **SQLite** (default for development)
- **PostgreSQL** (recommended for production)
- **MySQL**
- **Oracle**

## Production Deployment Checklist

- [ ] Set `DEBUG = False` in production settings
- [ ] Configure proper database (PostgreSQL recommended)
- [ ] Set up static file serving (WhiteNoise or CDN)
- [ ] Configure CORS for your frontend domain
- [ ] Enable HTTPS
- [ ] Set up proper logging
- [ ] Configure rate limiting
- [ ] Set up monitoring and error tracking
- [ ] Use environment variables for secrets
- [ ] Set up database backups
- [ ] Configure caching (Redis)

## Performance Optimization

### Database Optimization

```python
# Use select_related for foreign keys
products = Product.objects.select_related('category', 'created_by').all()

# Use prefetch_related for reverse foreign keys
categories = Category.objects.prefetch_related('products').all()

# Add database indexes (already configured in models)
```

### Caching

```python
# Add caching for frequently accessed data
from django.core.cache import cache

def get_featured_products():
    cache_key = 'featured_products'
    products = cache.get(cache_key)
    
    if products is None:
        products = Product.objects.filter(is_featured=True, is_active=True)
        cache.set(cache_key, products, 300)  # Cache for 5 minutes
    
    return products
```

## Next Steps

1. **Customize the models** to fit your specific requirements
2. **Add image upload** functionality for products
3. **Implement product variants** (size, color, etc.)
4. **Add inventory history** tracking
5. **Create analytics endpoints** for sales data
6. **Implement wishlist** functionality
7. **Add product comparison** feature
8. **Set up email notifications** for low stock
9. **Implement advanced search** with Elasticsearch
10. **Add API versioning**

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [JWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)

## Support

For detailed API documentation, visit:
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- Full documentation: `products/README.md`

## Summary

You now have a fully functional CRUD backend with:
- ✅ Complete CRUD operations for Categories, Products, and Reviews
- ✅ Advanced filtering, searching, and pagination
- ✅ JWT authentication and permission-based access control
- ✅ Comprehensive validation and error handling
- ✅ Admin interface for management
- ✅ API documentation with Swagger
- ✅ Test suite with 40+ test cases
- ✅ Production-ready architecture

Happy coding! 🚀
