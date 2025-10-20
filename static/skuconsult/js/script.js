// --- CONFIGURAÇÕES GLOBAIS ---
let todosOsProdutos = []; 
let produtosAtuais = []; 
const PRODUTOS_POR_PAGINA = 12;
let paginaAtual = 1;
let isLoading = false;

// --- INICIALIZAÇÃO ---
window.onload = function() {
    console.log('🔄 Iniciando carregamento de produtos...');
    const mensagemInfo = document.getElementById('mensagemInfo');
    mensagemInfo.innerText = '🔄 Carregando produtos do Google Sheets...';
    
    // Busca os produtos da API Flask (que lê do Google Sheets)
    fetch('/api/produtos')
        .then(response => {
            console.log('📡 Resposta recebida:', response.status);
            if (!response.ok) {
                throw new Error(`Erro HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('📦 Dados recebidos:', data);
            
            if (data.success) {
                todosOsProdutos = data.produtos;
                produtosAtuais = todosOsProdutos;

                console.log(`✓ ${data.total} produtos carregados do Google Sheets`);
                
                mensagemInfo.innerText = `✓ ${data.total} produtos carregados`;
                mensagemInfo.style.color = '#28a745';
                
                // Esconde a mensagem após 2 segundos
                setTimeout(() => {
                    mensagemInfo.innerText = '';
                }, 2000);

                document.getElementById('skuInput').addEventListener('input', handleFilter);
                window.addEventListener('scroll', handleScroll);

                carregarMaisProdutos();
            } else {
                throw new Error(data.error || 'Erro desconhecido ao carregar produtos');
            }
        })
        .catch(error => {
            console.error('❌ Erro:', error);
            mensagemInfo.innerText = `❌ ${error.message}`;
            mensagemInfo.style.color = '#dc3545';
        });
};

// --- LÓGICA DE CARREGAMENTO E RENDERIZAÇÃO ---
function carregarMaisProdutos() {
    const totalProdutos = produtosAtuais.length;
    console.log(`📊 Carregando mais produtos. Página: ${paginaAtual}, Total: ${totalProdutos}`);
    
    if (isLoading || ((paginaAtual - 1) * PRODUTOS_POR_PAGINA >= totalProdutos && totalProdutos > 0)) {
        console.log('⏸️ Não há mais produtos para carregar');
        return;
    }

    isLoading = true;
    const startIndex = (paginaAtual - 1) * PRODUTOS_POR_PAGINA;
    const endIndex = startIndex + PRODUTOS_POR_PAGINA;
    const produtosParaRenderizar = produtosAtuais.slice(startIndex, endIndex);
    
    console.log(`📦 Renderizando ${produtosParaRenderizar.length} produtos (${startIndex} a ${endIndex})`);
    
    renderizarProdutos(produtosParaRenderizar);
    paginaAtual++;
    isLoading = false;
}

function renderizarProdutos(produtos) {
    const listaDiv = document.getElementById('listaProdutos');
    const mensagemInfo = document.getElementById('mensagemInfo');

    if (listaDiv.innerHTML === '' && produtos.length === 0) {
        mensagemInfo.innerText = 'Nenhum produto encontrado.';
        mensagemInfo.style.color = '#666';
        return;
    }
    mensagemInfo.innerText = '';

    produtos.forEach(produto => {
        const sku = produto.COD_PRODUTO || 'N/A';
        const nome = produto.NOMEPRODUTOECOMM || 'Nome indisponível';
        const ean = produto.COD_BARRAS || 'N/A';
        const imagemUrl = produto.URLECOMMERCEIMG || 'https://via.placeholder.com/250';
        const productURL = produto.PRODUCTURL || '#';

        // Escapar caracteres especiais para evitar problemas no HTML
        const nomeEscapado = nome.replace(/'/g, "\\'").replace(/"/g, '&quot;');

        const cardHtml = `
            <div class="produto-card">
                <img class="produto-imagem" src="${imagemUrl}" alt="${nomeEscapado}" onerror="this.src='https://via.placeholder.com/250?text=Sem+Imagem'">
                <div class="produto-info">
                    <p><strong>SKU:</strong> <span>${sku}</span></p>
                    
                    <div class="nome-container">
                        <p><strong>Nome:</strong> <span>${nome}</span></p>
                        <button class="btn-copiar" title="Copiar nome" onclick="copiarTexto('${nomeEscapado}', this)">📋</button>
                    </div>
                    <p><strong>EAN:</strong> <span>${ean}</span></p>
                    <p><strong>URL da Imagem:</strong> 
                        <a href="${imagemUrl}" target="_blank" rel="noopener noreferrer" style="font-size: 0.85rem; word-break: break-all;">${imagemUrl}</a>
                    </p>
                    <p><strong>URL do Produto:</strong> 
                        <a href="${productURL}" target="_blank" rel="noopener noreferrer" style="font-size: 0.85rem; word-break: break-all;">${productURL}</a>
                    </p>

                    <a class="produto-download-btn" href="${imagemUrl}" download="imagem_${sku}" target="_blank">
                        <button>Baixar Imagem</button>
                    </a>
                </div>
            </div>
        `;
        listaDiv.insertAdjacentHTML('beforeend', cardHtml);
    });
    
    console.log(`✅ ${produtos.length} produtos renderizados`);
}

// --- GERENCIADORES DE EVENTOS ---
function handleScroll() {
    const pertoDoFim = (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 200;
    if (pertoDoFim) {
        carregarMaisProdutos();
    }
}

function handleFilter() {
    const termoBusca = document.getElementById('skuInput').value.toLowerCase();
    console.log(`🔍 Filtrando por: "${termoBusca}"`);
    
    produtosAtuais = todosOsProdutos.filter(produto => {
        const skuString = String(produto.COD_PRODUTO).toLowerCase();
        const nomeString = String(produto.NOMEPRODUTOECOMM).toLowerCase();
        const eanString = String(produto.COD_BARRAS).toLowerCase();
        
        return skuString.includes(termoBusca) || 
               nomeString.includes(termoBusca) || 
               eanString.includes(termoBusca);
    });
    
    console.log(`📊 Encontrados ${produtosAtuais.length} produtos`);
    
    paginaAtual = 1;
    document.getElementById('listaProdutos').innerHTML = '';
    document.getElementById('mensagemInfo').innerText = '';
    carregarMaisProdutos();
}

// --- FUNÇÃO DE CÓPIA ---
function copiarTexto(texto, elementoBotao) {
    navigator.clipboard.writeText(texto).then(() => {
        const iconeOriginal = elementoBotao.innerHTML;
        elementoBotao.innerHTML = '✅';
        elementoBotao.disabled = true;

        setTimeout(() => {
            elementoBotao.innerHTML = iconeOriginal;
            elementoBotao.disabled = false;
        }, 2000);
    }).catch(err => {
        console.error('Erro ao copiar o nome do produto: ', err);
        alert('Não foi possível copiar o nome.');
    });
}