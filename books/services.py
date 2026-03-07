from .models import Book, Category


def get_all_books(search=None, category_id=None, status=None, sort=None):
    books = Book.objects.select_related('category').all()
    if search:
        books = books.filter(title__icontains=search) | books.filter(author__icontains=search)
    if category_id:
        books = books.filter(category_id=category_id)
    if status:
        books = books.filter(status=status)
    sort_map = {
        'newest':     '-created_at',
        'oldest':     'created_at',
        'price_asc':  'price',
        'price_desc': '-price',
        'name_asc':   'title',
    }
    books = books.order_by(sort_map.get(sort, '-created_at'))
    return books


def get_book_by_id(book_id):
    try:
        return Book.objects.select_related('category').get(id=book_id)
    except Book.DoesNotExist:
        return None


def create_book(data, file=None):
    book = Book(
        title       = data.get('title'),
        author      = data.get('author', ''),
        price       = data.get('price', 0),
        description = data.get('description', ''),
        status      = data.get('status', 'active'),
    )
    category = data.get('category')
    if category:
        book.category = category   # object trực tiếp
    if file:
        book.cover_image = file
    book.save()
    return book


def update_book(book_id, data, file=None):
    book = get_book_by_id(book_id)
    if not book:
        return None, False
    book.title       = data.get('title', book.title)
    book.author      = data.get('author', book.author)
    book.price       = data.get('price', book.price)
    book.description = data.get('description', book.description)
    book.status      = data.get('status', book.status)
    category = data.get('category')
    if category:
        book.category = category   # object trực tiếp, không dùng category_id
    if file:
        book.cover_image = file
    book.save()
    return book, True


def delete_book(book_id):
    book = get_book_by_id(book_id)
    if not book:
        return False
    book.delete()
    return True


def toggle_book_status(book_id):
    book = get_book_by_id(book_id)
    if not book:
        return None
    book.status = 'inactive' if book.status == 'active' else 'active'
    book.save()
    return book


def get_all_categories():
    return Category.objects.filter(status='active').order_by('name')




# ══════════════════════════════════════════════
# CART SERVICES 
# ══════════════════════════════════════════════
# Cấu trúc session:
#   request.session['cart'] = {
#       '5': {'book_id': 5, 'title': '...', 'price': 120000,
#             'cover': '/media/...', 'qty': 2}
#   }

CART_KEY = 'cart'

def get_cart(request):
    return request.session.get(CART_KEY, {})

def _save_cart(request, cart):
    request.session[CART_KEY] = cart
    request.session.modified = True

def cart_add(request, book_id, qty=1):
    book = get_book_by_id(book_id)
    if not book:
        return False
    cart = get_cart(request)
    key  = str(book_id)
    if key in cart:
        cart[key]['qty'] += qty
    else:
        cart[key] = {
            'book_id': book.id,
            'title':   book.title,
            'author':  book.author,
            'price':   float(book.price),
            'cover':   book.cover_image.url if book.cover_image else '',
            'qty':     qty,
        }
    _save_cart(request, cart)
    return True

def cart_update(request, book_id, qty):
    """Cập nhật số lượng; qty <= 0 thì xóa"""
    cart = get_cart(request)
    key  = str(book_id)
    if key not in cart:
        return False
    if qty <= 0:
        del cart[key]
    else:
        cart[key]['qty'] = qty
    _save_cart(request, cart)
    return True

def cart_remove(request, book_id):
    cart = get_cart(request)
    key  = str(book_id)
    if key in cart:
        del cart[key]
        _save_cart(request, cart)
    return True

def cart_clear(request):
    request.session[CART_KEY] = {}
    request.session.modified  = True

def cart_total(cart):
    return sum(item['price'] * item['qty'] for item in cart.values())

def cart_count(cart):
    return sum(item['qty'] for item in cart.values())


# ══════════════════════════════════════════════
# ORDER SERVICES
# ══════════════════════════════════════════════

def create_order(user, cart, receiver_name, phone, address, note=''):
    """Tạo OrderGroup + các OrderItem từ giỏ hàng"""
    from .models import OrderGroup, OrderItem
    from decimal import Decimal

    if not cart:
        return None

    total = Decimal(str(cart_total(cart)))
    order = OrderGroup.objects.create(
        user          = user,
        total_price   = total,
        receiver_name = receiver_name,
        phone         = phone,
        address       = address,
        note          = note,
    )
    for item in cart.values():
        OrderItem.objects.create(
            order_group = order,
            book_id     = item['book_id'],
            quantity    = item['qty'],
            unit_price  = Decimal(str(item['price'])),
        )
    return order

def get_orders_by_user(user):
    from .models import OrderGroup
    return OrderGroup.objects.filter(user=user).prefetch_related('items__book').order_by('-created_at')



# ══════════════════════════════════════════════
# REVIEW SERVICES
# ══════════════════════════════════════════════

def can_user_review(user, book_id):
    """Kiểm tra user đã mua sách này chưa (dựa vào OrderGroup status done/approved)"""
    from .models import OrderGroup
    return OrderGroup.objects.filter(
        user=user,
        status__in=['done', 'approved'],
        items__book_id=book_id,
    ).exists()


def has_user_reviewed(user, book_id):
    """Kiểm tra user đã review sách này chưa"""
    from .models import Review
    return Review.objects.filter(user=user, book_id=book_id).exists()


def create_review(user, book_id, rating, comment):
    """Tạo review mới"""
    from .models import Review, Book
    book = get_book_by_id(book_id)
    if not book:
        return None, 'Không tìm thấy sách.'
    if not can_user_review(user, book_id):
        return None, 'Bạn cần mua và hoàn thành đơn hàng để đánh giá.'
    if has_user_reviewed(user, book_id):
        return None, 'Bạn đã đánh giá sách này rồi.'
    if not (1 <= int(rating) <= 5):
        return None, 'Đánh giá phải từ 1 đến 5 sao.'

    review = Review.objects.create(
        user=user,
        book=book,
        rating=int(rating),
        comment=comment.strip(),
        status='approved',  # auto approve, đổi thành 'pending' nếu cần duyệt
    )
    return review, None



# ══════════════════════════════════════════════
# USER SERVICES  — thêm vào services.py
# ══════════════════════════════════════════════

def get_all_users(search=None, role=None, status=None):
    """Lấy danh sách user với filter tùy chọn, sắp xếp mới nhất trước."""
    from .models import User
    users = User.objects.all()

    if search:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if role:
        users = users.filter(role=role)
    if status:
        users = users.filter(status=status)

    return users.order_by('-date_joined')


def toggle_user_status(user_id):
    """Khóa / mở khóa user. Trả về user sau khi đổi, hoặc None nếu không tìm thấy."""
    from .models import User
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

    # Không cho khóa admin
    if user.role == 'admin':
        return None

    user.status = 'inactive' if user.status == 'active' else 'active'
    user.save()
    return user


# ══════════════════════════════════════════════
# ORDER SERVICES — thêm vào services.py
# ══════════════════════════════════════════════

def get_all_orders(search=None, status=None, sort=None):
    """Lấy tất cả OrderGroup với filter và sort."""
    from .models import OrderGroup
    from django.db.models import Q

    orders = OrderGroup.objects.select_related('user').prefetch_related('items__book').all()

    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(receiver_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(phone__icontains=search)
        )
    if status:
        orders = orders.filter(status=status)

    sort_map = {
        'newest':     '-created_at',
        'oldest':     'created_at',
        'price_desc': '-total_price',
        'price_asc':  'total_price',
    }
    orders = orders.order_by(sort_map.get(sort, '-created_at'))
    return orders


# Các chuyển đổi trạng thái hợp lệ
VALID_ORDER_TRANSITIONS = {
    'pending':  ['approved', 'rejected'],
    'approved': ['shipping', 'rejected'],
    'shipping': ['done'],
}

def update_order_status(order_id, new_status):
    """
    Cập nhật trạng thái đơn hàng theo luồng hợp lệ.
    Trả về (order, error_message).
    """
    from .models import OrderGroup

    try:
        order = OrderGroup.objects.get(id=order_id)
    except OrderGroup.DoesNotExist:
        return None, 'Không tìm thấy đơn hàng.'

    allowed = VALID_ORDER_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        return None, f'Không thể chuyển từ "{order.status}" sang "{new_status}".'

    order.status = new_status
    order.save()
    return order, None

def get_dashboard_stats():
    """Trả về dict số liệu tổng quan cho admin dashboard."""
    from .models import Book, OrderGroup, User
    from django.utils import timezone
    from django.db.models import Sum
    from datetime import timedelta

    now        = timezone.now()
    # Đầu tháng hiện tại
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Đầu ngày hôm nay
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Sách
    total_books          = Book.objects.count()
    new_books_this_month = Book.objects.filter(created_at__gte=month_start).count()

    # Đơn hàng
    total_orders      = OrderGroup.objects.count()
    pending_orders    = OrderGroup.objects.filter(status='pending').count()
    shipping_orders   = OrderGroup.objects.filter(status='shipping').count()
    rejected_orders   = OrderGroup.objects.filter(status='rejected').count()
    new_orders_today  = OrderGroup.objects.filter(created_at__gte=today_start).count()

    # Doanh thu chỉ tính đơn done
    revenue_done = OrderGroup.objects.filter(status='done').aggregate(
        total=Sum('total_price')
    )['total'] or 0

    # Người dùng
    total_users          = User.objects.count()
    new_users_this_month = User.objects.filter(date_joined__gte=month_start).count()

    return {
        'total_books':          total_books,
        'new_books_this_month': new_books_this_month,
        'total_orders':         total_orders,
        'pending_orders':       pending_orders,
        'shipping_orders':      shipping_orders,
        'rejected_orders':      rejected_orders,
        'new_orders_today':     new_orders_today,
        'revenue_done':         revenue_done,
        'total_users':          total_users,
        'new_users_this_month': new_users_this_month,
    }






























