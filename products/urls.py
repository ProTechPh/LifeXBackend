from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, ProductReviewViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'reviews', ProductReviewViewSet, basename='review')

# The API URLs are determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]

"""
Available endpoints:

CATEGORIES:
- GET    /api/categories/              - List all categories
- POST   /api/categories/              - Create a new category (Admin)
- GET    /api/categories/{id}/         - Get category details
- PUT    /api/categories/{id}/         - Update category (Admin)
- PATCH  /api/categories/{id}/         - Partial update category (Admin)
- DELETE /api/categories/{id}/         - Delete category (Admin)

PRODUCTS:
- GET    /api/products/                - List all products (with filters)
- POST   /api/products/                - Create a new product (Admin)
- GET    /api/products/{id}/           - Get product details
- PUT    /api/products/{id}/           - Update product (Admin)
- PATCH  /api/products/{id}/           - Partial update product (Admin)
- DELETE /api/products/{id}/           - Delete product (Admin)
- GET    /api/products/low_stock/      - Get low stock products
- POST   /api/products/bulk_update/    - Bulk update products (Admin)
- PATCH  /api/products/{id}/update_stock/ - Update product stock (Admin)

REVIEWS:
- GET    /api/reviews/                 - List all reviews (filtered)
- POST   /api/reviews/                 - Create a review (Authenticated)
- GET    /api/reviews/{id}/            - Get review details
- PUT    /api/reviews/{id}/            - Update review (Owner/Admin)
- PATCH  /api/reviews/{id}/            - Partial update review (Owner/Admin)
- DELETE /api/reviews/{id}/            - Delete review (Owner/Admin)
- POST   /api/reviews/{id}/approve/    - Approve review (Admin)
- POST   /api/reviews/{id}/reject/     - Reject review (Admin)

Query Parameters for Filtering:

Categories:
- ?is_active=true/false
- ?search=keyword
- ?ordering=name,-created_at

Products:
- ?category=1
- ?status=active/draft/discontinued/out_of_stock
- ?is_featured=true/false
- ?is_active=true/false
- ?min_price=10.00
- ?max_price=100.00
- ?low_stock=true
- ?search=keyword
- ?ordering=name,price,-created_at

Reviews:
- ?product=1
- ?rating=1-5
- ?is_approved=true/false (Admin only)
- ?ordering=rating,-created_at
"""
