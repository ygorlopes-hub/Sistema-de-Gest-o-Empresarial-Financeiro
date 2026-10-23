// Preenche apenas os campos vazios dos outros cheques no mesmo modal.
function sincronizarCamposVazios(container, campos) {
    container.addEventListener('change', (event) => {
        const campo = event.target;
        if (!campos.includes(campo.name) || campo.value.trim() === '') return;

        container.querySelectorAll(`input[name="${campo.name}"]`).forEach(input => {
            if (input !== campo && input.value === '') input.value = campo.value;
        });
    });
}

var socket = io();
socket.on('atualizar_tela', function() {
    var modalAberto = document.querySelector('.modal.show');
    if (modalAberto) {
        modalAberto.addEventListener('hidden.bs.modal', function () {
            location.reload();
        }, { once: true });
    } else {
        location.reload();
    }
});

const dadosBackend = JSON.parse(document.getElementById('dadosResumo').textContent);
const ctxCheques = document.getElementById('graficoCheques').getContext('2d');

new Chart(ctxCheques, {
    type: 'doughnut',
    data: {
        labels: ['Pendentes', 'Repassados', 'Compensados', 'Devolvidos'],
        datasets: [{
            data: dadosBackend,
            backgroundColor: ['#6c757d', '#0d6efd', '#198754', '#dc3545'],
            borderWidth: 2,
            hoverOffset: 4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: { font: { weight: 'bold' } }
            }
        },
        cutout: '65%'
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const emissoresData = JSON.parse(document.getElementById('dadosEmissores').textContent);
    const emissorMap = {};
    emissoresData.forEach(item => {
        if (item.nome) emissorMap[item.nome.trim()] = item.cnpj_cpf || '';
    });

    const containerCheques = document.getElementById('container-cheques');
    const selectQtd = document.getElementById('select-qtd-cheques');

    function renderizarFormsCheques(qtd) {
        const atual = containerCheques.children.length;

        if (qtd > atual) {
            for (let i = atual + 1; i <= qtd; i++) {

                const cardHTML = `
                    <div class="card shadow-sm border-secondary flex-shrink-0" style="width: 320px; flex: 0 0 auto;">
                        <div class="card-header bg-secondary text-white fw-bold py-2 d-flex justify-content-between align-items-center">
                            <span>Cheque #${i}</span>
                        </div>
                        <div class="card-body p-3 bg-white">
                            <div class="row g-2">
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">Data Recebimento</label>
                                    <input type="date" name="data_recebimento[]" class="form-control form-control-sm">
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">Cliente</label>
                                    <input type="text" name="cliente[]" class="form-control form-control-sm" list="listaClientes" autocomplete="off">
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">Emissor</label>
                                    <input type="text" name="emissor[]" class="form-control form-control-sm input-emissor-multi" list="listaEmissores" autocomplete="off" required>
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">CPF / CNPJ</label>
                                    <input type="text" name="cnpj_cpf[]" class="form-control form-control-sm input-cpf-multi" autocomplete="off">
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">Banco</label>
                                    <input type="text" name="banco[]" class="form-control form-control-sm" list="listaBancos" autocomplete="off">
                                </div>
                                <div class="col-6">
                                    <label class="form-label fw-bold small mb-1">Nº do Cheque</label>
                                    <input type="text" name="numero_cheque[]" class="form-control form-control-sm" required>
                                </div>
                                <div class="col-6">
                                    <label class="form-label fw-bold small mb-1">Vencimento</label>
                                    <input type="date" name="data_bom_para[]" class="form-control form-control-sm" required>
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">Valor (R$)</label>
                                    <input type="number" step="0.01" name="valor[]" class="form-control form-control-sm" required>
                                </div>
                                <div class="col-6">
                                    <label class="form-label fw-bold small mb-1">Destino</label>
                                    <input type="text" name="destino[]" class="form-control form-control-sm" list="listaDestinos" autocomplete="off">
                                </div>
                                <div class="col-6">
                                    <label class="form-label fw-bold small mb-1">Data Repasse</label>
                                    <input type="date" name="data_repasse[]" class="form-control form-control-sm">
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1 text-primary">Info. Repasse</label>
                                    <textarea name="info_repasse[]" class="form-control form-control-sm border-primary" rows="2"></textarea>
                                </div>
                                <div class="col-12">
                                    <label class="form-label fw-bold small mb-1">Observações</label>
                                    <input type="text" name="observacoes[]" class="form-control form-control-sm">
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                containerCheques.insertAdjacentHTML('beforeend', cardHTML);
            }
        }
        else if (qtd < atual) {
            for (let i = atual; i > qtd; i--) {
                containerCheques.removeChild(containerCheques.lastElementChild);
            }
        }
    }
    renderizarFormsCheques(1);

    if (selectQtd) {
        selectQtd.addEventListener('change', (e) => {
            renderizarFormsCheques(parseInt(e.target.value));
        });
    }

    const modalNovoChequeEl = document.getElementById('modalNovoCheque');
    if (modalNovoChequeEl) {
        modalNovoChequeEl.addEventListener('show.bs.modal', function () {
            if (selectQtd) selectQtd.value = "1";
            containerCheques.innerHTML = '';
            renderizarFormsCheques(1);
        });
    }

    if (containerCheques) {
        containerCheques.addEventListener('input', function(e) {
            if (e.target.classList.contains('input-emissor-multi')) {
                const valorDigitado = e.target.value.trim();
                if (emissorMap.hasOwnProperty(valorDigitado)) {
                    const card = e.target.closest('.card-body');
                    const cpfInput = card ? card.querySelector('.input-cpf-multi') : null;
                    if (cpfInput) cpfInput.value = emissorMap[valorDigitado];
                }
            }
        });
        sincronizarCamposVazios(containerCheques, ['data_recebimento[]', 'cliente[]']);
    }
});

document.addEventListener("DOMContentLoaded", function() {
    const btnToggle = document.getElementById('btnToggleSidebar');
    const barraLateral = document.getElementById('barraLateral');

    if (barraLateral) {
        barraLateral.classList.add('sidebar-recolhida');
        if (btnToggle) {
            btnToggle.addEventListener('click', function() {
                barraLateral.classList.toggle('sidebar-recolhida');
            });
        }
    }
});
    document.addEventListener('DOMContentLoaded', () => {
        const checkTodos = document.getElementById('checkTodos');
        const checksCheque = document.querySelectorAll('.check-cheque');
        const barraAcoesLote = document.getElementById('barraAcoesLote');
        const contadores = document.querySelectorAll('.contadorSelecionados');
        const spanValorTotal = document.getElementById('valorTotalSelecionado');

        function atualizarEstadoBotao() {
            const selecionados = document.querySelectorAll('.check-cheque:checked');
            const qtd = selecionados.length;

            contadores.forEach(c => c.textContent = qtd);
            let somaValores = 0;
            selecionados.forEach(chk => {
                const tr = document.getElementById(`linha-cheque-${chk.value}`);
                if (tr) {
                    const valor = parseFloat(tr.getAttribute('data-valor')) || 0;
                    somaValores += valor;
                }
            });
            if (spanValorTotal) {
                spanValorTotal.textContent = somaValores.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            }

            if (barraAcoesLote) {
                barraAcoesLote.style.display = qtd > 0 ? 'flex' : 'none';
            }
        }

        if (checkTodos) {
            checkTodos.addEventListener('change', (e) => {
                checksCheque.forEach(chk => chk.checked = e.target.checked);
                atualizarEstadoBotao();
            });
        }

        checksCheque.forEach(chk => {
            chk.addEventListener('change', () => {
                if (!chk.checked && checkTodos) checkTodos.checked = false;
                atualizarEstadoBotao();
            });
        });
    });
    function exportarSelecionados() {
        const selecionados = document.querySelectorAll('.check-cheque:checked');
        const formExportar = document.getElementById('formExportarLote');
        formExportar.innerHTML = ''; // Limpa envios anteriores

        selecionados.forEach(chk => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'cheques_selecionados[]';
            input.value = chk.value;
            formExportar.appendChild(input);
        });

        formExportar.submit();
    }
    function abrirModalRomaneio() {
        const selecionados = document.querySelectorAll('.check-cheque:checked');
        const containerHidden = document.getElementById('hiddenInputsRomaneio');
        containerHidden.innerHTML = '';

        let destinoComum = '';

        selecionados.forEach((chk, index) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'cheques_selecionados[]';
            input.value = chk.value;
            containerHidden.appendChild(input);
            if (index === 0) {
                const tr = document.getElementById(`linha-cheque-${chk.value}`);
                if (tr && tr.getAttribute('data-destino')) {
                    destinoComum = tr.getAttribute('data-destino');
                }
            }
        });

        if (destinoComum !== '') {
            document.getElementById('inputDestinatarioRomaneio').value = destinoComum;
        }
        const hoje = new Date().toISOString().split('T')[0];
        document.getElementById('dataRomaneioInput').value = hoje;

        new bootstrap.Modal(document.getElementById('modalRomaneio')).show();
    }
function abrirModalEditarLote() {
    const selecionados = document.querySelectorAll('.check-cheque:checked');
    const container = document.getElementById('container-cheques-editar');
    container.innerHTML = ''; // Limpa os antigos

    let contador = 1;

    selecionados.forEach(chk => {
        const tr = document.getElementById(`linha-cheque-${chk.value}`);
        const data = {
            id: tr.getAttribute('data-id'),
            banco: tr.getAttribute('data-banco'),
            numero: tr.getAttribute('data-numero'),
            cliente: tr.getAttribute('data-cliente'),
            emissor: tr.getAttribute('data-emissor'),
            cnpj: tr.getAttribute('data-cnpj'),
            dataRec: tr.getAttribute('data-datarec'),
            dataVenc: tr.getAttribute('data-datavenc'),
            valor: tr.getAttribute('data-valor'),
            destino: tr.getAttribute('data-destino'),
            dataRep: tr.getAttribute('data-datarep'),
            infoRep: tr.getAttribute('data-inforep'),
            obs: tr.getAttribute('data-obs')
        };

        const card = document.createElement('div');
        card.className = 'card shadow-sm border-primary';
        card.style.minWidth = '320px';
        card.style.flex = '0 0 auto';
        card.innerHTML = `
            <div class="card-header bg-primary text-white fw-bold py-2 d-flex justify-content-between">
                <span><i class="bi bi-pencil-square"></i> Editando Cheque ${contador}</span>
                <span class="badge bg-light text-primary">Nº ${data.numero}</span>
            </div>
            <div class="card-body p-3 bg-white">
                <input type="hidden" name="id_cheque[]" value="${data.id}">

                <div class="row g-2 mb-2">
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1 text-muted">Data Recebimento</label>
                        <input type="date" name="data_recebimento[]" class="form-control form-control-sm bg-light" value="${data.dataRec}">
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1">Cliente</label>
                        <input type="text" name="cliente[]" class="form-control form-control-sm border-primary" list="listaClientes" autocomplete="off" value="${data.cliente}">
                    </div>
                </div>

                <div class="row g-2 mb-2">
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1 text-muted">Emissor</label>
                        <input type="text" name="emissor[]" class="form-control form-control-sm bg-light" list="listaEmissores" autocomplete="off" value="${data.emissor}">
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1 text-muted">CNPJ / CPF</label>
                        <input type="text" name="cnpj_cpf[]" class="form-control form-control-sm bg-light" list="listaCnpjs" autocomplete="off" value="${data.cnpj}">
                    </div>
                </div>

                <div class="row g-2 mb-2">
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1">Banco</label>
                        <input type="text" name="banco[]" class="form-control form-control-sm border-primary" list="listaBancos" autocomplete="off" value="${data.banco}">
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1">Nº Cheque</label>
                        <input type="text" name="numero_cheque[]" class="form-control form-control-sm border-primary" value="${data.numero}" required readonly title="O número do cheque não pode ser alterado em lote.">
                    </div>
                </div>

                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1">Venc. (Bom Para)</label>
                        <input type="date" name="data_bom_para[]" class="form-control form-control-sm border-primary" value="${data.dataVenc}" required readonly title="O vencimento não pode ser alterado em lote.">
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1">Valor (R$)</label>
                        <input type="number" step="0.01" name="valor[]" class="form-control form-control-sm border-primary" value="${data.valor}" required readonly title="O valor não pode ser alterado em lote.">
                    </div>
                </div>

                <hr class="text-muted my-2">

                <div class="row g-2 mb-2">
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1 text-muted">Destino</label>
                        <input type="text" name="destino[]" class="form-control form-control-sm bg-light" list="listaDestinos" autocomplete="off" value="${data.destino}">
                    </div>
                    <div class="col-6">
                        <label class="form-label small fw-bold mb-1 text-muted">Data Repasse</label>
                        <input type="date" name="data_repasse[]" class="form-control form-control-sm bg-light" value="${data.dataRep}">
                    </div>
                </div>

                <div class="mb-2">
                    <label class="form-label small fw-bold mb-1 text-primary">Info. do Repasse</label>
                    <textarea name="info_repasse[]" class="form-control form-control-sm border-primary bg-light" rows="1">${data.infoRep}</textarea>
                </div>
                <div class="mb-0">
                    <label class="form-label small fw-bold mb-1 text-muted">Observações</label>
                    <input type="text" name="observacoes[]" class="form-control form-control-sm bg-light" value="${data.obs}">
                </div>
            </div>
        `;
        container.appendChild(card);
        contador++;
    });
    new bootstrap.Modal(document.getElementById('modalEditarLote')).show();
}
    const containerChequesEditar = document.getElementById('container-cheques-editar');
    if (containerChequesEditar) {
        sincronizarCamposVazios(containerChequesEditar, ['destino[]', 'data_repasse[]']);
    }
