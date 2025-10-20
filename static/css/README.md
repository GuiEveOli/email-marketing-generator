# CSS Unificado - Ferramentas Email Marketing

## 📋 Estrutura

Este diretório contém os arquivos CSS do projeto:

- **`main.css`** - Arquivo CSS unificado com todos os estilos do sistema
- **`style.css`** - Arquivo antigo (mantido por compatibilidade, mas não mais utilizado)

## ✨ O que mudou?

Todos os estilos inline e CSS separados foram unificados em um único arquivo `main.css` para:

- ✅ Facilitar a edição e manutenção
- ✅ Evitar inconsistências no layout
- ✅ Centralizar todas as variáveis CSS
- ✅ Melhorar a organização do código
- ✅ Reduzir duplicação de estilos

## 🎨 Estrutura do `main.css`

O arquivo está organizado em seções:

### 1. Reset e Variáveis
- Variáveis CSS globais (cores, sombras, etc.)
- Reset básico de estilos

### 2. Navbar (Compartilhada)
- Estilos da barra de navegação
- Links e branding
- Estados ativos e hover

### 3. Hub (Index)
- Página principal
- Cards de ferramentas
- Gradiente de fundo
- Responsividade

### 4. Gerador
- Layout de 2 colunas
- Seção de busca e produtos
- Seção de configurações
- Drag & drop de produtos
- Sugestões e dropdown
- Toast notifications
- Loading overlay

### 5. SKU Consult
- Grid de produtos
- Cards de visualização
- Botões de download e cópia

### 6. Responsive
- Media queries para mobile
- Ajustes de layout

## 🔧 Como editar?

Para fazer alterações no layout:

1. Abra `/static/css/main.css`
2. Localize a seção correspondente
3. Faça as alterações necessárias
4. Salve o arquivo

**IMPORTANTE:** Não edite estilos inline nos arquivos HTML. Todos os estilos devem estar no `main.css`.

## 📱 Classes especiais por página

Cada página usa uma classe no `<body>` para aplicar estilos específicos:

- **Hub:** `<body class="hub-page">`
- **Gerador:** `<body class="gerador-page">`
- **SKU Consult:** `<body class="skuconsult-page">`

## 🎨 Variáveis CSS disponíveis

```css
--primary-color: #122447;
--secondary-color: #034abb;
--accent-color: #677de8;
--light-gray: #f8f9fa;
--gray-border: #dee2e6;
--text-color: #3c3e41;
--card-shadow: 0 4px 8px rgba(0,0,0,.1);
```

Use essas variáveis em vez de cores hard-coded para manter a consistência.

## 📂 Arquivos atualizados

Os seguintes arquivos HTML foram atualizados para usar o novo CSS:

- ✅ `templates/index.html`
- ✅ `templates/gerador.html`
- ✅ `templates/skuconsult/index.html`

## 🗑️ Arquivo antigo

O arquivo `style.css` foi mantido por compatibilidade, mas não está mais sendo usado. Você pode removê-lo com segurança após confirmar que tudo funciona corretamente.
