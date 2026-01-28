# Products CRUD API - Complete Implementation Guide

## Overview

This is a complete RESTful CRUD (Create, Read, Update, Delete) backend implementation using Django REST Framework. The implementation demonstrates best practices for building scalable, secure, and maintainable APIs.

## Technology Stack

- **Framework**: Django 6.0 + Django REST Framework
- **Database**: PostgreSQL (configurable for MySQL, SQLite)
- **Authentication**: JWT (JSON Web Tokens) via SimpleJWT
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Language**: Python 3.10+

## Features

### 1. Complete CRUD Operations
- **Create**: POST endpoints with validation
- **Read**: GET endpoints with filtering, searching, and pagination
- **Update**: PUT/PATCH endpoints with partial updates
- **Delete**: DELETE endpoints with soft delete options

### 2. Three Resource Types
- **Categories**: Product categorization
- **Products**: Main product management
- **Reviews**: User-generated product reviews

### 3. Advanced Features
- Field-level validation with custom validators
- Cross-field validation
- Relationship management (One-to-Many, Many-to-One)
- Computed properties (profit margin, stock status)
- Bulk operations
- Custom actions (approve reviews, update stock)
- Advanced filtering and search
- Permission-based access control
- Comprehensive error handling

## Database Schema

### Category Model
```
- id (Primary Key)
- name (CharField, unique)
- description (TextField, optional)
- slug (SlugField, unique)
- is_active (Boolean)
- created_at (DateTime)
- updated_at (DateTime)
```

### Product Model
```
- id (Primary Key)
- name (CharField)
- description (TextField)
- short_description (CharField, optional)
- price (Decimal, validated > 0)
- cost_price (Decimal, optional)
- stock_quantity (Integer, validated >= 0)
- low_stock_threshold (Integer)
- sku (CharField, unique)
- barcode (CharField, optional)
- weight (Decimal, optional)
- status (Choice: draft, active, discontinued, out_of_stock)
- is_featured (Boolean)
- is_active (Boolean)
- category (ForeignKey to Category)
- created_by (ForeignKey to User)
- created_at (DateTime)
- updated_at (DateTime)
```

### ProductReview Model
```
- id (Primary Key)
- product (ForeignKey to Product)
- user (ForeignKey to User)
- rating (Integer, 1-5)
- title (CharField)
- comment (TextField)
- is_verified_purchase (Boolean)
- is_approved (Boolean)
- created_at (DateTime)
- updated_at (DateTime)
- Unique constraint: (product, user)
```

## Installation & Setup

### 1. Install Dependencies
```bash
# Already included in requirements.txt
pip install djangorestframework
pip install djangorestframework-simplejwt
pip install drf-spectacular
pip install django-cors-headers
```

### 2. Run Migrations
```bash
# Create migration files
python manage.py makemigrations products

# Apply migrations to database
python manage.py migrate products
```

### 3. Create Superuser (for admin access)
```bash
python manage.py createsuperuser
```

### 4. Run Development Server
```bash
python manage.py runserver
```

## API Endpoints

### Base URL
```
http://localhost:8000/api/
```

### Categories

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/categories/` | List all categories | No |
| POST | `/categories/` | Create category | Admin |
| GET | `/categories/{id}/` | Get category details | No |
| PUT | `/categories/{id}/` | Update category | Admin |
| PATCH | `/categories/{id}/` | Partial update | Admin |
| DELETE | `/categories/{id}/` | Delete category | Admin |

**Query Parameters:**
- `?is_active=true` - Filter by active status
- `?search=keyword` - Search in name/description
- `?ordering=name` - Order results

### Products

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/products/` | List all products | No |
| POST | `/products/` | Create product | Admin |
| GET | `/products/{id}/` | Get product details | No |
| PUT | `/products/{id}/` | Update product | Admin |
| PATCH | `/products/{id}/` | Partial update | Admin |
| DELETE | `/products/{id}/` | Delete product | Admin |
| GET | `/products/low_stock/` | Get low stock products | No |
| POST | `/products/bulk_update/` | Bulk update products | Admin |
| PATCH | `/products/{id}/update_stock/` | Update stock | Admin |

**Query Parameters:**
- `?category=1` - Filter by category ID
- `?status=active` - Filter by status
- `?is_featured=true` - Filter featured products
- `?min_price=10&max_price=100` - Price range
- `?low_stock=true` - Show low stock items
- `?search=keyword` - Search in name/description/SKU
- `?ordering=-created_at` - Order results

### Reviews

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/reviews/` | List reviews | No |
| POST | `/reviews/` | Create review | Yes |
| GET | `/reviews/{id}/` | Get review details | No |
| PUT | `/reviews/{id}/` | Update review | Owner/Admin |
| PATCH | `/reviews/{id}/` | Partial update | Owner/Admin |
| DELETE | `/reviews/{id}/` | Delete review | Owner/Admin |
| POST | `/reviews/{id}/approve/` | Approve review | Admin |
| POST | `/reviews/{id}/reject/` | Reject review | Admin |

**Query Parameters:**
- `?product=1` - Filter by product ID
- `?rating=5` - Filter by rating
- `?is_approved=true` - Filter by approval status (Admin only)

## Request/Response Examples

### Create Product (POST /api/products/)

**Request:**
```json
{
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless mouse with 2.4GHz connectivity",
  "short_description": "Comfortable wireless mouse",
  "price": "29.99",
  "cost_price": "15.00",
  "stock_quantity": 100,
  "low_stock_threshold": 10,
  "sku": "WM-001",
  "barcode": "1234567890123",
  "weight": "0.15",
  "status": "active",
  "is_featured": true,
  "is_active": true,
  "category_id": 1
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless mouse with 2.4GHz connectivity",
  "short_description": "Comfortable wireless mouse",
  "price": "29.99",
  "cost_price": "15.00",
  "stock_quantity": 100,
  "low_stock_threshold": 10,
  "sku": "WM-001",
  "barcode": "1234567890123",
  "weight": "0.15",
  "status": "active",
  "is_featured": true,
  "is_active": true,
  "category": {
    "id": 1,
    "name": "Electronics",
    "slug": "electronics"
  },
  "created_by_email": "admin@example.com",
  "is_low_stock": false,
  "profit_margin": "99.93",
  "review_count": 0,
  "average_rating": null,
  "created_at": "2026-01-28T10:00:00Z",
  "updated_at": "2026-01-28T10:00:00Z"
}
```

### Update Product (PATCH /api/products/1/)

**Request:**
```json
{
  "price": "24.99",
  "stock_quantity": 50
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Wireless Mouse",
  "price": "24.99",
  "stock_quantity": 50,
  ...
}
```

### List Products with Filters (GET /api/products/?category=1&min_price=20&max_price=50)

**Response (200 OK):**
```json
{
  "count": 15,
  "next": "http://localhost:8000/api/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Wireless Mouse",
      "short_description": "Comfortable wireless mouse",
      "price": "24.99",
      "stock_quantity": 50,
      "sku": "WM-001",
      "status": "active",
      "is_featured": true,
      "is_active": true,
      "category_name": "Electronics",
      "is_low_stock": false,
      "created_at": "2026-01-28T10:00:00Z"
    }
  ]
}
```

### Create Review (POST /api/reviews/)

**Request:**
```json
{
  "product": 1,
  "rating": 5,
  "title": "Excellent product!",
  "comment": "This wireless mouse is very comfortable and works perfectly."
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "product": 1,
  "product_name": "Wireless Mouse",
  "user_email": "user@example.com",
  "user_name": "John Doe",
  "rating": 5,
  "title": "Excellent product!",
  "comment": "This wireless mouse is very comfortable and works perfectly.",
  "is_verified_purchase": false,
  "is_approved": false,
  "created_at": "2026-01-28T10:30:00Z",
  "updated_at": "2026-01-28T10:30:00Z"
}
```

### Bulk Update Products (POST /api/products/bulk_update/)

**Request:**
```json
{
  "product_ids": [1, 2, 3],
  "status": "active",
  "is_featured": true
}
```

**Response (200 OK):**
```json
{
  "message": "Successfully updated 3 products.",
  "updated_fields": ["status", "is_featured"],
  "product_ids": [1, 2, 3]
}
```

## Error Handling

### Validation Error (400 Bad Request)
```json
{
  "name": ["This field is required."],
  "price": ["Price must be greater than zero."],
  "sku": ["A product with this SKU already exists."]
}
```

### Not Found (404 Not Found)
```json
{
  "detail": "Not found."
}
```

### Permission Denied (403 Forbidden)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Unauthorized (401 Unauthorized)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

## Authentication

### JWT Token Authentication

1. **Obtain Token:**
```bash
POST /api/auth/login/
{
  "email": "user@example.com",
  "password": "password123"
}
```

2. **Use Token in Requests:**
```bash
Authorization: Bearer <access_token>
```

3. **Refresh Token:**
```bash
POST /api/auth/token/refresh/
{
  "refresh": "<refresh_token>"
}
```

## Permissions

### Permission Classes

1. **IsAdminOrReadOnly**
   - GET: Anyone
   - POST/PUT/PATCH/DELETE: Admin only
   - Used for: Categories, Products

2. **IsOwnerOrAdmin**
   - GET: Anyone (filtered)
   - POST: Authenticated users
   - PUT/PATCH/DELETE: Owner or Admin
   - Used for: Reviews

## Validation Rules

### Product Validation
- Name: Min 3 characters
- SKU: Min 3 characters, unique, auto-uppercase
- Price: Must be > 0
- Cost price: Cannot exceed selling price
- Stock quantity: Must be >= 0
- Status: Auto-updates to 'out_of_stock' when quantity = 0

### Review Validation
- Rating: Must be 1-5
- Title: Min 5 characters
- Comment: Min 10 characters
- One review per user per product
- Cannot review inactive products

### Category Validation
- Name: Min 2 characters, unique
- Slug: Alphanumeric with hyphens/underscores only

## Testing the API

### Using cURL

```bash
# List products
curl http://localhost:8000/api/products/

# Create product (requires admin token)
curl -X POST http://localhost:8000/api/products/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Product","price":"19.99","sku":"TEST-001","status":"active"}'

# Update product
curl -X PATCH http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"price":"24.99"}'

# Delete product
curl -X DELETE http://localhost:8000/api/products/1/ \
  -H "Authorization: Bearer <token>"
```

### Using Postman

1. Import the OpenAPI schema from `/api/schema/`
2. Set up environment variables for base URL and tokens
3. Use the pre-configured requests

### Using Swagger UI

Visit: `http://localhost:8000/api/schema/swagger-ui/`

## Admin Interface

Access Django Admin at: `http://localhost:8000/admin/`

Features:
- Visual product management
- Bulk actions (mark as featured, change status)
- Stock status indicators
- Review approval workflow
- Advanced filtering and search

## Best Practices Implemented

1. **Security**
   - Input validation and sanitization
   - Permission-based access control
   - JWT authentication
   - CORS configuration

2. **Performance**
   - Database indexing on frequently queried fields
   - select_related() for foreign keys
   - Pagination for list views
   - Lightweight serializers for list operations

3. **Maintainability**
   - Comprehensive docstrings
   - Separation of concerns (models, serializers, views)
   - DRY principle
   - Consistent naming conventions

4. **Scalability**
   - Stateless API design
   - Efficient database queries
   - Modular architecture
   - Configurable settings

## Common Use Cases

### 1. E-commerce Product Catalog
- Manage products with categories
- Track inventory
- Handle customer reviews
- Featured products section

### 2. Inventory Management
- Stock tracking
- Low stock alerts
- Bulk updates
- Cost/profit analysis

### 3. Content Management
- Product information management
- Multi-status workflow (draft → active → discontinued)
- User-generated content (reviews)

## Troubleshooting

### Issue: Migrations not applying
```bash
python manage.py migrate --run-syncdb
```

### Issue: Permission denied errors
- Ensure user has proper role (is_staff for admin)
- Check JWT token is valid and not expired

### Issue: Validation errors
- Check request payload matches serializer fields
- Ensure required fields are provided
- Verify data types match model definitions

## Next Steps

1. **Add More Features:**
   - Image upload for products
   - Product variants (size, color)
   - Inventory history tracking
   - Advanced analytics

2. **Enhance Security:**
   - Rate limiting
   - API versioning
   - Request throttling
   - Input sanitization

3. **Improve Performance:**
   - Redis caching
   - Database query optimization
   - CDN for static files
   - Async task processing

4. **Testing:**
   - Unit tests for models
   - Integration tests for APIs
   - Load testing
   - Security testing

## Support

For issues or questions:
- Check the API documentation at `/api/schema/swagger-ui/`
- Review Django REST Framework docs: https://www.django-rest-framework.org/
- Check Django documentation: https://docs.djangoproject.com/

## License

This implementation is part of the LifeX Backend project.
