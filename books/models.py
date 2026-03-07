from django.db import models
from django.contrib.auth.models import AbstractUser


# BẢNG 1: Users 
class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return self.username


class Category(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
# BẢNG 2: Books
class Book(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title



    
    
    
# BẢNG 3: Orders (đặt hàng)
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"



# BẢNG 4: Reviews (đánh giá sách)
class Review(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)       
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} on {self.book.title}"
    
    
    
class OrderGroup(models.Model):
    """Một lần đặt hàng có thể chứa nhiều sách"""
    STATUS_CHOICES = [
        ('pending',  'Chờ xác nhận'),
        ('approved', 'Đã duyệt'),
        ('shipping', 'Đang giao'),
        ('done',     'Hoàn thành'),
        ('rejected', 'Đã hủy'),
    ]
    user           = models.ForeignKey(User, on_delete=models.CASCADE)
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    total_price    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Thông tin giao hàng
    receiver_name  = models.CharField(max_length=100)
    phone          = models.CharField(max_length=20)
    address        = models.TextField()
    note           = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OrderGroup #{self.id} — {self.user.username}"


class OrderItem(models.Model):
    """Chi tiết từng sách trong một lần đặt"""
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name='items')
    book        = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity    = models.IntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.book.title} x{self.quantity}"


































