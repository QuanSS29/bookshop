from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def home(request):
    
    page = int(request.GET.get('page', 1))
    per_page = 12
    all_books = list(range(1, 18)) 
    total_books = len(all_books)
    total_pages = (total_books + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = min(start + per_page, total_books) 
    books_to_show = all_books[start:end]

    context = {
        'books_to_show': books_to_show,
        'current_page': page,
        'total_pages': total_pages,
        'page_range': range(1, total_pages + 1),
    }
    return render(request, 'home.html', context)


def login_view(request):
    """Xử lý đăng nhập"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Đăng nhập thành công!')
            return redirect('books:home') 
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    
    return render(request, 'login.html')

def dashboard_view(request):
    return render(request, 'dashboard.html')
