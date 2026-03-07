from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # trang chung
    path('',        views.home,         name='home'),
    path('login/',  views.login_view,   name='login'),
    path('logout/', views.logout_view,  name='logout'),

    # user
    path('product/<int:id>/', views.product_detail_view, name='product_detail'),
    path('cart/',             views.cart_view,           name='cart'),
    path('order/',            views.order_view,          name='order'),
    path('profile/',          views.profile_view,        name='profile'),
    path('shop/',             views.shop_view,           name='shop'),

    # admin
    path('dashboard/', views.admin_dashboard_view, name='dashboard'),

    # Admin CRUD sách
    path('dashboard/books/create/',               views.book_create_view,        name='book_create'),
    path('dashboard/books/<int:book_id>/edit/',   views.book_edit_view,          name='book_edit'),
    path('dashboard/books/<int:book_id>/delete/', views.book_delete_view,        name='book_delete'),
    path('dashboard/books/<int:book_id>/toggle/', views.book_toggle_status_view, name='book_toggle'),
    
    # cart
    path('cart/',                          views.cart_view,        name='cart'),
    path('cart/add/<int:book_id>/',        views.cart_add_view,    name='cart_add'),
    path('cart/update/<int:book_id>/',     views.cart_update_view, name='cart_update'),
    path('cart/remove/<int:book_id>/',     views.cart_remove_view, name='cart_remove'),

    # order
    path('order/',                         views.order_view,         name='order'),
    path('order/success/<int:order_id>/',  views.order_success_view, name='order_success'),
    
    
    # review 
    path('books/<int:book_id>/review/', views.review_add_view, name='review_add'),
    
    # manager user
    path('users/<int:user_id>/toggle/', views.user_toggle_status_view, name='user_toggle'),
    path('orders/<int:order_id>/status/', views.order_update_status_view, name='order_update_status'),
    path('register/', views.register_view, name='register'),

]