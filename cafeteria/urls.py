from django.urls import path
from . import views
from django.shortcuts import render

urlpatterns = [
    # Páginas principais
    path('', views.homepage, name='homepage'),
    path('menu/', views.menu, name='menu'),
    path('promocoes/', views.promocoes, name='promocoes'),
    path('item/<int:id>/', views.item_detail, name='item_detail'),
    
    # Carrinho e checkout
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('confirm-order/', views.confirm_order, name='confirm_order'),
    path('pagamento/<int:pedido_id>/', views.pagamento, name='pagamento'),

    # Autenticação
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('perfil/', views.perfil, name='perfil'),
    path('logout/', views.logout_view, name='logout'),
    # Placeholder para recuperação de senha (US21, não implementado)
    path('password_reset/', lambda r: render(r, 'auth/password_reset.html'), name='password_reset'),
    
    # Páginas administrativas
    path('gerenciamento/', views.admin_dashboard, name='admin_dashboard'),
    path('gerenciamento/menu/', views.admin_menu, name='admin_menu'),
    path('gerenciamento/menu/add/', views.add_menu_item, name='add_menu_item'),
    path('gerenciamento/menu/edit/<int:item_id>/', views.edit_menu_item, name='edit_menu_item'),
    path('gerenciamento/menu/delete/<int:item_id>/', views.delete_menu_item, name='delete_menu_item'),
    path('gerenciamento/pedidos/', views.gerenciar_pedidos, name='gerenciar_pedidos'),
    path('gerenciamento/promocoes/', views.admin_promocoes, name='admin_promocoes'),
    path('gerenciamento/promocoes/add/', views.add_promocao, name='add_promocao'),
    path('gerenciamento/promocoes/edit/<int:promocao_id>/', views.edit_promocao, name='edit_promocao'),
    path('gerenciamento/promocoes/delete/<int:promocao_id>/', views.delete_promocao, name='delete_promocao'),
]