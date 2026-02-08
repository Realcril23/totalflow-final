from django.contrib import admin, messages
from .models import Figura, Venta, Abono, CajaChica

# --- 1. GESTIÓN DE CAJA CHICA ---
@admin.register(CajaChica)
class CajaChicaAdmin(admin.ModelAdmin):
    list_display = ('saldo', 'ultima_actualizacion')
    
    def has_add_permission(self, request):
        # Solo permite crear una caja si no existe ninguna
        return not CajaChica.objects.exists()

# --- 2. GESTIÓN DE FIGURAS CON BOTÓN DE COMPRA ---
@admin.register(Figura)
class FiguraAdmin(admin.ModelAdmin):
    # Asegúrate de que precio_costo esté en list_display para verlo
    list_display = ('nombre', 'medida', 'material', 'precio_costo', 'precio', 'stock')
    list_filter = ('material',)
    search_fields = ('nombre',)
    list_editable = ('precio_costo', 'precio', 'stock')
    
    # ESTA ES LA LÍNEA CLAVE PARA QUE SALGA EL BOTÓN
    actions = ['comprar_stock_proveedor']

    @admin.action(description="📦 Comprar 1 unidad al proveedor (Usa Caja Chica)")
    def comprar_stock_proveedor(self, request, queryset):
        caja = CajaChica.objects.first()
        
        if not caja:
            self.message_user(request, "Error: No hay una Caja Chica creada.", messages.ERROR)
            return

        exitos = 0
        for figura in queryset:
            if figura.precio_costo > 0 and caja.saldo >= figura.precio_costo:
                figura.stock += 1
                figura.save()
                caja.saldo -= figura.precio_costo
                exitos += 1
            else:
                self.message_user(request, f"Saldo insuficiente para {figura.nombre}", messages.WARNING)
        
        caja.save()
        if exitos > 0:
            self.message_user(request, f"Se compraron {exitos} unidades exitosamente.", messages.SUCCESS)

# --- 3. GESTIÓN DE VENTAS Y ABONOS ---
class AbonoInline(admin.TabularInline):
    model = Abono
    extra = 1
    readonly_fields = ('fecha_pago',)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('n_contrato', 'cliente', 'figura', 'deuda_total', 'monto_pagado', 'get_saldo', 'estado')
    list_filter = ('estado', 'modalidad_pago', 'fecha_venta')
    search_fields = ('cliente', 'cedula', 'n_contrato')
    inlines = [AbonoInline]

    def get_saldo(self, obj):
        return f"${obj.saldo_restante}"
    get_saldo.short_description = 'Saldo Pendiente'

@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):
    list_display = ('venta', 'monto', 'fecha_pago')