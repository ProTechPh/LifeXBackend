from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductReview


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Category model.
    """
    list_display = ['name', 'slug', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_count(self, obj):
        """Display count of products in category"""
        count = obj.products.count()
        return format_html('<strong>{}</strong>', count)
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model with advanced features.
    """
    list_display = [
        'name', 'sku', 'price', 'stock_quantity', 'status',
        'is_featured', 'is_active', 'stock_status', 'created_at'
    ]
    list_filter = [
        'status', 'is_featured', 'is_active', 'category',
        'created_at', 'updated_at'
    ]
    search_fields = ['name', 'description', 'sku', 'barcode']
    list_editable = ['is_featured', 'is_active', 'status']
    readonly_fields = [
        'created_at', 'updated_at', 'created_by',
        'is_low_stock', 'profit_margin'
    ]
    autocomplete_fields = ['category']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'short_description', 'category')
        }),
        ('Pricing & Inventory', {
            'fields': (
                'price', 'cost_price', 'stock_quantity',
                'low_stock_threshold', 'is_low_stock', 'profit_margin'
            )
        }),
        ('Product Details', {
            'fields': ('sku', 'barcode', 'weight')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'is_featured', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_active',
        'mark_as_discontinued',
        'mark_as_featured',
        'unmark_as_featured'
    ]
    
    def stock_status(self, obj):
        """Display stock status with color coding"""
        if obj.stock_quantity == 0:
            color = 'red'
            text = 'Out of Stock'
        elif obj.is_low_stock:
            color = 'orange'
            text = 'Low Stock'
        else:
            color = 'green'
            text = 'In Stock'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    stock_status.short_description = 'Stock Status'
    
    def save_model(self, request, obj, form, change):
        """Set created_by on creation"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Admin actions
    @admin.action(description='Mark selected products as active')
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='active', is_active=True)
        self.message_user(request, f'{updated} products marked as active.')
    
    @admin.action(description='Mark selected products as discontinued')
    def mark_as_discontinued(self, request, queryset):
        updated = queryset.update(status='discontinued')
        self.message_user(request, f'{updated} products marked as discontinued.')
    
    @admin.action(description='Mark selected products as featured')
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    
    @admin.action(description='Unmark selected products as featured')
    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} products unmarked as featured.')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductReview model.
    """
    list_display = [
        'product', 'user', 'rating', 'title',
        'is_verified_purchase', 'is_approved', 'created_at'
    ]
    list_filter = [
        'rating', 'is_verified_purchase', 'is_approved',
        'created_at', 'updated_at'
    ]
    search_fields = ['title', 'comment', 'product__name', 'user__email']
    list_editable = ['is_approved']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['product', 'user']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'user', 'rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'reject_reviews']
    
    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    
    @admin.action(description='Reject selected reviews')
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews rejected.')
