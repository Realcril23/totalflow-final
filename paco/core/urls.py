from django.urls import path
from . import views

urlpatterns = [
    # --- Autenticación e Inicio ---
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'), # Acceso Admin
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'), # Registro Admin/Staff
    
    # --- PORTAL DEL CLIENTE (Flujo Amarillo) ---
    path('portal/login/', views.login_cliente, name='login_cliente'),
    path('portal/inicio/', views.portal_cliente, name='portal_cliente'),
    
    # --- Lógica del Carrito (Nuevas Rutas) ---
    path('carrito/agregar/<int:figura_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    
    # --- Panel Principal Admin ---
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # --- Galería / Inventario ---
    path('galeria/', views.cursos, name='cursos'),
    path('eliminar-figura/<int:figura_id>/', views.eliminar_figura, name='eliminar_figura'),
    
    # --- NUEVAS RUTAS: Cargar Stock ---
    path('inventario/cargar/', views.gestion_stock, name='gestion_stock'),
    path('inventario/update/<int:id>/', views.actualizar_stock, name='actualizar_stock'),
    
    # --- Ventas y Finanzas ---
    path('vender/<int:figura_id>/', views.realizar_venta, name='realizar_venta'),
    path('abonar/<int:venta_id>/', views.abonar_pago, name='abonar_pago'),
    
    # --- Auxiliares ---
    path('carrito/confirmar/', views.confirmar_compra, name='confirmar_compra'),
    path('dashboard/historial/', views.historial_pagados, name='historial_pagados'),
]