from django.contrib import admin

from .models import Categoria, ItemPedido, Pedido, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nome", "slug", "ordem"]
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ["nome", "categoria", "marca", "preco", "preco_promocional", "estoque", "ativo"]
    list_filter = ["categoria", "ativo", "destaque"]
    search_fields = ["nome", "marca"]
    prepopulated_fields = {"slug": ("nome",)}


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ["produto", "quantidade", "preco_unitario"]
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "nome", "email", "status", "total", "criado_em"]
    list_filter = ["status"]
    inlines = [ItemPedidoInline]
