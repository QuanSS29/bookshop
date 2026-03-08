"""
tests.py — Bookshop
Chạy: python manage.py test books
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import Category, Book, OrderGroup, OrderItem, Review
from . import services

User = get_user_model()


# ══════════════════════════════════════════════
# HELPERS — tạo dữ liệu dùng chung
# ══════════════════════════════════════════════

def make_user(username='testuser', password='Pass1234!', role='user'):
    return User.objects.create_user(
        username=username, password=password,
        email=f'{username}@test.com', role=role
    )

def make_category(name='Văn học'):
    return Category.objects.create(name=name, status='active')

def make_book(title='Test Book', price=100000, status='active', category=None):
    if category is None:
        category = make_category()
    return Book.objects.create(
        title=title, author='Test Author',
        price=Decimal(str(price)),
        category=category, status=status,
    )


# ══════════════════════════════════════════════
# 1. MODEL TESTS
# ══════════════════════════════════════════════

class CategoryModelTest(TestCase):

    def test_create_category(self):
        cat = make_category('Khoa học')
        self.assertEqual(cat.name, 'Khoa học')
        self.assertEqual(cat.status, 'active')

    def test_str(self):
        cat = make_category('Lịch sử')
        self.assertEqual(str(cat), 'Lịch sử')


class BookModelTest(TestCase):

    def test_create_book(self):
        book = make_book('Django Handbook', price=250000)
        self.assertEqual(book.title, 'Django Handbook')
        self.assertEqual(book.price, Decimal('250000'))
        self.assertEqual(book.status, 'active')

    def test_str(self):
        book = make_book('Clean Code')
        self.assertEqual(str(book), 'Clean Code')

    def test_default_status_active(self):
        cat  = make_category()
        book = Book.objects.create(title='X', price=0, category=cat)
        self.assertEqual(book.status, 'active')


class OrderGroupModelTest(TestCase):

    def test_create_order_group(self):
        user  = make_user()
        book  = make_book()
        order = OrderGroup.objects.create(
            user=user, total_price=Decimal('100000'),
            receiver_name='Nguyen A', phone='0901234567',
            address='123 Test St',
        )
        OrderItem.objects.create(
            order_group=order, book=book,
            quantity=2, unit_price=Decimal('50000'),
        )
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().subtotal, Decimal('100000'))

    def test_default_status_pending(self):
        user  = make_user('u2')
        order = OrderGroup.objects.create(
            user=user, total_price=0,
            receiver_name='X', phone='0', address='Y',
        )
        self.assertEqual(order.status, 'pending')


# ══════════════════════════════════════════════
# 2. SERVICE TESTS
# ══════════════════════════════════════════════

class BookServiceTest(TestCase):

    def setUp(self):
        self.cat = make_category()

    def test_get_all_books_returns_active_only(self):
        make_book('Active',   status='active',   category=self.cat)
        make_book('Inactive', status='inactive', category=self.cat)
        books = services.get_all_books(status='active')
        self.assertEqual(books.count(), 1)
        self.assertEqual(books.first().title, 'Active')

    def test_get_all_books_search_by_title(self):
        make_book('Python Programming', category=self.cat)
        make_book('Java Guide',         category=self.cat)
        result = services.get_all_books(search='python')
        self.assertEqual(result.count(), 1)

    def test_get_all_books_search_by_author(self):
        Book.objects.create(title='Book A', author='Nguyen Van A',
                            price=0, category=self.cat, status='active')
        Book.objects.create(title='Book B', author='Tran Thi B',
                            price=0, category=self.cat, status='active')
        result = services.get_all_books(search='nguyen')
        self.assertEqual(result.count(), 1)

    def test_get_book_by_id_found(self):
        book = make_book(category=self.cat)
        found = services.get_book_by_id(book.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, book.id)

    def test_get_book_by_id_not_found(self):
        result = services.get_book_by_id(99999)
        self.assertIsNone(result)

    def test_create_book(self):
        data = {
            'title': 'New Book', 'author': 'Author X',
            'price': Decimal('150000'), 'description': 'Desc',
            'status': 'active', 'category': self.cat,
        }
        book = services.create_book(data=data)
        self.assertIsNotNone(book.id)
        self.assertEqual(book.title, 'New Book')
        self.assertEqual(book.category, self.cat)

    def test_update_book(self):
        book = make_book('Old Title', category=self.cat)
        data = {
            'title': 'New Title', 'author': book.author,
            'price': book.price, 'description': '',
            'status': 'active', 'category': self.cat,
        }
        updated, ok = services.update_book(book.id, data)
        self.assertTrue(ok)
        self.assertEqual(updated.title, 'New Title')

    def test_update_book_not_found(self):
        result, ok = services.update_book(99999, {})
        self.assertFalse(ok)
        self.assertIsNone(result)

    def test_delete_book(self):
        book = make_book(category=self.cat)
        bid  = book.id
        ok   = services.delete_book(bid)
        self.assertTrue(ok)
        self.assertIsNone(services.get_book_by_id(bid))

    def test_delete_book_not_found(self):
        ok = services.delete_book(99999)
        self.assertFalse(ok)

    def test_toggle_book_status(self):
        book = make_book(status='active', category=self.cat)
        toggled = services.toggle_book_status(book.id)
        self.assertEqual(toggled.status, 'inactive')
        toggled2 = services.toggle_book_status(book.id)
        self.assertEqual(toggled2.status, 'active')

    def test_sort_price_asc(self):
        make_book('Cheap',      price=50000,  category=self.cat)
        make_book('Expensive',  price=200000, category=self.cat)
        books = services.get_all_books(sort='price_asc')
        self.assertEqual(books.first().title, 'Cheap')

    def test_filter_by_category(self):
        cat2 = make_category('Tech')
        make_book('Cat1 Book', category=self.cat)
        make_book('Cat2 Book', category=cat2)
        result = services.get_all_books(category_id=cat2.id)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().title, 'Cat2 Book')


class CartServiceTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user   = make_user()
        self.book   = make_book()

    def _get_request(self):
        """Giả lập request có session thật (hỗ trợ .modified)"""
        class FakeSession(dict):
            """Dict có thêm thuộc tính .modified như Django session"""
            def __init__(self):
                super().__init__()
                self.modified = False

        class FakeRequest:
            def __init__(self):
                self.session = FakeSession()

        return FakeRequest()

    def test_cart_add(self):
        req = self._get_request()
        ok  = services.cart_add(req, self.book.id, qty=2)
        self.assertTrue(ok)
        cart = services.get_cart(req)
        self.assertIn(str(self.book.id), cart)
        self.assertEqual(cart[str(self.book.id)]['qty'], 2)

    def test_cart_add_accumulates(self):
        req = self._get_request()
        services.cart_add(req, self.book.id, qty=1)
        services.cart_add(req, self.book.id, qty=3)
        cart = services.get_cart(req)
        self.assertEqual(cart[str(self.book.id)]['qty'], 4)

    def test_cart_update(self):
        req = self._get_request()
        services.cart_add(req, self.book.id, qty=1)
        services.cart_update(req, self.book.id, qty=5)
        self.assertEqual(services.get_cart(req)[str(self.book.id)]['qty'], 5)

    def test_cart_update_zero_removes_item(self):
        req = self._get_request()
        services.cart_add(req, self.book.id, qty=1)
        services.cart_update(req, self.book.id, qty=0)
        self.assertNotIn(str(self.book.id), services.get_cart(req))

    def test_cart_remove(self):
        req = self._get_request()
        services.cart_add(req, self.book.id, qty=1)
        services.cart_remove(req, self.book.id)
        self.assertNotIn(str(self.book.id), services.get_cart(req))

    def test_cart_total(self):
        req  = self._get_request()
        b2   = make_book('Book2', price=50000)
        services.cart_add(req, self.book.id, qty=2)   # 100000 * 2
        services.cart_add(req, b2.id, qty=1)          # 50000  * 1
        cart  = services.get_cart(req)
        total = services.cart_total(cart)
        self.assertEqual(total, 100000 * 2 + 50000 * 1)

    def test_cart_clear(self):
        req = self._get_request()
        services.cart_add(req, self.book.id, qty=1)
        services.cart_clear(req)
        self.assertEqual(services.get_cart(req), {})

    def test_cart_add_invalid_book(self):
        req = self._get_request()
        ok  = services.cart_add(req, 99999, qty=1)
        self.assertFalse(ok)
        self.assertEqual(services.get_cart(req), {})


class OrderServiceTest(TestCase):

    def test_create_order(self):
        user = make_user()
        book = make_book(price=100000)

        # Tạo cart giả
        cart = {
            str(book.id): {
                'book_id': book.id,
                'title':   book.title,
                'price':   100000,
                'qty':     2,
            }
        }
        order = services.create_order(
            user=user, cart=cart,
            receiver_name='Test User',
            phone='0901234567',
            address='123 Street',
        )
        self.assertIsNotNone(order)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_price, Decimal('200000'))
        self.assertEqual(order.receiver_name, 'Test User')

    def test_create_order_empty_cart_returns_none(self):
        user  = make_user('u3')
        order = services.create_order(user=user, cart={},
                                      receiver_name='X', phone='0', address='Y')
        self.assertIsNone(order)


# ══════════════════════════════════════════════
# 3. VIEW TESTS
# ══════════════════════════════════════════════

class HomeViewTest(TestCase):

    def test_home_returns_200(self):
        res = self.client.get(reverse('books:home'))
        self.assertEqual(res.status_code, 200)

    def test_home_uses_correct_template(self):
        res = self.client.get(reverse('books:home'))
        self.assertTemplateUsed(res, 'home.html')

    def test_home_context_has_books(self):
        make_book()
        res = self.client.get(reverse('books:home'))
        self.assertIn('books_to_show', res.context)


class AuthViewTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_login_page_200(self):
        res = self.client.get(reverse('books:login'))
        self.assertEqual(res.status_code, 200)

    def test_login_success_redirects(self):
        res = self.client.post(reverse('books:login'), {
            'username': 'testuser@test.com',
            'password': 'Pass1234!',
        })
        self.assertRedirects(res, reverse('books:home'))

    def test_login_wrong_password(self):
        res = self.client.post(reverse('books:login'), {
            'username': 'testuser@test.com',
            'password': 'WrongPass!',
        })
        self.assertEqual(res.status_code, 200)

    def test_logout_redirects(self):
        self.client.login(username='testuser', password='Pass1234!')
        res = self.client.get(reverse('books:logout'))
        self.assertRedirects(res, reverse('books:home'))

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username='testuser', password='Pass1234!')
        res = self.client.get(reverse('books:login'))
        self.assertRedirects(res, reverse('books:home'))


class ShopViewTest(TestCase):

    def setUp(self):
        self.cat = make_category()
        for i in range(12):
            make_book(f'Book {i}', category=self.cat)

    def test_shop_200(self):
        res = self.client.get(reverse('books:shop'))
        self.assertEqual(res.status_code, 200)

    def test_shop_pagination_9_per_page(self):
        res = self.client.get(reverse('books:shop'))
        self.assertEqual(len(res.context['books_to_show']), 9)

    def test_shop_search(self):
        res = self.client.get(reverse('books:shop') + '?search=Book 1')
        self.assertIn('books_to_show', res.context)


class CartViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.book = make_book()

    def test_cart_page_200(self):
        res = self.client.get(reverse('books:cart'))
        self.assertEqual(res.status_code, 200)

    def test_add_to_cart(self):
        res = self.client.post(
            reverse('books:cart_add', args=[self.book.id]),
            {'qty': 2, 'next': '/'},
        )
        self.assertEqual(res.status_code, 302)
        cart = self.client.session.get('cart', {})
        self.assertIn(str(self.book.id), cart)
        self.assertEqual(cart[str(self.book.id)]['qty'], 2)

    def test_remove_from_cart(self):
        self.client.post(
            reverse('books:cart_add', args=[self.book.id]),
            {'qty': 1, 'next': '/'},
        )
        self.client.post(reverse('books:cart_remove', args=[self.book.id]))
        cart = self.client.session.get('cart', {})
        self.assertNotIn(str(self.book.id), cart)


class OrderViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.book = make_book(price=100000)

    def _add_to_cart(self):
        self.client.post(
            reverse('books:cart_add', args=[self.book.id]),
            {'qty': 1, 'next': '/'},
        )

    def test_order_requires_login(self):
        res = self.client.get(reverse('books:order'))
        self.assertRedirects(res, reverse('books:login'))

    def test_order_empty_cart_redirects(self):
        self.client.login(username='testuser', password='Pass1234!')
        res = self.client.get(reverse('books:order'))
        self.assertRedirects(res, reverse('books:cart'))

    def test_order_post_creates_order(self):
        self.client.login(username='testuser', password='Pass1234!')
        self._add_to_cart()
        res = self.client.post(reverse('books:order'), {
            'receiver_name': 'Test User',
            'phone':         '0901234567',
            'address':       '123 Test Street',
            'note':          '',
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(OrderGroup.objects.filter(user=self.user).count(), 1)

    def test_order_clears_cart_after_success(self):
        self.client.login(username='testuser', password='Pass1234!')
        self._add_to_cart()
        self.client.post(reverse('books:order'), {
            'receiver_name': 'Test User',
            'phone':         '0901234567',
            'address':       '123 Test Street',
        })
        cart = self.client.session.get('cart', {})
        self.assertEqual(cart, {})


class AdminViewTest(TestCase):

    def setUp(self):
        self.admin = make_user('admin_user', role='admin')
        self.user  = make_user('normal_user')
        self.cat   = make_category()

    def test_dashboard_requires_admin(self):
        self.client.login(username='normal_user', password='Pass1234!')
        res = self.client.get(reverse('books:dashboard'))
        self.assertRedirects(res, reverse('books:home'))

    def test_dashboard_accessible_by_admin(self):
        self.client.login(username='admin_user', password='Pass1234!')
        res = self.client.get(reverse('books:dashboard'))
        self.assertEqual(res.status_code, 200)

    def test_book_create(self):
        self.client.login(username='admin_user', password='Pass1234!')
        res = self.client.post(reverse('books:book_create'), {
            'title':       'New Book Via Form',
            'author':      'Author',
            'price':       '150000',
            'description': 'Desc',
            'status':      'active',
            'category':    self.cat.id,
        })
        self.assertEqual(Book.objects.filter(title='New Book Via Form').count(), 1)

    def test_book_delete(self):
        book = make_book(category=self.cat)
        self.client.login(username='admin_user', password='Pass1234!')
        self.client.post(reverse('books:book_delete', args=[book.id]))
        self.assertIsNone(services.get_book_by_id(book.id))

    def test_book_toggle(self):
        book = make_book(status='active', category=self.cat)
        self.client.login(username='admin_user', password='Pass1234!')
        self.client.post(reverse('books:book_toggle', args=[book.id]))
        book.refresh_from_db()
        self.assertEqual(book.status, 'inactive')