from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

# --- 1. MODELO DE CAJA CHICA ---
class CajaChica(models.Model):
    """
    Controla el dinero disponible para gastos operativos y compras a proveedores.
    """
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Caja Chica"
        verbose_name_plural = "Caja Chica"

    def __str__(self):
        return f"Saldo Disponible: ${self.saldo}"

# --- 2. PERFIL DE USUARIO ---
class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    cedula = models.CharField(max_length=20, verbose_name="Cédula/RUC", blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    domicilio = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

# --- 3. MODELO DE FIGURAS ---
class Figura(models.Model):
    MATERIALES = [
        ('RESINA', 'Resina'),
        ('VIDRIO', 'Vidrio/Fibra'),
    ]
    nombre = models.CharField(max_length=100)
    medida = models.CharField(max_length=50, help_text="Ej: 40cm")
    material = models.CharField(max_length=20, choices=MATERIALES, default='RESINA')
    
    # Diferenciación de precios
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta (Cliente)")
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio de Costo (Proveedor)")
    
    stock = models.IntegerField(default=0)
    descripcion = models.TextField(max_length=500, default="Artesanía Sacra - Calidad Premium", blank=True, null=True)
    imagen = models.ImageField(upload_to='figuras/', blank=True, null=True, help_text="Sube la foto de la figura")

    def __str__(self):
        return f"{self.nombre} ({self.medida})"

# --- 4. CARRITO DE COMPRAS ---
class Carrito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carrito')
    figura = models.ForeignKey(Figura, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    agregado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.figura.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.figura.precio

# --- 5. MODELO DE VENTAS (COBRANZAS) ---
class Venta(models.Model):
    ESTADOS = [
        ('PAGADO', 'Pagado Totalmente'),
        ('PENDIENTE', 'Pendiente de Pago'),
        ('CANCELADO_MES', 'Cancelado este Mes'),
    ]
    
    MODALIDADES = [
        ('presencial', 'Cobro Presencial (Domicilio)'),
        ('virtual', 'Transferencia Virtual'),
        ('contado', 'Venta de Contado'),
    ]

    cliente = models.CharField(max_length=150)
    cedula = models.CharField(max_length=20, verbose_name="Cédula/RUC", blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    domicilio = models.CharField(max_length=255, blank=True, null=True)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    
    figura = models.ForeignKey(Figura, on_delete=models.CASCADE)
    n_contrato = models.CharField(max_length=50, unique=True, verbose_name="N° de Contrato", blank=True, null=True)
    modalidad_pago = models.CharField(max_length=20, choices=MODALIDADES, default='presencial')
    archivo_contrato = models.FileField(upload_to='contratos/', blank=True, null=True)
    
    fecha_venta = models.DateTimeField(auto_now_add=True)
    deuda_total = models.DecimalField(max_digits=10, decimal_places=2)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fecha_limite = models.DateField(help_text="Día máximo para el abono del mes")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    vendedor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def saldo_restante(self):
        return self.deuda_total - self.monto_pagado

    def actualizar_monto_pagado(self):
        total_abonado = self.abonos.aggregate(total=Sum('monto'))['total'] or 0
        self.monto_pagado = total_abonado
        
        if self.monto_pagado >= self.deuda_total:
            self.estado = 'PAGADO'
        else:
            self.estado = 'PENDIENTE'
        
        Venta.objects.filter(pk=self.pk).update(
            monto_pagado=self.monto_pagado, 
            estado=self.estado
        )

    def __str__(self):
        return f"Contrato {self.n_contrato} - {self.cliente}"

# --- 6. MODELO DE ABONOS ---
class Abono(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='abonos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    comprobante = models.ImageField(upload_to='abonos/', blank=True, null=True)
    notas = models.CharField(max_length=255, blank=True, null=True, help_text="Ej: Pago en efectivo")

    def __str__(self):
        return f"Abono ${self.monto} -> {self.venta.cliente}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.venta.actualizar_monto_pagado()