# Sistema Corporativo de Gestão

Aplicação web desenvolvida para otimizar o controle operacional corporativo, englobando a gestão de estoque, controle financeiro de contas e gerenciamento avançado de cheques.

## Tecnologias Utilizadas

Backend: Python (Flask, Flask-SocketIO)
Banco de Dados: MySQL (PyMySQL)
Frontend: Bootstrap 5, HTML5, CSS3, JavaScript, Chart.js
Manipulação de Dados: Pandas e OpenPyXL para importação e exportação de planilhas Excel

## Principais Funcionalidades

Autenticação e Controle de Acesso (RBAC): Sistema de login seguro com distinção de níveis de permissão entre Administrador e Usuário Comum.
Auditoria em Tempo Real: Registro detalhado de endereços IP, horários e ações executadas por cada usuário no sistema.
Módulo de Cheques: Recursos de filtros avançados, paginação, resumos automáticos e atualização dinâmica de tela via WebSockets.
Gestão Financeira e Estoque: Alertas visuais automáticos parametrizados para prazos de vencimento e níveis de estoque mínimo.