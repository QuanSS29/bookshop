from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from . import services
from .forms import BookForm
from .models import User
from django.http import JsonResponse

# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('books:home')

    # Xóa messages cũ (tránh hiện "đăng xuất thành công" khi vào login)
    storage = get_messages(request)
    for _ in storage:
        pass

    if request.method == 'POST':
        email    = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            if user.status == 'inactive':
                messages.error(request, 'Tài khoản của bạn đã bị khóa.')
            else:
                login(request, user)
                messages.success(request, f'Chào mừng {user.username}!')
                return redirect('books:home')
        else:
            messages.error(request, 'Email hoặc mật khẩu không đúng.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Đã đăng xuất.')
    return redirect('books:home')


# ══════════════════════════════════════════════
# HOME / SHOP
# ══════════════════════════════════════════════

def home(request):
    from django.utils import timezone
    from datetime import timedelta

    page     = int(request.GET.get('page', 1))
    per_page = 6  # 2 hàng x 3 cột

    # Sách nổi bật: xáo trộn ngẫu nhiên
    all_books   = services.get_all_books(status='active').order_by('?')
    total_books = all_books.count()
    total_pages = (total_books + per_page - 1) // per_page
    start         = (page - 1) * per_page
    books_to_show = all_books[start:start + per_page]

    # Sách mới về: tạo trong 2 ngày gần nhất
    two_days_ago = timezone.now() - timedelta(days=2)
    new_books = services.get_all_books(status='active').filter(
        created_at__gte=two_days_ago
    ).order_by('-created_at')[:6]

    context = {
        'books_to_show': books_to_show,
        'new_books':     new_books,
        'current_page':  page,
        'total_pages':   total_pages,
        'page_range':    range(1, total_pages + 1),
    }
    return render(request, 'home.html', context)


def shop_view(request):
    from django.utils import timezone
    from datetime import timedelta

    page        = int(request.GET.get('page', 1))
    per_page    = 9
    search      = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    sort        = request.GET.get('sort', 'newest')

    all_books = services.get_all_books(
        search      = search or None,
        category_id = category_id or None,
        status      = 'active',
        sort        = sort,
    )
    total_books   = all_books.count()
    total_pages   = (total_books + per_page - 1) // per_page
    start         = (page - 1) * per_page
    books_to_show = all_books[start:start + per_page]
    categories    = services.get_all_categories()
    two_days_ago  = timezone.now() - timedelta(days=2)

    context = {
        'books_to_show': books_to_show,
        'categories':    categories,
        'total_books':   total_books,
        'current_page':  page,
        'total_pages':   total_pages,
        'page_range':    range(1, total_pages + 1),
        'search':        search,
        'selected_cat':  category_id,
        'selected_sort': sort,
        'two_days_ago':  two_days_ago,
    }
    return render(request, 'user/shop.html', context)


def product_detail_view(request, id):
    book = services.get_book_by_id(id)
    if not book:
        messages.error(request, 'Không tìm thấy sách.')
        return redirect('books:home')

    from .models import Review
    reviews = Review.objects.filter(
        book=book, status='approved'
    ).select_related('user').order_by('-created_at')

    # Kiểm tra quyền review
    can_review    = False
    has_reviewed  = False
    if request.user.is_authenticated:
        can_review   = services.can_user_review(request.user, id)
        has_reviewed = services.has_user_reviewed(request.user, id)

    return render(request, 'user/product_detail.html', {
        'book':         book,
        'reviews':      reviews,
        'can_review':   can_review,
        'has_reviewed': has_reviewed,
    })

# ── CART ──────────────────────────────────────

def cart_view(request):
    cart  = services.get_cart(request)
    total = services.cart_total(cart)
    return render(request, 'user/cart.html', {
        'cart':  cart.values(),
        'total': total,
        'count': services.cart_count(cart),
    })

def cart_add_view(request, book_id):
    qty = int(request.POST.get('qty', 1))
    ok  = services.cart_add(request, book_id, qty)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if ok:
            return JsonResponse({'status': 'ok', 'message': 'Đã thêm vào giỏ hàng!'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy sách.'}, status=404)
    
    if ok:
        messages.success(request, 'Đã thêm vào giỏ hàng!')
    else:
        messages.error(request, 'Không tìm thấy sách.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)

def cart_update_view(request, book_id):
    qty = int(request.POST.get('qty', 1))
    services.cart_update(request, book_id, qty)
    return redirect('books:cart')

def cart_remove_view(request, book_id):
    services.cart_remove(request, book_id)
    messages.success(request, 'Đã xóa khỏi giỏ hàng.')
    return redirect('books:cart')

# ── ORDER ──────────────────────────────────────

def order_view(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Vui lòng đăng nhập để đặt hàng.')
        return redirect('books:login')

    cart  = services.get_cart(request)
    total = services.cart_total(cart)

    if not cart:
        messages.warning(request, 'Giỏ hàng của bạn đang trống.')
        return redirect('books:cart')

    if request.method == 'POST':
        receiver_name = request.POST.get('receiver_name', '').strip()
        phone         = request.POST.get('phone', '').strip()
        address       = request.POST.get('address', '').strip()
        note          = request.POST.get('note', '').strip()

        if not receiver_name or not phone or not address:
            messages.error(request, 'Vui lòng điền đầy đủ thông tin giao hàng.')
        else:
            order = services.create_order(
                user          = request.user,
                cart          = cart,
                receiver_name = receiver_name,
                phone         = phone,
                address       = address,
                note          = note,
            )
            services.cart_clear(request)
            messages.success(request, f'Đặt hàng thành công! Mã đơn #{order.id}')
            return redirect('books:order_success', order_id=order.id)

    return render(request, 'user/order.html', {
        'cart':  cart.values(),
        'total': total,
        'user':  request.user,
    })

def order_success_view(request, order_id):
    from .models import OrderGroup
    try:
        order = OrderGroup.objects.prefetch_related('items__book').get(id=order_id, user=request.user)
    except:
        return redirect('books:home')
    return render(request, 'user/order_success.html', {'order': order})

@login_required(login_url='books:login')
def profile_view(request):
    from .models import OrderGroup
    from django.db.models import Sum

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_info':
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name  = request.POST.get('last_name', '').strip()
            user.email      = request.POST.get('email', '').strip()
            user.save()
            messages.success(request, 'Cập nhật thông tin thành công!')
            return redirect('books:profile')

        elif action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            user    = request.user
            old_pw  = request.POST.get('old_password', '')
            new_pw  = request.POST.get('new_password', '')
            new_pw2 = request.POST.get('new_password2', '')
            if not user.check_password(old_pw):
                messages.error(request, 'Mật khẩu hiện tại không đúng.')
            elif new_pw != new_pw2:
                messages.error(request, 'Mật khẩu mới không khớp.')
            elif len(new_pw) < 8:
                messages.error(request, 'Mật khẩu cần ít nhất 8 ký tự.')
            else:
                user.set_password(new_pw)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('books:profile')

    # ── Truy vấn đơn hàng ──────────────────────────────
    orders = (
        OrderGroup.objects
        .filter(user=request.user)
        .prefetch_related('items__book')
        .order_by('-created_at')
    )

    # Chỉ tính đơn status='done' là hoàn thành thực sự
    orders_done       = orders.filter(status='done')
    orders_done_count = orders_done.count()

    # Tổng chi tiêu chỉ tính đơn đã hoàn thành (done)
    total_spent = orders_done.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    context = {
        'orders':            orders,
        'orders_done_count': orders_done_count,
        'total_spent':       total_spent,
    }
    return render(request, 'user/profile.html', context)


# ══════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════

def _check_admin(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Vui lòng đăng nhập.')
        return redirect('books:login')
    if request.user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập.')
        return redirect('books:home')
    return None


# URL redirect về dashboard và giữ nguyên panel books
BOOKS_PANEL_URL = '/dashboard/?panel=books'



def book_create_view(request):
    check = _check_admin(request)
    if check: return check

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            services.create_book(data=form.cleaned_data, file=request.FILES.get('cover_image'))
            messages.success(request, 'Thêm sách thành công!')
            return redirect(BOOKS_PANEL_URL)  # ← về đúng panel books
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin.')
    else:
        form = BookForm()

    return render(request, 'admin/book_form.html', {'form': form, 'action': 'Thêm sách'})


def book_edit_view(request, book_id):
    check = _check_admin(request)
    if check: return check

    book = services.get_book_by_id(book_id)
    if not book:
        messages.error(request, 'Không tìm thấy sách.')
        return redirect(BOOKS_PANEL_URL)

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            services.update_book(book_id=book_id, data=form.cleaned_data, file=request.FILES.get('cover_image'))
            messages.success(request, f'Đã cập nhật "{book.title}".')
            return redirect(BOOKS_PANEL_URL)  # ← về đúng panel books
        else:
            messages.error(request, 'Vui lòng kiểm tra lại thông tin.')
    else:
        form = BookForm(instance=book)

    return render(request, 'admin/book_form.html', {'form': form, 'book': book, 'action': 'Sửa sách'})


def book_delete_view(request, book_id):
    check = _check_admin(request)
    if check: return check

    if request.method == 'POST':
        book = services.get_book_by_id(book_id)
        if book:
            services.delete_book(book_id)
            messages.success(request, f'Đã xóa "{book.title}".')
        else:
            messages.error(request, 'Không tìm thấy sách.')
    return redirect(BOOKS_PANEL_URL)  # ← về đúng panel books


def book_toggle_status_view(request, book_id):
    check = _check_admin(request)
    if check: return check

    if request.method == 'POST':
        book = services.toggle_book_status(book_id)
        if book:
            label = 'kích hoạt' if book.status == 'active' else 'ẩn'
            messages.success(request, f'Đã {label} sách "{book.title}".')
    return redirect(BOOKS_PANEL_URL)  # ← về đúng panel books



def review_add_view(request, book_id):
    if not request.user.is_authenticated:
        messages.error(request, 'Vui lòng đăng nhập để đánh giá.')
        return redirect('books:login')

    if request.method != 'POST':
        return redirect('books:product_detail', id=book_id)

    rating  = request.POST.get('rating', 5)
    comment = request.POST.get('comment', '').strip()

    review, error = services.create_review(
        user=request.user,
        book_id=book_id,
        rating=rating,
        comment=comment,
    )
    if error:
        messages.error(request, error)
    else:
        messages.success(request, 'Cảm ơn bạn đã đánh giá!')

    return redirect('books:product_detail', id=book_id)


# ══════════════════════════════════════════════
# USER MANAGEMENT VIEWS — thêm vào views.py
# ══════════════════════════════════════════════

def user_toggle_status_view(request, user_id):
    check = _check_admin(request)
    if check:
        return check

    if request.method == 'POST':
        user = services.toggle_user_status(user_id)
        if user:
            label = 'khóa' if user.status == 'inactive' else 'mở khóa'
            messages.success(request, f'Đã {label} tài khoản "{user.username}".')
        else:
            messages.error(request, 'Không thể thực hiện thao tác này.')

    # Dùng HttpResponseRedirect thay vì redirect() để nhận URL tương đối có query string
    from django.http import HttpResponseRedirect
    next_url = request.POST.get('next_url') or '/dashboard/?panel=users'
    return HttpResponseRedirect(next_url)




# ══════════════════════════════════════════════
# ORDER VIEW — thêm vào views.py
# ══════════════════════════════════════════════

def order_update_status_view(request, order_id):
    """Admin cập nhật trạng thái đơn hàng."""
    check = _check_admin(request)
    if check:
        return check

    if request.method == 'POST':
        new_status = request.POST.get('new_status', '')
        order, error = services.update_order_status(order_id, new_status)

        if error:
            messages.error(request, error)
        else:
            status_labels = {
                'approved': 'Đã duyệt',
                'shipping': 'Đang giao',
                'done':     'Hoàn thành',
                'rejected': 'Đã hủy',
            }
            label = status_labels.get(order.status, order.status)
            messages.success(request, f'Đơn #{order.id} → {label}.')

    from django.http import HttpResponseRedirect
    next_url = request.POST.get('next_url') or '/dashboard/?panel=orders'
    return HttpResponseRedirect(next_url)


# ══════════════════════════════════════════════
# CẬP NHẬT admin_dashboard_view — thêm phần orders
# ══════════════════════════════════════════════

def admin_dashboard_view(request):
    check = _check_admin(request)
    if check:
        return check

    # ── Panel: books ──────────────────────────
    books_qs = services.get_all_books(
        search      = request.GET.get('search'),
        category_id = request.GET.get('category'),
        status      = request.GET.get('status'),
        sort        = request.GET.get('sort'),
    )
    paginator_books = Paginator(books_qs, 5)
    books = paginator_books.get_page(request.GET.get('page', 1))
    categories = services.get_all_categories()

    # ── Panel: users ──────────────────────────
    user_search      = request.GET.get('user_search', '')
    selected_role    = request.GET.get('role', '')
    selected_ustatus = request.GET.get('ustatus', '')
    users_qs = services.get_all_users(
        search = user_search or None,
        role   = selected_role or None,
        status = selected_ustatus or None,
    )
    paginator_users = Paginator(users_qs, 5)
    users = paginator_users.get_page(request.GET.get('page', 1))

    # ── Panel: orders ─────────────────────────
    order_search          = request.GET.get('order_search', '')
    selected_order_status = request.GET.get('order_status', '')
    selected_order_sort   = request.GET.get('order_sort', 'newest')
    orders_qs = services.get_all_orders(
        search = order_search or None,
        status = selected_order_status or None,
        sort   = selected_order_sort,
    )
    paginator_orders = Paginator(orders_qs, 5)
    orders = paginator_orders.get_page(request.GET.get('page', 1))

    # ── Panel: overview ───────────────────────
    stats         = services.get_dashboard_stats()
    recent_orders = services.get_all_orders(sort='newest')[:5]
    recent_books  = services.get_all_books(sort='newest')[:5]

    context = {
        # books
        'books':             books,
        'categories':        categories,
        'search':            request.GET.get('search', ''),
        'selected_category': request.GET.get('category', ''),
        'selected_status':   request.GET.get('status', ''),
        'selected_sort':     request.GET.get('sort', ''),
        # users
        'users':             users,
        'user_search':       user_search,
        'selected_role':     selected_role,
        'selected_ustatus':  selected_ustatus,
        # orders
        'orders':                orders,
        'order_search':          order_search,
        'selected_order_status': selected_order_status,
        'selected_order_sort':   selected_order_sort,
        # overview
        'stats':         stats,
        'recent_orders': recent_orders,
        'recent_books':  recent_books,
        # active panel
        'active_panel': request.GET.get('panel', 'overview'),
    }
    return render(request, 'admin/dashboard.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('books:home')

    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        password   = request.POST.get('password', '')
        password2  = request.POST.get('password2', '')

        # Validate
        if not username or not email or not password:
            messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc.')
            return render(request, 'register.html')

        if password != password2:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
            return render(request, 'register.html')

        if len(password) < 8:
            messages.error(request, 'Mật khẩu cần ít nhất 8 ký tự.')
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã được sử dụng.')
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email này đã được đăng ký.')
            return render(request, 'register.html')

        # Tạo user với role mặc định 'user'
        user = User.objects.create_user(
            username   = username,
            email      = email,
            password   = password,
            first_name = first_name,
            last_name  = last_name,
        )
        user.role   = 'user'
        user.status = 'active'
        user.save()

        # Đăng nhập luôn sau khi tạo xong
        login(request, user)
        messages.success(request, f'Chào mừng {user.username}! Tài khoản đã được tạo thành công.')
        return redirect('books:home')

    return render(request, 'register.html')
