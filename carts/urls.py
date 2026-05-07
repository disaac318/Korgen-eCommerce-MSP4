from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add_cart/<int:product_id>/', views.add_cart, name='add_cart'),
    path('increment_cart_item/<int:cart_item_id>/', views.increment_cart_item, name='increment_cart_item'),
    path('confirm_remove_from_cart/<int:cart_item_id>/', views.confirm_remove_from_cart, name='confirm_remove_from_cart'),
    path('confirm_delete_cart_item/<int:cart_item_id>/', views.confirm_delete_cart_item, name='confirm_delete_cart_item'),
    path('remove_from_cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('delete_cart_item/<int:cart_item_id>/', views.delete_cart_item, name='delete_cart_item'),
  
]
