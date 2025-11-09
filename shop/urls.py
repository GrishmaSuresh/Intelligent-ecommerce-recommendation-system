from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('ask_my_circle/', views.ask_my_circle, name='ask_my_circle'),
    path('get_my_circle/', views.get_my_circle, name='get_my_circle'),
    path('search/', views.search, name='search'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('notifications/', views.my_notifications, name='notifications'),
    path('ask-circle/', views.ask_my_circle, name='ask_my_circle'),
    path('get-circle/', views.get_my_circle, name='get_my_circle'),
path('chat/<int:product_id>/', views.chat_room, name='chat_room'),
path('react/<int:product_id>/', views.react_to_product, name='react_to_product'),

]
