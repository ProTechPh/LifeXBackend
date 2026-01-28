from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal

from .models import Category, Product, ProductReview

User = get_user_model()


class CategoryModelTest(TestCase):
    """Test cases for Category model"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics",
            description="Electronic products"
        )
    
    def test_category_creation(self):
        """Test category is created correctly"""
        self.assertEqual(self.category.name, "Electronics")
        self.assertEqual(self.category.slug, "electronics")
        self.assertTrue(self.category.is_active)
    
    def test_category_str(self):
        """Test category string representation"""
        self.assertEqual(str(self.category), "Electronics")


class ProductModelTest(TestCase):
    """Test cases for Product model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics"
        )
        self.product = Product.objects.create(
            name="Wireless Mouse",
            description="Ergonomic wireless mouse",
            price=Decimal("29.99"),
            cost_price=Decimal("15.00"),
            stock_quantity=100,
            sku="WM-001",
            status="active",
            category=self.category,
            created_by=self.user
        )
    
    def test_product_creation(self):
        """Test product is created correctly"""
        self.assertEqual(self.product.name, "Wireless Mouse")
        self.assertEqual(self.product.sku, "WM-001")
        self.assertEqual(self.product.price, Decimal("29.99"))
        self.assertEqual(self.product.stock_quantity, 100)
    
    def test_product_str(self):
        """Test product string representation"""
        self.assertEqual(str(self.product), "Wireless Mouse (WM-001)")
    
    def test_is_low_stock_property(self):
        """Test is_low_stock property"""
        self.assertFalse(self.product.is_low_stock)
        self.product.stock_quantity = 5
        self.product.save()
        self.assertTrue(self.product.is_low_stock)
    
    def test_profit_margin_property(self):
        """Test profit_margin calculation"""
        expected_margin = ((Decimal("29.99") - Decimal("15.00")) / Decimal("15.00")) * 100
        self.assertAlmostEqual(float(self.product.profit_margin), float(expected_margin), places=2)
    
    def test_auto_status_update_on_zero_stock(self):
        """Test status auto-updates to out_of_stock when quantity is 0"""
        self.product.stock_quantity = 0
        self.product.save()
        self.assertEqual(self.product.status, "out_of_stock")


class CategoryAPITest(APITestCase):
    """Test cases for Category API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        self.regular_user = User.objects.create_user(
            email="user@example.com",
            password="userpass123"
        )
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics",
            description="Electronic products"
        )
    
    def test_list_categories(self):
        """Test listing categories (public access)"""
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle both paginated and non-paginated responses
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_retrieve_category(self):
        """Test retrieving a single category"""
        response = self.client.get(f'/api/categories/{self.category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Electronics")
    
    def test_create_category_as_admin(self):
        """Test creating category as admin"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'name': 'Books',
            'slug': 'books',
            'description': 'Book products'
        }
        response = self.client.post('/api/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)
    
    def test_create_category_as_regular_user(self):
        """Test creating category as regular user (should fail)"""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'name': 'Books',
            'slug': 'books'
        }
        response = self.client.post('/api/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_category_as_admin(self):
        """Test updating category as admin"""
        self.client.force_authenticate(user=self.admin_user)
        data = {'name': 'Electronics & Gadgets'}
        response = self.client.patch(f'/api/categories/{self.category.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Electronics & Gadgets')
    
    def test_delete_category_as_admin(self):
        """Test deleting category as admin"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/categories/{self.category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Category.objects.count(), 0)


class ProductAPITest(APITestCase):
    """Test cases for Product API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics"
        )
        self.product = Product.objects.create(
            name="Wireless Mouse",
            description="Ergonomic wireless mouse",
            price=Decimal("29.99"),
            stock_quantity=100,
            sku="WM-001",
            status="active",
            category=self.category,
            created_by=self.admin_user
        )
    
    def test_list_products(self):
        """Test listing products (public access)"""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_retrieve_product(self):
        """Test retrieving a single product"""
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Wireless Mouse")
        self.assertEqual(response.data['sku'], "WM-001")
    
    def test_create_product_as_admin(self):
        """Test creating product as admin"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'name': 'Keyboard',
            'description': 'Mechanical keyboard',
            'price': '79.99',
            'stock_quantity': 50,
            'sku': 'KB-001',
            'status': 'active',
            'category_id': self.category.id
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
    
    def test_create_product_validation(self):
        """Test product creation validation"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'name': 'KB',  # Too short
            'price': '-10',  # Negative price
            'sku': 'KB',  # Too short
            'stock_quantity': -5  # Negative stock
        }
        response = self.client.post('/api/products/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_product(self):
        """Test updating product"""
        self.client.force_authenticate(user=self.admin_user)
        data = {'price': '24.99', 'stock_quantity': 75}
        response = self.client.patch(f'/api/products/{self.product.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("24.99"))
        self.assertEqual(self.product.stock_quantity, 75)
    
    def test_delete_product(self):
        """Test deleting product"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Product.objects.count(), 0)
    
    def test_filter_products_by_category(self):
        """Test filtering products by category"""
        response = self.client.get(f'/api/products/?category={self.category.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_filter_products_by_price_range(self):
        """Test filtering products by price range"""
        response = self.client.get('/api/products/?min_price=20&max_price=50')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_search_products(self):
        """Test searching products"""
        response = self.client.get('/api/products/?search=mouse')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_low_stock_endpoint(self):
        """Test low stock products endpoint"""
        self.product.stock_quantity = 5
        self.product.save()
        response = self.client.get('/api/products/low_stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_bulk_update_products(self):
        """Test bulk updating products"""
        self.client.force_authenticate(user=self.admin_user)
        product2 = Product.objects.create(
            name="Keyboard",
            description="Mechanical keyboard",
            price=Decimal("79.99"),
            stock_quantity=50,
            sku="KB-001",
            status="draft",
            category=self.category,
            created_by=self.admin_user
        )
        data = {
            'product_ids': [self.product.id, product2.id],
            'status': 'active',
            'is_featured': True
        }
        response = self.client.post('/api/products/bulk_update/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        product2.refresh_from_db()
        self.assertTrue(self.product.is_featured)
        self.assertTrue(product2.is_featured)
        self.assertEqual(product2.status, 'active')
    
    def test_update_stock_endpoint(self):
        """Test updating product stock"""
        self.client.force_authenticate(user=self.admin_user)
        data = {'stock_quantity': 150}
        response = self.client.patch(f'/api/products/{self.product.id}/update_stock/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 150)


class ProductReviewAPITest(APITestCase):
    """Test cases for ProductReview API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="userpass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="userpass123"
        )
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics"
        )
        self.product = Product.objects.create(
            name="Wireless Mouse",
            description="Ergonomic wireless mouse",
            price=Decimal("29.99"),
            stock_quantity=100,
            sku="WM-001",
            status="active",
            category=self.category,
            created_by=self.admin_user
        )
        self.review = ProductReview.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            title="Great product!",
            comment="This mouse is very comfortable and works perfectly.",
            is_approved=True
        )
    
    def test_list_reviews(self):
        """Test listing reviews (public access shows only approved)"""
        response = self.client.get('/api/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_retrieve_review(self):
        """Test retrieving a single review"""
        response = self.client.get(f'/api/reviews/{self.review.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rating'], 5)
    
    def test_create_review_as_authenticated_user(self):
        """Test creating review as authenticated user"""
        self.client.force_authenticate(user=self.user2)
        data = {
            'product': self.product.id,
            'rating': 4,
            'title': 'Good product',
            'comment': 'Works well but could be better.'
        }
        response = self.client.post('/api/reviews/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductReview.objects.count(), 2)
    
    def test_create_review_as_unauthenticated_user(self):
        """Test creating review as unauthenticated user (should fail)"""
        data = {
            'product': self.product.id,
            'rating': 4,
            'title': 'Good product',
            'comment': 'Works well.'
        }
        response = self.client.post('/api/reviews/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_duplicate_review(self):
        """Test creating duplicate review (should fail)"""
        self.client.force_authenticate(user=self.user1)
        data = {
            'product': self.product.id,
            'rating': 3,
            'title': 'Another review',
            'comment': 'Trying to review again.'
        }
        response = self.client.post('/api/reviews/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_own_review(self):
        """Test updating own review"""
        self.client.force_authenticate(user=self.user1)
        data = {'rating': 4, 'title': 'Updated review'}
        response = self.client.patch(f'/api/reviews/{self.review.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
    
    def test_update_other_user_review(self):
        """Test updating another user's review (should fail)"""
        self.client.force_authenticate(user=self.user2)
        data = {'rating': 3}
        response = self.client.patch(f'/api/reviews/{self.review.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_delete_own_review(self):
        """Test deleting own review"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f'/api/reviews/{self.review.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ProductReview.objects.count(), 0)
    
    def test_approve_review_as_admin(self):
        """Test approving review as admin"""
        self.review.is_approved = False
        self.review.save()
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/reviews/{self.review.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_approved)
    
    def test_reject_review_as_admin(self):
        """Test rejecting review as admin"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/reviews/{self.review.id}/reject/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_approved)
    
    def test_filter_reviews_by_product(self):
        """Test filtering reviews by product"""
        response = self.client.get(f'/api/reviews/?product={self.product.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_filter_reviews_by_rating(self):
        """Test filtering reviews by rating"""
        response = self.client.get('/api/reviews/?rating=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
    
    def test_review_validation(self):
        """Test review validation"""
        self.client.force_authenticate(user=self.user2)
        data = {
            'product': self.product.id,
            'rating': 6,  # Invalid rating
            'title': 'Bad',  # Too short
            'comment': 'Short'  # Too short
        }
        response = self.client.post('/api/reviews/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
