from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User 
from django.contrib import messages 
from django.db.models import Sum, F 
from django.utils import timezone
from decimal import Decimal
import datetime 

# Importamos los modelos
from .models import Figura, Venta, Abono, Carrito, Perfil, CajaChica

# 1. Inicio
def landing(request):
    return render(request, 'core/landing.html')

# 2. Login Administrativo
def login_view(request):
    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        user = authenticate(username=usuario, password=clave)
        if user is not None:
            if user.is_staff:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Esta cuenta no tiene permisos de administrador.")
        else:
            messages.error(request, "Credenciales incorrectas.")
    return render(request, 'core/login.html')

# 3. Registro de Usuarios
def register(request):
    if request.method == 'POST':
        usuario = request.POST.get('username')
        correo = request.POST.get('email')
        clave = request.POST.get('password')
        
        cedula = request.POST.get('cedula')
        telefono = request.POST.get('telefono')
        domicilio = request.POST.get('domicilio')

        if User.objects.filter(username=usuario).exists():
            messages.error(request, "Ese nombre de usuario ya existe.")
        else:
            user = User.objects.create_user(username=usuario, email=correo, password=clave)
            Perfil.objects.create(
                user=user,
                cedula=cedula,
                telefono=telefono,
                domicilio=domicilio
            )
            messages.success(request, "Cuenta creada exitosamente. Ya puedes iniciar sesión.")
            return redirect('login')
    return render(request, 'core/register.html')

# 4. Portal del Cliente
def login_cliente(request):
    if request.method == 'POST':
        cedula_input = request.POST.get('username')
        clave = request.POST.get('password')
        user = authenticate(username=cedula_input, password=clave)
        if user is not None:
            login(request, user)
            return redirect('portal_cliente')
        else:
            messages.error(request, "Cédula o contraseña incorrecta.")
    return render(request, 'cliente/login_cliente.html')

@login_required
def portal_cliente(request):
    perfil = getattr(request.user, 'perfil', None)
    cedula_user = perfil.cedula if perfil else request.user.username
    
    venta = Venta.objects.filter(cedula=cedula_user).first()
    items_carrito = Carrito.objects.filter(usuario=request.user)
    
    subtotal_puro = sum(item.subtotal for item in items_carrito)
    iva = Decimal(subtotal_puro) * Decimal('0.15')
    total_neto_carro = Decimal(subtotal_puro) + iva

    context = {
        'venta': venta,
        'items_carrito': items_carrito,
        'subtotal_puro': subtotal_puro,
        'iva': iva,
        'total_carrito': total_neto_carro,
    }

    if venta:
        abonos = Abono.objects.filter(venta=venta).order_by('-fecha_pago')
        context.update({
            'saldo': venta.saldo_restante,
            'abonos': abonos,
            'fecha_compra': venta.fecha_venta,
            'fecha_pago_limite': venta.fecha_limite,
            'figura': venta.figura
        })
    
    return render(request, 'cliente/portal_cliente.html', context)

# 5. Cerrar Sesión
def logout_view(request):
    logout(request)
    return redirect('landing')

# 6. Dashboard Admin (LOGICA DE 6 CUADROS)
@login_required 
def dashboard(request):
    if not request.user.is_staff:
        return redirect('portal_cliente')

    abonos_totales = Abono.objects.all()
    recaudado_bruto = abonos_totales.aggregate(Sum('monto'))['monto__sum'] or Decimal('0.00')
    
    # 1. Calculamos cuánto se ha ido a Caja Chica (Costo de reposición)
    total_inversion_recuperada = Decimal('0.00')
    for abono in abonos_totales:
        fig = abono.venta.figura
        if fig.precio > 0:
            total_inversion_recuperada += abono.monto * (fig.precio_costo / fig.precio)

    # 2. Calculamos Otros Gastos (20% del total recaudado)
    otros_gastos = recaudado_bruto * Decimal('0.20') 

    # 3. El Total Neto (Ganancia) es lo que sobra
    # Ganancia = Bruto - Lo que volvió a la caja chica - Los gastos
    ganancia_neta = recaudado_bruto - total_inversion_recuperada - otros_gastos

    caja_obj = CajaChica.objects.first()
    saldo_caja_chica = caja_obj.saldo if caja_obj else 0.00
    
    ventas_pendientes = Venta.objects.exclude(estado='PAGADO').order_by('-fecha_venta')
    por_cobrar = sum(v.saldo_restante for v in Venta.objects.exclude(estado='PAGADO'))
    facturas_pendientes = ventas_pendientes.count()

    figuras = Figura.objects.all()
    inversion_stock = figuras.aggregate(total=Sum(F('stock') * F('precio_costo')))['total'] or 0
    ganancia_proyectada = figuras.aggregate(total=Sum(F('stock') * (F('precio') - F('precio_costo'))))['total'] or 0

    # Gráfica
    dias_labels = []
    ganancias_data = []
    for i in range(6, -1, -1):
        dia_iterado = timezone.now().date() - datetime.timedelta(days=i)
        dias_labels.append(dia_iterado.strftime('%d %b'))
        monto_dia = Abono.objects.filter(fecha_pago__date=dia_iterado).aggregate(Sum('monto'))['monto__sum'] or 0
        ganancias_data.append(float(monto_dia))

    context = {
        'total_neto': ganancia_neta,          # Cuadro 1: Ganancia Real
        'otros_gastos': otros_gastos,         # Cuadro 2: OTROS GASTOS (NUEVO)
        'saldo_caja_chica': saldo_caja_chica, # Cuadro 3: Saldo Inversión
        'por_cobrar': por_cobrar,             # Cuadro 4
        'inversion_stock': inversion_stock,   # Cuadro 5
        'ganancia_proyectada': ganancia_proyectada, # Cuadro 6
        'facturas_pendientes': facturas_pendientes,
        'ventas': ventas_pendientes,
        'grafica_dias': dias_labels,
        'grafica_monto': ganancias_data,
    }
    return render(request, 'core/dashboard.html', context)

# 7. Galería / Inventario
@login_required
def cursos(request):
    if request.method == 'POST' and request.user.is_staff:
        nom = request.POST.get('nombre')
        mat = request.POST.get('material')
        pre = request.POST.get('precio')
        pre_costo = request.POST.get('precio_costo', 0) 
        stk = int(request.POST.get('stock', 0))
        med = request.POST.get('medida', '40cm')
        desc = request.POST.get('descripcion')
        img = request.FILES.get('imagen') 

        Figura.objects.create(
            nombre=nom, material=mat, precio=pre, precio_costo=pre_costo,
            medida=med, imagen=img, stock=stk,
            descripcion=desc
        )
        messages.success(request, f"Pieza '{nom}' registrada exitosamente.")
        return redirect('cursos')

    figuras_db = Figura.objects.all().order_by('-id')
    conteo_carrito = Carrito.objects.filter(usuario=request.user).count()
    return render(request, 'core/cursos.html', {'figuras': figuras_db, 'conteo_global': conteo_carrito})

@login_required
def agregar_al_carrito(request, figura_id):
    figura = get_object_or_404(Figura, id=figura_id)
    if figura.stock <= 0:
        messages.error(request, "Producto agotado.")
        return redirect('cursos')

    item, created = Carrito.objects.get_or_create(usuario=request.user, figura=figura)
    if not created:
        if item.cantidad < figura.stock:
            item.cantidad += 1
            item.save()
            messages.success(request, f"Se añadió otra unidad de {figura.nombre}.")
        else:
            messages.warning(request, "Máximo stock alcanzado.")
    else:
        messages.success(request, f"{figura.nombre} añadido al carrito.")
    
    return redirect('cursos')

@login_required
def eliminar_del_carrito(request, item_id):
    item = get_object_or_404(Carrito, id=item_id, usuario=request.user)
    item.delete()
    messages.info(request, "Producto quitado del carrito.")
    return redirect('portal_cliente')

# 8. Cierre de Compra
@login_required
def confirmar_compra(request):
    items = Carrito.objects.filter(usuario=request.user)
    perfil = getattr(request.user, 'perfil', None)
    
    if not items.exists():
        messages.error(request, "El carrito está vacío.")
        return redirect('portal_cliente')

    subtotal_puro = sum(item.subtotal for item in items)
    iva = Decimal(subtotal_puro) * Decimal('0.15')
    total_con_iva = Decimal(subtotal_puro) + iva
    referencia_figura = items.first().figura

    fecha_actual = timezone.now()
    fecha_limite_defecto = fecha_actual + datetime.timedelta(days=30)

    nueva_venta = Venta.objects.create(
        cliente=request.user.get_full_name() or request.user.username,
        cedula=perfil.cedula if perfil else request.user.username, 
        telefono=perfil.telefono if perfil else "S/N",
        domicilio=perfil.domicilio if perfil else "S/N",
        figura=referencia_figura,
        deuda_total=total_con_iva,
        monto_pagado=0,
        vendedor=User.objects.filter(is_staff=True).first(),
        estado='PENDIENTE',
        fecha_venta=fecha_actual,
        fecha_limite=fecha_limite_defecto
    )

    for item in items:
        figura = item.figura
        if figura.stock >= item.cantidad:
            figura.stock -= item.cantidad
            figura.save()
        
    items.delete()
    messages.success(request, f"¡Compra #{nueva_venta.id} confirmada!")
    return redirect('portal_cliente')

# 9. Ventas Manuales y Abonos
@login_required
def realizar_venta(request, figura_id):
    if not request.user.is_staff:
        return redirect('cursos')

    if request.method == 'POST':
        figura = get_object_or_404(Figura, id=figura_id)
        Venta.objects.create(
            cliente=request.POST.get('cliente'),
            cedula=request.POST.get('cedula'),
            telefono=request.POST.get('telefono'),
            domicilio=request.POST.get('domicilio'),
            n_contrato=request.POST.get('n_contrato'),
            modalidad_pago=request.POST.get('modalidad_pago'),
            figura=figura,
            deuda_total=figura.precio,
            monto_pagado=0,
            fecha_limite=request.POST.get('fecha_limite'),
            vendedor=request.user,
            estado='PENDIENTE'
        )
        figura.stock -= 1
        figura.save()
        messages.success(request, "Venta registrada y contrato generado.")
    return redirect('dashboard')

@login_required
def abonar_pago(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Venta, id=venta_id)
        try:
            monto = Decimal(request.POST.get('monto', 0))
            if monto > 0:
                Abono.objects.create(venta=venta, monto=monto)
                
                figura = venta.figura
                caja = CajaChica.objects.first()
                
                if caja and figura.precio > 0:
                    # REPARTO AUTOMÁTICO:
                    # Mandamos el porcentaje del COSTO a Caja Chica para poder comprar otra pieza después
                    proporcion_costo = figura.precio_costo / figura.precio
                    monto_recuperacion = monto * proporcion_costo
                    caja.saldo += monto_recuperacion
                    caja.save()
                    # El dashboard automáticamente mostrará el resto en Gastos y Ganancia Neta

                if venta.saldo_restante <= 0:
                    venta.estado = 'PAGADO'
                    venta.save()
                    
                messages.success(request, f"Abono de ${monto} procesado y repartido.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
            
    return redirect('dashboard')

@login_required
def eliminar_figura(request, figura_id):
    if request.user.is_staff:
        figura = get_object_or_404(Figura, id=figura_id)
        figura.delete()
        messages.success(request, "Figura eliminada.")
    return redirect('cursos')

@login_required
def historial_pagados(request):
    ventas_pagadas = Venta.objects.filter(estado='PAGADO').order_by('-fecha_venta')
    return render(request, 'core/historial_pagados.html', {'ventas': ventas_pagadas})

@login_required
def gestion_stock(request):
    figuras = Figura.objects.all() 
    return render(request, 'core/cargar_stock.html', {'figuras': figuras})

@login_required
def actualizar_stock(request, id):
    if request.method == 'POST' and request.user.is_staff:
        figura = get_object_or_404(Figura, id=id)
        cantidad = int(request.POST.get('cantidad', 0))
        total_compra = cantidad * figura.precio_costo
        caja = CajaChica.objects.first()

        if caja and caja.saldo >= total_compra:
            figura.stock += cantidad
            figura.save()
            caja.saldo -= total_compra
            caja.save()
            messages.success(request, f"Stock actualizado. Gasto: ${total_compra}")
        else:
            messages.error(request, "Saldo insuficiente en Caja Chica.")
            
    return redirect('gestion_stock')