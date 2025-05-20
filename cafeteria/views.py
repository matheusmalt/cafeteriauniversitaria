from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from .models import ItemMenu, Promocao, Carrinho, ItemCarrinho, Pedido, PedidoItem
import logging
from django.utils import timezone
import os

# Configurar logger para depuração
logger = logging.getLogger(__name__)

# Verifica se o usuário é administrador
def is_admin(user):
    return user.is_staff

@login_required(login_url='login')  # Explicitamente define login_url
@user_passes_test(is_admin, login_url='login')
def admin_dashboard(request):
    return render(request, 'admin/dashboard.html')

def homepage(request):
    featured_items = ItemMenu.objects.filter(destaque=True)[:4]
    promocoes = Promocao.objects.filter(ativa=True)
    return render(request, 'index.html', {'featured_items': featured_items, 'promocoes': promocoes})

def menu(request):
    query = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    items = ItemMenu.objects.all()
    if query:
        items = items.filter(nome__icontains=query)
    if categoria:
        items = items.filter(categoria=categoria)
    categorias = ItemMenu.objects.values_list('categoria', flat=True).distinct()
    return render(request, 'menu.html', {'items': items, 'categorias': categorias, 'query': query, 'selected_categoria': categoria})

def item_detail(request, id):
    item = ItemMenu.objects.get(id=id)
    return render(request, 'item_detail.html', {'item': item})

def cart(request):
    cart_items = ItemCarrinho.objects.filter(carrinho__cliente=request.user)
    cart_total = sum(item.subtotal for item in cart_items)
    return render(request, 'cart.html', {'cart_items': cart_items, 'cart_total': cart_total})

def add_to_cart(request, item_id):
    item = get_object_or_404(ItemMenu, id=item_id)
    
    # Obtém ou cria um carrinho para o usuário atual
    carrinho, created = Carrinho.objects.get_or_create(cliente=request.user)
    
    if request.method == 'POST':
        quantidade = int(request.POST.get('quantidade', 1))
        # Verifica se a quantidade é válida
        if quantidade < 1:
            messages.error(request, "Quantidade deve ser pelo menos 1.")
            return redirect('item_detail', id=item_id)
        
        # Verifica se o item já está no carrinho
        item_carrinho, created = ItemCarrinho.objects.get_or_create(
            carrinho=carrinho,
            item_menu=item,
            defaults={'quantidade': quantidade, 'preco_unitario': item.preco}
        )
        
        if not created:
            item_carrinho.quantidade += quantidade
            item_carrinho.save()
        
        messages.success(request, f"{item.nome} adicionado ao carrinho!")
        return redirect('cart')  # Redireciona para a página do carrinho
    
    messages.error(request, "Método inválido para adicionar ao carrinho.")
    return redirect('item_detail', id=item_id)

def checkout(request):
    carrinho = get_object_or_404(Carrinho, cliente=request.user)
    cart_items = ItemCarrinho.objects.filter(carrinho=carrinho)
    cart_total = sum(item.subtotal for item in cart_items)
    
    if not cart_items.exists():
        messages.error(request, "Seu carrinho está vazio.")
        logger.warning(f"Acesso ao checkout com carrinho vazio por {request.user.email}")
        return redirect('cart')

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
    })

def update_cart(request, item_id):
    if request.method == 'POST':
        nova_quantidade = int(request.POST.get('quantidade', 1))

        carrinho = get_object_or_404(Carrinho, cliente=request.user)
        item_carrinho = get_object_or_404(ItemCarrinho, carrinho=carrinho, item_menu__id=item_id)

        if nova_quantidade > 0:
            item_carrinho.quantidade = nova_quantidade
            item_carrinho.save()
        else:
            item_carrinho.delete()

    return redirect('cart')

def remove_from_cart(request, item_id):
    carrinho = get_object_or_404(Carrinho, cliente=request.user)
    logger.debug(f"Tentando remover item_menu__id={item_id} do carrinho {carrinho.id} do usuário {request.user.email}")
    
    try:
        item_carrinho = ItemCarrinho.objects.get(carrinho=carrinho, item_menu__id=item_id)
        item_nome = item_carrinho.item_menu.nome
        item_carrinho.delete()
        messages.success(request, f"{item_nome} removido do carrinho!")
        logger.info(f"Item {item_nome} (item_menu__id={item_id}) removido do carrinho {carrinho.id}")
    except ItemCarrinho.DoesNotExist:
        item_nome = ItemMenu.objects.filter(id=item_id).first()
        item_nome = item_nome.nome if item_nome else f"ID {item_id}"
        messages.error(request, f"O item '{item_nome}' não está no seu carrinho.")
        logger.warning(f"ItemCarrinho não encontrado para carrinho {carrinho.id} e item_menu__id={item_id}")
    
    return redirect('cart')

def confirm_order(request):
    if request.method != 'POST':
        messages.error(request, "Método inválido para confirmar o pedido.")
        return redirect('cart')

    carrinho = get_object_or_404(Carrinho, cliente=request.user)
    itens = ItemCarrinho.objects.filter(carrinho=carrinho)

    if not itens.exists():
        messages.error(request, "Seu carrinho está vazio.")
        logger.warning(f"Tentativa de confirmar pedido com carrinho vazio para {request.user.email}")
        return redirect('cart')

    # Processar dados do formulário
    metodo_entrega = request.POST.get('metodo_entrega', 'retirada')
    endereco_entrega = request.POST.get('endereco', '') if metodo_entrega == 'entrega' else ''
    metodo_pagamento = request.POST.get('metodo_pagamento', 'pix')

    # Validar método de entrega
    if metodo_entrega not in ['retirada', 'entrega']:
        messages.error(request, "Método de entrega inválido.")
        logger.warning(f"Método de entrega inválido: {metodo_entrega} para {request.user.email}")
        return redirect('checkout')

    # Validar endereço para entrega
    if metodo_entrega == 'entrega' and not endereco_entrega.strip():
        messages.error(request, "Por favor, forneça um endereço de entrega.")
        logger.warning(f"Endereço de entrega vazio para {request.user.email}")
        return redirect('checkout')

    # Validar método de pagamento
    if metodo_pagamento not in ['cartao', 'pix']:
        messages.error(request, "Método de pagamento inválido.")
        logger.warning(f"Método de pagamento inválido: {metodo_pagamento} para {request.user.email}")
        return redirect('checkout')

    try:
        with transaction.atomic():
            # Calcular o total do carrinho
            total = sum(item.subtotal for item in itens)
            
            # Verificar disponibilidade dos itens
            for item in itens:
                if not item.item_menu.disponibilidade:
                    messages.error(request, f"{item.item_menu.nome} está indisponível.")
                    logger.warning(f"Item indisponível: {item.item_menu.nome} no carrinho de {request.user.email}")
                    return redirect('cart')

            # Aplicar promoção, se houver
            promocao = Promocao.objects.filter(
                ativa=True,
                data_inicio__lte=timezone.now().date(),
                data_fim__gte=timezone.now().date()
            ).first()
            if promocao:
                desconto = total * (promocao.desconto / 100)
                total -= desconto
                logger.debug(f"Aplicado desconto de {promocao.desconto}% (R${desconto:.2f}) ao Pedido para {request.user.email}")
                messages.success(request, f"Desconto de {promocao.desconto}% aplicado! Você economizou R${desconto:.2f}.")

            # Criar o pedido
            pedido = Pedido.objects.create(
                cliente=request.user,
                total=total,
                status='PENDENTE',
                metodo_entrega='Retirada no Local' if metodo_entrega == 'retirada' else 'Entrega',
                endereco_entrega=endereco_entrega,
                metodo_pagamento='Cartão de Crédito' if metodo_pagamento == 'cartao' else 'PIX',
            )
            logger.debug(f"Pedido #{pedido.id} criado para {request.user.email} com total R${total}")

            # Criar PedidoItem para cada ItemCarrinho
            for item in itens:
                PedidoItem.objects.create(
                    pedido=pedido,
                    item_menu=item.item_menu,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario
                )
                logger.debug(f"PedidoItem criado: {item.quantidade}x {item.item_menu.nome} no Pedido #{pedido.id}")

            # Limpar o carrinho
            itens.delete()
            logger.info(f"Carrinho {carrinho.id} limpo após criação do Pedido #{pedido.id}")

            messages.success(request, f"Pedido #{pedido.id} confirmado com sucesso! Prossiga com o pagamento.")
            return redirect('pagamento', pedido_id=pedido.id)

    except Exception as e:
        logger.error(f"Erro ao confirmar pedido para {request.user.email}: {str(e)}", exc_info=True)
        messages.error(request, "Erro ao confirmar o pedido. Tente novamente.")
        return redirect('checkout')
    
def promocoes(request):
    # Filtrar promoções válidas (ativas e dentro do período)
    promocoes = Promocao.objects.filter(ativa=True, data_inicio__lte=timezone.now().date(), data_fim__gte=timezone.now().date())
    logger.debug(f"Exibindo {promocoes.count()} promoções válidas para {request.user.email if request.user.is_authenticated else 'usuário anônimo'}")
    
    return render(request, 'promocoes.html', {'promocoes': promocoes})


@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_promocoes(request):
    promocoes = Promocao.objects.all().order_by('titulo')
    return render(request, 'admin/promocoes.html', {
        'promocoes': promocoes
    })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def add_promocao(request):
    if request.method == 'POST':
        logger.debug(f"POST recebido: {request.POST}")
        form_data = request.POST
        try:
            with transaction.atomic():
                titulo = request.POST.get('titulo')
                descricao = request.POST.get('descricao', '')
                desconto = request.POST.get('desconto')
                data_inicio = request.POST.get('data_inicio')
                data_fim = request.POST.get('data_fim')
                ativa = request.POST.get('ativa') == 'on'

                if not all([titulo, desconto, data_inicio, data_fim]):
                    logger.warning("Campos obrigatórios ausentes")
                    messages.error(request, 'Preencha todos os campos obrigatórios.')
                    return render(request, 'admin/promocoes.html', {
                        'promocoes': Promocao.objects.all(),
                        'form_data': form_data
                    })

                try:
                    desconto = Decimal(desconto)
                    if not 0 < desconto <= 100:
                        raise ValueError("Desconto deve estar entre 0.01 e 100.")
                except (ValueError, TypeError):
                    logger.warning(f"Desconto inválido: {desconto}")
                    messages.error(request, 'Desconto inválido. Use um valor entre 0.01 e 100.')
                    return render(request, 'admin/promocoes.html', {
                        'promocoes': Promocao.objects.all(),
                        'form_data': form_data
                    })

                logger.debug(f"Criando Promoção: titulo={titulo}, desconto={desconto}%")
                promocao = Promocao(
                    titulo=titulo,
                    descricao=descricao,
                    desconto=desconto,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    ativa=ativa
                )
                promocao.full_clean()
                promocao.save()

                logger.info(f"Promoção '{titulo}' salva com sucesso, ID: {promocao.id}")
                messages.success(request, f'Promoção "{titulo}" adicionada com sucesso.')
                return redirect('admin_promocoes')

        except ValidationError as e:
            logger.error(f"ValidationError ao salvar promoção: {str(e)}")
            messages.error(request, f'Erro ao adicionar promoção: {str(e)}')
            return render(request, 'admin/promocoes.html', {
                'promocoes': Promocao.objects.all(),
                'form_data': form_data
            })
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar promoção: {str(e)}", exc_info=True)
            messages.error(request, f'Erro inesperado: {str(e)}')
            return render(request, 'admin/promocoes.html', {
                'promocoes': Promocao.objects.all(),
                'form_data': form_data
            })

    return render(request, 'admin/promocoes.html', {
        'promocoes': Promocao.objects.all()
    })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def edit_promocao(request, promocao_id):
    promocao = get_object_or_404(Promocao, id=promocao_id)

    if request.method == 'POST':
        form_data = {
            'titulo': request.POST.get('titulo', ''),
            'descricao': request.POST.get('descricao', ''),
            'desconto': request.POST.get('desconto', ''),
            'data_inicio': request.POST.get('data_inicio', ''),
            'data_fim': request.POST.get('data_fim', ''),
            'ativa': request.POST.get('ativa') == 'on'
        }
        try:
            with transaction.atomic():
                promocao.titulo = request.POST.get('titulo', promocao.titulo)
                promocao.descricao = request.POST.get('descricao', promocao.descricao)
                desconto = request.POST.get('desconto', promocao.desconto)
                promocao.data_inicio = request.POST.get('data_inicio', promocao.data_inicio)
                promocao.data_fim = request.POST.get('data_fim', promocao.data_fim)
                promocao.ativa = request.POST.get('ativa') == 'on'

                try:
                    desconto = Decimal(desconto)
                    if not 0 < desconto <= 100:
                        raise ValueError("Desconto deve estar entre 0.01 e 100.")
                    promocao.desconto = desconto
                except (ValueError, TypeError):
                    logger.warning(f"Desconto inválido: {desconto}")
                    messages.error(request, 'Desconto inválido. Use um valor entre 0.01 e 100.')
                    return render(request, 'admin/edit_promocao.html', {
                        'promocao': promocao,
                        'form_data': form_data
                    })

                promocao.full_clean()
                promocao.save()

                logger.info(f"Promoção '{promocao.titulo}' atualizada com sucesso, ID: {promocao.id}")
                messages.success(request, f'Promoção "{promocao.titulo}" atualizada com sucesso.')
                return redirect('admin_promocoes')

        except ValidationError as e:
            logger.error(f"ValidationError ao atualizar promoção: {str(e)}")
            messages.error(request, f'Erro ao atualizar promoção: {str(e)}')
            return render(request, 'admin/edit_promocao.html', {
                'promocao': promocao,
                'form_data': form_data
            })
        except Exception as e:
            logger.error(f"Erro inesperado ao atualizar promoção: {str(e)}", exc_info=True)
            messages.error(request, 'Erro inesperado. Tente novamente.')
            return render(request, 'admin/edit_promocao.html', {
                'promocao': promocao,
                'form_data': form_data
            })

    return render(request, 'admin/edit_promocao.html', {
        'promocao': promocao
    })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_promocao(request, promocao_id):
    promocao = get_object_or_404(Promocao, id=promocao_id)
    if request.method == 'POST':
        try:
            titulo = promocao.titulo
            promocao.delete()
            logger.info(f"Promoção '{titulo}' excluída com sucesso, ID: {promocao_id}")
            messages.success(request, f'Promoção "{titulo}" excluída com sucesso.')
        except Exception as e:
            logger.error(f"Erro ao excluir promoção ID {promocao_id}: {str(e)}", exc_info=True)
            messages.error(request, 'Erro ao excluir promoção. Tente novamente.')
        return redirect('admin_promocoes')
    return redirect('admin_promocoes')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('homepage')

    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not all([nome, email, password, confirm_password]):
            messages.error(request, 'Por favor, preencha todos os campos.')
        elif password != confirm_password:
            messages.error(request, 'As senhas não coincidem.')
        elif User.objects.filter(username=email).exists():
            messages.error(request, 'Este e-mail já está registrado.')
        else:
            try:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=nome
                )
                login(request, user)
                messages.success(request, 'Conta criada com sucesso! Bem-vindo!')
                return redirect('homepage')
            except Exception as e:
                messages.error(request, 'Erro ao criar a conta. Tente novamente.')

    return render(request, 'auth/register.html')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_menu(request):
    itens = ItemMenu.objects.all().order_by('nome')
    categoria_choices = ItemMenu._meta.get_field('categoria').choices
    return render(request, 'admin/menu.html', {
        'items': itens,
        'categoria_choices': categoria_choices
    })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def add_menu_item(request):
    if request.method == 'POST':
        logger.debug(f"POST recebido: {request.POST}, FILES: {request.FILES}")
        form_data = request.POST
        try:
            with transaction.atomic():
                nome = request.POST.get('nome')
                descricao = request.POST.get('descricao')
                preco = request.POST.get('preco')
                categoria = request.POST.get('categoria')
                disponibilidade = request.POST.get('disponibilidade') == 'on'
                imagem = request.FILES.get('imagem')
                ingredientes = request.POST.get('ingredientes', '')
                opcoes_raw = request.POST.get('opcoes', '')

                if not all([nome, descricao, preco, categoria]):
                    logger.warning("Campos obrigatórios ausentes")
                    messages.error(request, 'Preencha todos os campos obrigatórios.')
                    return render(request, 'admin/menu.html', {
                        'items': ItemMenu.objects.all(),
                        'form_data': form_data
                    })

                # Validate preco
                try:
                    preco = Decimal(preco)
                    if preco < 0:
                        raise ValueError("Preço não pode ser negativo.")
                except (ValueError, TypeError):
                    logger.warning(f"Preço inválido: {preco}")
                    messages.error(request, 'Preço inválido. Use um valor numérico positivo.')
                    return render(request, 'admin/menu.html', {
                        'items': ItemMenu.objects.all(),
                        'form_data': form_data
                    })

                # Validate categoria
                valid_categories = [choice[0] for choice in ItemMenu._meta.get_field('categoria').choices]
                if categoria not in valid_categories:
                    logger.warning(f"Categoria inválida: {categoria}")
                    messages.error(request, f'Categoria inválida. Escolha: {", ".join(valid_categories)}.')
                    return render(request, 'admin/menu.html', {
                        'items': ItemMenu.objects.all(),
                        'form_data': form_data
                    })

                # Process opcoes
                opcoes = [opt.strip() for opt in opcoes_raw.split(',') if opt.strip()] if opcoes_raw else []

                logger.debug(f"Criando ItemMenu: nome={nome}, preco={preco}, categoria={categoria}")
                item = ItemMenu(
                    nome=nome,
                    descricao=descricao,
                    preco=preco,
                    categoria=categoria,
                    disponibilidade=disponibilidade,
                    imagem=imagem,
                    ingredientes=ingredientes,
                    opcoes=opcoes
                )
                item.full_clean()
                item.save()
                logger.info(f"Item '{nome}' salvo com sucesso, ID: {item.id}")
                messages.success(request, f'Item "{nome}" adicionado com sucesso.')
                return redirect('admin_menu')

        except ValidationError as e:
            logger.error(f"ValidationError ao salvar item: {str(e)}")
            messages.error(request, f'Erro ao adicionar item: {str(e)}')
            return render(request, 'admin/menu.html', {
                'items': ItemMenu.objects.all(),
                'form_data': form_data
            })
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar item: {str(e)}", exc_info=True)
            messages.error(request, f'Erro inesperado: {str(e)}')
            return render(request, 'admin/menu.html', {
                'items': ItemMenu.objects.all(),
                'form_data': form_data
            })

    logger.debug("Requisição GET para add_menu_item")
    return render(request, 'admin/menu.html', {'items': ItemMenu.objects.all()})

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def edit_menu_item(request, item_id):
    item = get_object_or_404(ItemMenu, id=item_id)

    # Obter as escolhas de categoria do modelo ItemMenu
    categoria_choices = ItemMenu._meta.get_field('categoria').choices

    if request.method == 'POST':
        form_data = {
            'nome': request.POST.get('nome', ''),
            'descricao': request.POST.get('descricao', ''),
            'preco': request.POST.get('preco', ''),
            'categoria': request.POST.get('categoria', ''),
            'disponibilidade': request.POST.get('disponibilidade') == 'on',
            'ingredientes': request.POST.get('ingredientes', ''),
            'opcoes': request.POST.get('opcoes', '')
        }
        try:
            with transaction.atomic():
                item.nome = request.POST.get('nome', item.nome)
                item.descricao = request.POST.get('descricao', item.descricao)
                preco = request.POST.get('preco', item.preco)
                item.categoria = request.POST.get('categoria', item.categoria)
                item.disponibilidade = request.POST.get('disponibilidade') == 'on'
                item.ingredientes = request.POST.get('ingredientes', item.ingredientes)
                opcoes_raw = request.POST.get('opcoes', '')

                # Validate preco
                try:
                    preco = Decimal(preco)
                    if preco < 0:
                        raise ValueError("Preço não pode ser negativo.")
                    item.preco = preco
                except (ValueError, TypeError):
                    logger.warning(f"Preço inválido: {preco}")
                    messages.error(request, 'Preço inválido. Use um valor numérico positivo.')
                    return render(request, 'admin/edit_menu.html', {
                        'item': item,
                        'form_data': form_data,
                        'categoria_choices': categoria_choices
                    })

                # Validate categoria
                valid_categories = [choice[0] for choice in categoria_choices]
                if item.categoria not in valid_categories:
                    logger.warning(f"Categoria inválida: {item.categoria}")
                    messages.error(request, f'Categoria inválida. Escolha: {", ".join(valid_categories)}.')
                    return render(request, 'admin/edit_menu.html', {
                        'item': item,
                        'form_data': form_data,
                        'categoria_choices': categoria_choices
                    })

                # Process opcoes
                item.opcoes = [opt.strip() for opt in opcoes_raw.split(',') if opt.strip()] if opcoes_raw else item.opcoes

                if request.FILES.get('imagem'):
                    item.imagem = request.FILES['imagem']
                    item.imagem.name = request.FILES['imagem'].name  # Preserva o nome original

                item.full_clean()
                item.save()
                logger.info(f"Item '{item.nome}' atualizado com sucesso, ID: {item.id}")
                messages.success(request, f'Item "{item.nome}" atualizado com sucesso.')
                return redirect('admin_menu')

        except ValidationError as e:
            logger.error(f"ValidationError ao atualizar item: {str(e)}")
            messages.error(request, f'Erro ao atualizar item: {str(e)}')
            return render(request, 'admin/edit_menu.html', {
                'item': item,
                'form_data': form_data,
                'categoria_choices': categoria_choices
            })
        except Exception as e:
            logger.error(f"Erro inesperado ao atualizar item: {str(e)}", exc_info=True)
            messages.error(request, 'Erro inesperado. Tente novamente.')
            return render(request, 'admin/edit_menu.html', {
                'item': item,
                'form_data': form_data,
                'categoria_choices': categoria_choices
            })

    # GET: Render the edit form with item data
    return render(request, 'admin/edit_menu.html', {
        'item': item,
        'categoria_choices': categoria_choices
    })

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def delete_menu_item(request, item_id):
    item = get_object_or_404(ItemMenu, id=item_id)
    
    if request.method == 'POST':
        try:
            nome = item.nome
            # Verificar se o item tem uma imagem associada
            if item.imagem:
                # Excluir o arquivo de imagem do sistema de arquivos
                image_path = item.imagem.path
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Imagem '{image_path}' excluída com sucesso.")
                else:
                    logger.warning(f"Imagem '{image_path}' não encontrada no sistema de arquivos.")
                # Limpar o campo imagem (opcional, já que o item será deletado)
                item.imagem = None
                item.save()
            
            # Excluir o item do banco de dados
            item.delete()
            logger.info(f"Item '{nome}' excluído com sucesso, ID: {item_id}")
            messages.success(request, f'Item "{nome}" excluído com sucesso.')
        except Exception as e:
            logger.error(f"Erro ao excluir item ID {item_id}: {str(e)}", exc_info=True)
            messages.error(request, f'Erro ao excluir item: {str(e)}. Tente novamente.')
    
    return redirect('admin_menu')

@login_required
@user_passes_test(is_admin, login_url='login')
def gerenciar_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-criado_em')
    
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        novo_status = request.POST.get('status')
        try:
            pedido = get_object_or_404(Pedido, id=pedido_id)
            if novo_status in [choice[0] for choice in Pedido.STATUS_CHOICES]:
                pedido.status = novo_status
                pedido.save()
                messages.success(request, f'Status do pedido #{pedido.id} atualizado para "{pedido.get_status_display()}".')
            else:
                messages.error(request, 'Status inválido.')
        except Exception as e:
            logger.error(f'Erro ao atualizar pedido: {str(e)}')
            messages.error(request, 'Erro ao atualizar o pedido. Tente novamente.')
    
    return render(request, 'admin/pedidos.html', {'pedidos': pedidos})

@login_required
def perfil(request):
    if request.method == 'POST':
        try:
            nome = request.POST.get('nome')
            email = request.POST.get('email')
            if not all([nome, email]):
                messages.error(request, 'Por favor, preencha todos os campos.')
            elif User.objects.filter(username=email).exclude(id=request.user.id).exists():
                messages.error(request, 'Este e-mail já está registrado.')
            else:
                request.user.first_name = nome
                request.user.email = email
                request.user.username = email  # Atualiza o username (usado para login)
                request.user.save()
                messages.success(request, 'Perfil atualizado com sucesso!')
                return redirect('perfil')
        except Exception as e:
            logger.error(f'Erro ao atualizar perfil: {str(e)}')
            messages.error(request, 'Erro ao atualizar o perfil. Tente novamente.')
    
    return render(request, 'perfil.html', {'user': request.user})

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                logger.info(f"Usuário {email} logado com sucesso.")
                return redirect('homepage')
            else:
                messages.error(request, 'Credenciais inválidas.')
        except User.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
    return render(request, 'auth/login.html', {})

def logout_view(request):
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('homepage')

def pagamento(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente=request.user)
    logger.debug(f"Acessando página de pagamento para Pedido #{pedido.id} de {request.user.email}")
    
    return render(request, 'pagamento.html', {
        'pedido': pedido,
        'itens': pedido.itens.all(),
        'total': pedido.total,
    })