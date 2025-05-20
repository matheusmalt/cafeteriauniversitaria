# Projeto Integrador: Cafeteria

Bem-vindo ao repositório do **Projeto Integrador Transdisciplinar em Sistemas de Informação I - Turma 001**, da Universidade Cruzeiro do Sul. Este projeto implementa uma aplicação web para gerenciamento de uma cafeteria, integrando teoria e prática em uma solução funcional.

## Tecnologias Utilizadas

- **Python**: Lógica de backend e processamento de dados.
- **Django**: Framework web para desenvolvimento rápido e seguro.
- **HTML/CSS**: Estrutura e estilização das páginas.
- **JavaScript**: Interatividade no frontend (embutido nos templates HTML).
- **Bootstrap**: Design responsivo e componentes de interface.
- **SQLite**: Banco de dados leve para armazenamento.

## Mapa do Site

O aplicativo Cafeteria oferece as seguintes funcionalidades principais:

| **Seção**          | **Funcionalidade**                  | **Descrição**                                                                 |
|--------------------|-------------------------------------|-------------------------------------------------------------------------------|
| Página Inicial     | Boas-vindas e Visão Geral          | Apresenta o sistema da cafeteria com links para as principais seções.         |
| Cardápio           | Exibição de Itens                  | Lista de produtos (bebidas, lanches) com preços e detalhes.                   |
| Pedidos            | Gerenciamento de Pedidos           | Interface para criar, visualizar e atualizar pedidos (CRUD).                  |
| Autenticação       | Login/Logout de Usuários           | Sistema de autenticação para funcionários ou administradores (via Django).    |
| Estoque            | Controle de Estoque                | Gerenciamento de insumos e produtos disponíveis na cafeteria.                 |

## Estrutura do Repositório

- **/project**: Código-fonte do backend (Django, Python).
  - `models.py`: Modelos do banco de dados (ex.: Pedido, Produto, Estoque).
  - `views.py`: Lógica das visualizações do aplicativo.
  - `urls.py`: Rotas da aplicação.
- **/templates**: Arquivos HTML com JavaScript embutido para renderização das páginas.
- **/media**: Imagens e outros arquivos de mídia.
- **/db.sqlite3**: Banco de dados SQLite.
- **requirements.txt**: Dependências do projeto.
- **manage.py**: Script de gerenciamento do Django.

## Como Executar

1. Clone o repositório:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure o banco de dados:
   ```bash
   python manage.py migrate
   ```
4. Inicie o servidor:
   ```bash
   python manage.py runserver
   ```
5. Acesse a aplicação em: `http://localhost:8000`

## Contribuições

Contribuições são bem-vindas! Para sugerir melhorias ou correções, abra uma **issue** ou envie um **pull request**.

## Licença

Este projeto é licenciado sob a [MIT License](LICENSE).
