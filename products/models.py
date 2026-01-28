from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()


class Category(models.Model):
    """
    Category model for organizing products.
    Demonstrates one-to-many relationship with Product.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (must be unique)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional category description"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly category identifier"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when category was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when category was last updated"
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Product model demonstrating complete CRUD operations.
    Includes validation, relationships, and comprehensive field types.
    """
    
    # Status choices for product availability
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('discontinued', 'Discontinued'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        help_text="Product name"
    )
    description = models.TextField(
        help_text="Detailed product description"
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Brief product summary"
    )
    
    # Pricing and Inventory
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Product price (must be positive)"
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text="Cost price for profit calculation"
    )
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Available stock quantity"
    )
    low_stock_threshold = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text="Alert threshold for low stock"
    )
    
    # Product Details
    sku = models.CharField(
        max_length=100,
        unique=True,
        help_text="Stock Keeping Unit (unique identifier)"
    )
    barcode = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Product barcode"
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Product weight in kg"
    )
    
    # Status and Visibility
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current product status"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether product is featured"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether product is active"
    )
    
    # Relationships
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Product category"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_products',
        help_text="User who created this product"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when product was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when product was last updated"
    )
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_low_stock(self):
        """Check if product stock is below threshold"""
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def profit_margin(self):
        """Calculate profit margin if cost price is available"""
        if self.cost_price and self.cost_price > 0:
            return ((self.price - self.cost_price) / self.cost_price) * 100
        return None
    
    def save(self, *args, **kwargs):
        """Override save to add custom validation"""
        # Auto-update status based on stock
        if self.stock_quantity == 0 and self.status == 'active':
            self.status = 'out_of_stock'
        super().save(*args, **kwargs)


class ProductReview(models.Model):
    """
    Product review model demonstrating additional relationships.
    Shows how to handle user-generated content with CRUD operations.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="Product being reviewed"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        help_text="User who wrote the review"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(
        max_length=200,
        help_text="Review title"
    )
    comment = models.TextField(
        help_text="Review comment"
    )
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="Whether this is a verified purchase"
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Whether review is approved for display"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when review was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when review was last updated"
    )
    
    class Meta:
        verbose_name = "Product Review"
        verbose_name_plural = "Product Reviews"
        ordering = ['-created_at']
        unique_together = ['product', 'user']  # One review per user per product
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"
