from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Category, Product, ProductReview
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductReviewSerializer,
    BulkProductUpdateSerializer
)
from .permissions import IsAdminOrReadOnly, IsOwnerOrAdmin


@extend_schema_view(
    list=extend_schema(
        tags=['Categories'],
        summary='List all categories',
        description='Retrieve a list of all product categories with product counts.',
    ),
    retrieve=extend_schema(
        tags=['Categories'],
        summary='Get category details',
        description='Retrieve detailed information about a specific category.',
    ),
    create=extend_schema(
        tags=['Categories'],
        summary='Create a new category',
        description='Create a new product category (Admin only).',
    ),
    update=extend_schema(
        tags=['Categories'],
        summary='Update category',
        description='Update an existing category (Admin only).',
    ),
    partial_update=extend_schema(
        tags=['Categories'],
        summary='Partially update category',
        description='Partially update an existing category (Admin only).',
    ),
    destroy=extend_schema(
        tags=['Categories'],
        summary='Delete category',
        description='Delete a category (Admin only). Products in this category will have their category set to null.',
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD operations.
    
    Provides:
    - list: GET /api/categories/
    - retrieve: GET /api/categories/{id}/
    - create: POST /api/categories/
    - update: PUT /api/categories/{id}/
    - partial_update: PATCH /api/categories/{id}/
    - destroy: DELETE /api/categories/{id}/
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """
        Optionally filter categories by active status.
        Query params: ?is_active=true
        """
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active', None)
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete category with custom response message.
        """
        instance = self.get_object()
        product_count = instance.products.count()
        
        self.perform_destroy(instance)
        
        return Response(
            {
                'message': f'Category deleted successfully. {product_count} products were affected.',
                'deleted_category': instance.name
            },
            status=status.HTTP_200_OK
        )


@extend_schema_view(
    list=extend_schema(
        tags=['Products'],
        summary='List all products',
        description='Retrieve a paginated list of products with filtering and search capabilities.',
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                description='Filter by category ID'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                description='Filter by status (draft, active, discontinued, out_of_stock)'
            ),
            OpenApiParameter(
                name='is_featured',
                type=OpenApiTypes.BOOL,
                description='Filter by featured status'
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.NUMBER,
                description='Minimum price filter'
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.NUMBER,
                description='Maximum price filter'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                description='Search in name, description, and SKU'
            ),
        ]
    ),
    retrieve=extend_schema(
        tags=['Products'],
        summary='Get product details',
        description='Retrieve detailed information about a specific product including reviews and ratings.',
    ),
    create=extend_schema(
        tags=['Products'],
        summary='Create a new product',
        description='Create a new product (Admin only).',
    ),
    update=extend_schema(
        tags=['Products'],
        summary='Update product',
        description='Update an existing product (Admin only).',
    ),
    partial_update=extend_schema(
        tags=['Products'],
        summary='Partially update product',
        description='Partially update an existing product (Admin only).',
    ),
    destroy=extend_schema(
        tags=['Products'],
        summary='Delete product',
        description='Delete a product (Admin only).',
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product CRUD operations with advanced filtering.
    
    Provides standard CRUD operations plus custom actions:
    - list: GET /api/products/
    - retrieve: GET /api/products/{id}/
    - create: POST /api/products/
    - update: PUT /api/products/{id}/
    - partial_update: PATCH /api/products/{id}/
    - destroy: DELETE /api/products/{id}/
    - low_stock: GET /api/products/low_stock/
    - bulk_update: POST /api/products/bulk_update/
    - update_stock: PATCH /api/products/{id}/update_stock/
    """
    queryset = Product.objects.select_related('category', 'created_by').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'sku', 'barcode']
    ordering_fields = ['name', 'price', 'stock_quantity', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        elif self.action == 'bulk_update':
            return BulkProductUpdateSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        """
        Advanced filtering for products.
        Supports: category, status, is_featured, price range, stock status
        """
        queryset = super().get_queryset()
        
        # Filter by category
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by featured
        is_featured = self.request.query_params.get('is_featured', None)
        if is_featured is not None:
            is_featured_bool = is_featured.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_featured=is_featured_bool)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)
        
        # Price range filter
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        # Low stock filter
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock and low_stock.lower() in ('true', '1', 'yes'):
            queryset = queryset.filter(
                stock_quantity__lte=models.F('low_stock_threshold')
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a new product with enhanced response.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return detailed serializer for response
        instance = serializer.instance
        response_serializer = ProductDetailSerializer(instance)
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update product with enhanced response.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return detailed serializer for response
        response_serializer = ProductDetailSerializer(instance)
        
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete product with custom response.
        """
        instance = self.get_object()
        product_name = instance.name
        product_sku = instance.sku
        
        self.perform_destroy(instance)
        
        return Response(
            {
                'message': 'Product deleted successfully.',
                'deleted_product': {
                    'name': product_name,
                    'sku': product_sku
                }
            },
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        tags=['Products'],
        summary='Get low stock products',
        description='Retrieve all products with stock below their threshold.',
    )
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Custom action to get products with low stock.
        GET /api/products/low_stock/
        """
        from django.db.models import F
        
        low_stock_products = self.get_queryset().filter(
            stock_quantity__lte=F('low_stock_threshold'),
            is_active=True
        )
        
        serializer = ProductListSerializer(low_stock_products, many=True)
        
        return Response({
            'count': low_stock_products.count(),
            'products': serializer.data
        })
    
    @extend_schema(
        tags=['Products'],
        summary='Bulk update products',
        description='Update multiple products at once (Admin only).',
        request=BulkProductUpdateSerializer,
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        """
        Bulk update multiple products.
        POST /api/products/bulk_update/
        
        Body: {
            "product_ids": [1, 2, 3],
            "status": "active",
            "is_featured": true
        }
        """
        serializer = BulkProductUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_ids = serializer.validated_data['product_ids']
        update_fields = {}
        
        if 'status' in serializer.validated_data:
            update_fields['status'] = serializer.validated_data['status']
        if 'is_active' in serializer.validated_data:
            update_fields['is_active'] = serializer.validated_data['is_active']
        if 'is_featured' in serializer.validated_data:
            update_fields['is_featured'] = serializer.validated_data['is_featured']
        
        updated_count = Product.objects.filter(id__in=product_ids).update(**update_fields)
        
        return Response({
            'message': f'Successfully updated {updated_count} products.',
            'updated_fields': list(update_fields.keys()),
            'product_ids': product_ids
        })
    
    @extend_schema(
        tags=['Products'],
        summary='Update product stock',
        description='Update stock quantity for a specific product.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'stock_quantity': {'type': 'integer', 'minimum': 0}
                },
                'required': ['stock_quantity']
            }
        }
    )
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser])
    def update_stock(self, request, pk=None):
        """
        Update stock quantity for a product.
        PATCH /api/products/{id}/update_stock/
        
        Body: {"stock_quantity": 100}
        """
        product = self.get_object()
        stock_quantity = request.data.get('stock_quantity')
        
        if stock_quantity is None:
            return Response(
                {'error': 'stock_quantity is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stock_quantity = int(stock_quantity)
            if stock_quantity < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'error': 'stock_quantity must be a non-negative integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_stock = product.stock_quantity
        product.stock_quantity = stock_quantity
        product.save()
        
        return Response({
            'message': 'Stock updated successfully.',
            'product': product.name,
            'old_stock': old_stock,
            'new_stock': product.stock_quantity,
            'is_low_stock': product.is_low_stock
        })


@extend_schema_view(
    list=extend_schema(
        tags=['Product Reviews'],
        summary='List product reviews',
        description='Retrieve reviews for products with filtering options.',
        parameters=[
            OpenApiParameter(
                name='product',
                type=OpenApiTypes.INT,
                description='Filter by product ID'
            ),
            OpenApiParameter(
                name='rating',
                type=OpenApiTypes.INT,
                description='Filter by rating (1-5)'
            ),
            OpenApiParameter(
                name='is_approved',
                type=OpenApiTypes.BOOL,
                description='Filter by approval status'
            ),
        ]
    ),
    retrieve=extend_schema(
        tags=['Product Reviews'],
        summary='Get review details',
        description='Retrieve detailed information about a specific review.',
    ),
    create=extend_schema(
        tags=['Product Reviews'],
        summary='Create a review',
        description='Create a new product review (Authenticated users only).',
    ),
    update=extend_schema(
        tags=['Product Reviews'],
        summary='Update review',
        description='Update your own review.',
    ),
    partial_update=extend_schema(
        tags=['Product Reviews'],
        summary='Partially update review',
        description='Partially update your own review.',
    ),
    destroy=extend_schema(
        tags=['Product Reviews'],
        summary='Delete review',
        description='Delete your own review or any review (Admin).',
    ),
)
class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product Review CRUD operations.
    
    Users can create, read, update, and delete their own reviews.
    Admins can manage all reviews and approve them.
    """
    queryset = ProductReview.objects.select_related('product', 'user').all()
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter reviews by product, rating, and approval status.
        Non-admin users only see approved reviews (except their own).
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Non-authenticated or non-admin users only see approved reviews
        if not user.is_authenticated or not user.is_staff:
            queryset = queryset.filter(is_approved=True)
        elif user.is_authenticated and not user.is_staff:
            # Authenticated users see approved reviews + their own
            queryset = queryset.filter(
                Q(is_approved=True) | Q(user=user)
            )
        
        # Filter by product
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by rating
        rating = self.request.query_params.get('rating', None)
        if rating:
            try:
                queryset = queryset.filter(rating=int(rating))
            except ValueError:
                pass
        
        # Filter by approval status (admin only)
        if user.is_authenticated and user.is_staff:
            is_approved = self.request.query_params.get('is_approved', None)
            if is_approved is not None:
                is_approved_bool = is_approved.lower() in ('true', '1', 'yes')
                queryset = queryset.filter(is_approved=is_approved_bool)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Save review with current user.
        """
        serializer.save(user=self.request.user)
    
    @extend_schema(
        tags=['Product Reviews'],
        summary='Approve review',
        description='Approve a product review (Admin only).',
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """
        Approve a review (Admin only).
        POST /api/reviews/{id}/approve/
        """
        review = self.get_object()
        review.is_approved = True
        review.save()
        
        serializer = self.get_serializer(review)
        
        return Response({
            'message': 'Review approved successfully.',
            'review': serializer.data
        })
    
    @extend_schema(
        tags=['Product Reviews'],
        summary='Reject review',
        description='Reject/unapprove a product review (Admin only).',
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """
        Reject/unapprove a review (Admin only).
        POST /api/reviews/{id}/reject/
        """
        review = self.get_object()
        review.is_approved = False
        review.save()
        
        serializer = self.get_serializer(review)
        
        return Response({
            'message': 'Review rejected successfully.',
            'review': serializer.data
        })
