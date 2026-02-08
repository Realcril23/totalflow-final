from .models import Carrito

def carrito_count(request):
    if request.user.is_authenticated:
        # Esto cuenta cuántos tipos de figuras tiene el cliente en su carrito
        total = Carrito.objects.filter(usuario=request.user).count()
        return {'conteo_global': total}
    return {'conteo_global': 0}