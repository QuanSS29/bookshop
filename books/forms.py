from django import forms
from .models import Book, Category


class BookForm(forms.ModelForm):

    # Override price thành CharField → tránh browser validate type="number"
    price = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class':       'form-input',
            'placeholder': 'Nhập giá sách...',
            'id':          'id_price',
            'inputmode':   'numeric',
        })
    )

    class Meta:
        model  = Book
        fields = ['title', 'author', 'price', 'description', 'category', 'cover_image', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nhập tên sách...'
            }),
            'author': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nhập tên tác giả...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Mô tả sách...',
                'rows': 4
            }),
            'category': forms.Select(attrs={
                'class': 'form-input'
            }),
            'cover_image': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*'
            }),
            'status': forms.Select(attrs={
                'class': 'form-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Chỉ hiển thị category đang active
        self.fields['category'].queryset    = Category.objects.filter(status='active')
        self.fields['category'].empty_label = '-- Chọn danh mục --'
        self.fields['category'].required    = True

        # Không bắt buộc
        self.fields['author'].required      = False
        self.fields['description'].required = False
        self.fields['cover_image'].required = False

        self.fields['status'].initial = 'active'

        if self.instance and self.instance.pk and self.instance.price:
            self.initial['price'] = f"{int(self.instance.price):,}".replace(',', ' ')

    def clean_price(self):
        price_raw = self.cleaned_data.get('price', '')
        price_str = str(price_raw).replace(' ', '').replace(',', '').strip()
        if not price_str:
            return 0
        try:
            price = float(price_str)
        except ValueError:
            raise forms.ValidationError('Giá không hợp lệ, chỉ nhập số.')
        if price < 0:
            raise forms.ValidationError('Giá không được âm.')
        return price

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category:
            raise forms.ValidationError('Vui lòng chọn danh mục.')
        return category

 ## check ảnh khi upload 
    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        if image and hasattr(image, 'content_type'):
            if image.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                raise forms.ValidationError('Chỉ chấp nhận ảnh JPG, PNG, WEBP.')
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Ảnh không được vượt quá 2MB.')
        return image