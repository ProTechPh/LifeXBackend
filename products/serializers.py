from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, Product, ProductReview

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model.
    Handles validation and serialization for category CRUD operations.
    """
    product_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'slug', 'is_active',
            'created_at', 'updated_at', 'product_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_product_count(self, obj):
        """Return count of active products in this category"""
        return obj.products.filter(is_active=True).count()
    
    def validate_name(self, value):
        """Validate category name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Category name must be at least 2 characters long."
            )
        return value.strip()
    
    def validate_slug(self, value):
        """Validate slug format"""
        if not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError(
                "Slug can only contain letters, numbers, hyphens, and underscores."
            )
        return value.lower()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product list views.
    Returns minimal data for better performance in list operations.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'short_description', 'price', 'stock_quantity',
            'sku', 'status', 'is_featured', 'is_active', 'category_name',
            'is_low_stock', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for product retrieve operations.
    Includes all fields and computed properties.
    """
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    profit_margin = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    review_count = serializers.SerializerMethodField(read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'short_description', 'price',
            'cost_price', 'stock_quantity', 'low_stock_threshold', 'sku',
            'barcode', 'weight', 'status', 'is_featured', 'is_active',
            'category', 'category_id', 'created_by_email', 'is_low_stock',
            'profit_margin', 'review_count', 'average_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by_email']
    
    def get_review_count(self, obj):
        """Return count of approved reviews"""
        return obj.reviews.filter(is_approved=True).count()
    
    def get_average_rating(self, obj):
        """Calculate average rating from approved reviews"""
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            from django.db.models import Avg
            avg = reviews.aggregate(Avg('rating'))['rating__avg']
            return round(avg, 2) if avg else None
        return None


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for product create and update operations.
    Includes comprehensive validation rules.
    """
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        source='category',
        required=False,
        allow_null=True,
        help_text="ID of the category (must be active)"
    )
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'short_description', 'price',
            'cost_price', 'stock_quantity', 'low_stock_threshold', 'sku',
            'barcode', 'weight', 'status', 'is_featured', 'is_active',
            'category_id'
        ]
        read_only_fields = ['id']
    
    def validate_name(self, value):
        """Validate product name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Product name must be at least 3 characters long."
            )
        return value.strip()
    
    def validate_sku(self, value):
        """Validate SKU uniqueness and format"""
        value = value.strip().upper()
        
        # Check uniqueness (excluding current instance on update)
        instance = self.instance
        if Product.objects.filter(sku=value).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists."
            )
        
        if len(value) < 3:
            raise serializers.ValidationError(
                "SKU must be at least 3 characters long."
            )
        
        return value
    
    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )
        return value
    
    def validate_stock_quantity(self, value):
        """Validate stock quantity"""
        if value < 0:
            raise serializers.ValidationError(
                "Stock quantity cannot be negative."
            )
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Validate cost price vs selling price
        cost_price = attrs.get('cost_price', self.instance.cost_price if self.instance else None)
        price = attrs.get('price', self.instance.price if self.instance else None)
        
        if cost_price and price and cost_price > price:
            raise serializers.ValidationError({
                'cost_price': 'Cost price cannot be greater than selling price.'
            })
        
        # Validate low stock threshold
        low_stock = attrs.get('low_stock_threshold', 
                             self.instance.low_stock_threshold if self.instance else 10)
        stock = attrs.get('stock_quantity',
                         self.instance.stock_quantity if self.instance else 0)
        
        if low_stock > stock:
            # This is just a warning, not an error
            pass
        
        return attrs
    
    def create(self, validated_data):
        """Create product with current user as creator"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for product review CRUD operations.
    Includes validation for ratings and user permissions.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'user_email', 'user_name',
            'rating', 'title', 'comment', 'is_verified_purchase',
            'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'user_name', 'product_name',
            'is_verified_purchase', 'is_approved', 'created_at', 'updated_at'
        ]
    
    def get_user_name(self, obj):
        """Return user's full name or email"""
        if obj.user.first_name or obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.email
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )
        return value
    
    def validate_title(self, value):
        """Validate review title"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Review title must be at least 5 characters long."
            )
        return value.strip()
    
    def validate_comment(self, value):
        """Validate review comment"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Review comment must be at least 10 characters long."
            )
        return value.strip()
    
    def validate_product(self, value):
        """Validate product exists and is active"""
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot review an inactive product."
            )
        return value
    
    def validate(self, attrs):
        """Check if user already reviewed this product"""
        request = self.context.get('request')
        product = attrs.get('product')
        
        if request and hasattr(request, 'user') and product:
            # Only check on create, not update
            if not self.instance:
                if ProductReview.objects.filter(
                    user=request.user,
                    product=product
                ).exists():
                    raise serializers.ValidationError(
                        "You have already reviewed this product."
                    )
        
        return attrs
    
    def create(self, validated_data):
        """Create review with current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class BulkProductUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk update operations.
    Allows updating multiple products at once.
    """
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of product IDs to update"
    )
    status = serializers.ChoiceField(
        choices=Product.STATUS_CHOICES,
        required=False,
        help_text="New status for selected products"
    )
    is_active = serializers.BooleanField(
        required=False,
        help_text="Active status for selected products"
    )
    is_featured = serializers.BooleanField(
        required=False,
        help_text="Featured status for selected products"
    )
    
    def validate_product_ids(self, value):
        """Validate all product IDs exist"""
        existing_ids = Product.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)
        
        if missing_ids:
            raise serializers.ValidationError(
                f"Products with IDs {missing_ids} do not exist."
            )
        
        return value
    
    def validate(self, attrs):
        """Ensure at least one field to update is provided"""
        update_fields = ['status', 'is_active', 'is_featured']
        if not any(field in attrs for field in update_fields):
            raise serializers.ValidationError(
                "At least one field to update must be provided."
            )
        return attrs
