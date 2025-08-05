class HorarioView {
    constructor() {
        this.turnoSelect = document.getElementById('turno');
        this.btnGerar = document.getElementById('btnGerar');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressBar = document.getElementById('progressBar');
        this.mensagem = document.getElementById('mensagem');
        this.container = document.getElementById('horarios-container');
        this.dias = ['seg', 'ter', 'qua', 'qui', 'sex'];
        this.diasNomes = {
            'seg': 'Segunda',
            'ter': 'Terça',
            'qua': 'Quarta',
            'qui': 'Quinta',
            'sex': 'Sexta'
        };
        
        this.professoresCores = {};
        this.dadosHorario = null;
        
        // Inicializar estado de seleções persistentes
        this.selecoesPersistentes = {
            disponibilidades: {},
            restricoes: {},
            excecoes: {
                disciplinaDuasAulas: [],
                disciplinaConsecutivas: [],
                professorDuasAulas: []
            }
        };
        
        // Carregar seleções salvas
        this.carregarSelecoesPersistentes();
        
        // Inicializar listeners de persistência
        this.inicializarListenersPersistencia();
        
        // Adicionar propriedades para ML
        this.metricasML = null;
        
        // Inicializar visualização de ML
        this.initML();
        
        this.init();
    }
    
    init() {
        this.btnGerar.addEventListener('click', () => this.carregarHorario());
        
        // Adicionar event listeners para os novos botões
        document.getElementById('btnDisponibilidades').addEventListener('click', () => this.navegarParaDisponibilidades());
        document.getElementById('btnRestricoes').addEventListener('click', () => this.navegarParaRestricoes());
        document.getElementById('btnExcecoes').addEventListener('click', () => this.navegarParaExcecoes());
        document.getElementById('btnHorariosProfessores').addEventListener('click', () => this.navegarParaHorariosProfessores());

        // Adicionar evento para botão de voltar ao topo
        const btnVoltarTopo = document.getElementById('btnVoltarTopo');
        btnVoltarTopo.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        // Mostrar/ocultar botão de voltar ao topo
        window.addEventListener('scroll', () => {
            const scrollPosition = window.pageYOffset;
            
            if (scrollPosition > 300) {
                btnVoltarTopo.style.display = 'block';
            } else {
                btnVoltarTopo.style.display = 'none';
            }
        });
    }

    async initML() {
        // Carregar métricas iniciais
        await this.carregarMetricasML();
        
        // Adicionar botão de treinar modelo
        const btnTreinarML = document.createElement('button');
        btnTreinarML.id = 'btnTreinarML';
        btnTreinarML.className = 'btn btn-primary mt-3 mb-3';
        btnTreinarML.textContent = 'Treinar Modelo ML';
        btnTreinarML.addEventListener('click', () => this.treinarModelo());
        
        // Adicionar ao container de botões existente
        document.querySelector('.row.mb-3').appendChild(btnTreinarML);
    }
    
    async carregarMetricasML() {
        try {
            const resposta = await fetch('/api/ml/metricas');
            if (!resposta.ok) {
                throw new Error('Erro ao carregar métricas');
            }
            
            this.metricasML = await resposta.json();
            this.renderizarMetricasML();
            
        } catch (error) {
            console.error('Erro ao carregar métricas ML:', error);
            this.mostrarMensagem('Erro ao carregar métricas de ML', 'warning');
        }
    }
    
    renderizarMetricasML() {
        if (!this.metricasML) return;
        
        const containerMetricas = document.createElement('div');
        containerMetricas.className = 'card mt-4 mb-4';
        containerMetricas.innerHTML = `
            <div class="card-header">
                <h5 class="mb-0">Métricas de Machine Learning</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <div class="metric-item">
                            <h6>Total de Horários Gerados</h6>
                            <p class="h4">${this.metricasML.total_horarios_gerados}</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="metric-item">
                            <h6>Score Médio</h6>
                            <p class="h4">${this.metricasML.score_medio.toFixed(2)}</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="metric-item">
                            <h6>Score Máximo</h6>
                            <p class="h4">${this.metricasML.score_maximo.toFixed(2)}</p>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <h6>Evolução dos Scores</h6>
                    <canvas id="chartEvolucao"></canvas>
                </div>
                
                <div class="mt-3 text-muted">
                    <small>Último treino: ${new Date(this.metricasML.data_ultimo_treino * 1000).toLocaleString()}</small>
                </div>
            </div>
        `;
        
        // Adicionar ao container principal
        this.container.insertBefore(containerMetricas, this.container.firstChild);
        
        // Renderizar gráfico
        this.renderizarGraficoEvolucao();
    }
    
    renderizarGraficoEvolucao() {
        const ctx = document.getElementById('chartEvolucao').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: this.metricasML.evolucao_scores.length}, (_, i) => `Geração ${i+1}`),
                datasets: [{
                    label: 'Score',
                    data: this.metricasML.evolucao_scores,
                    borderColor: '#007bff',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Evolução dos Scores'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    async treinarModelo() {
        try {
            const btnTreinarML = document.getElementById('btnTreinarML');
            btnTreinarML.disabled = true;
            btnTreinarML.textContent = 'Treinando...';
            
            const resposta = await fetch('/api/ml/treinar', {
                method: 'POST'
            });
            
            if (!resposta.ok) {
                throw new Error('Erro ao treinar modelo');
            }
            
            this.mostrarMensagem('Modelo treinado com sucesso!', 'success');
            
            // Atualizar métricas
            await this.carregarMetricasML();
            
        } catch (error) {
            console.error('Erro ao treinar modelo:', error);
            this.mostrarMensagem('Erro ao treinar modelo', 'danger');
        } finally {
            const btnTreinarML = document.getElementById('btnTreinarML');
            btnTreinarML.disabled = false;
            btnTreinarML.textContent = 'Treinar Modelo ML';
        }
    }

    async navegarParaRestricoes() {
        try {
            // Buscar dados das disciplinas
            const resposta = await fetch('/api/disciplinas');
            
            if (!resposta.ok) {
                // Tentar obter detalhes do erro
                const erro = await resposta.json();
                console.error('Detalhes do erro:', erro);
                throw new Error(erro.error || 'Erro desconhecido ao carregar disciplinas');
            }
            
            const dadosDisciplinasOriginal = await resposta.json();

            // Verificar se há dados
            if (!dadosDisciplinasOriginal || dadosDisciplinasOriginal.length === 0) {
                throw new Error('Nenhuma disciplina encontrada');
            }

            // Remover duplicatas baseado no nome da disciplina e ordenar alfabeticamente
            const disciplinasUnicas = new Map();

            dadosDisciplinasOriginal.forEach(disciplina => {
                // Garantir que todos os campos de restrição sejam strings válidas
                const disciplinaSegura = {...disciplina};
                ['r_seg', 'r_ter', 'r_qua', 'r_qui', 'r_sex'].forEach(dia => {
                    disciplinaSegura[dia] = (disciplinaSegura[dia] || '').toString().trim();
                });

                if (!disciplinasUnicas.has(disciplinaSegura.disciplina)) {
                    disciplinasUnicas.set(disciplinaSegura.disciplina, disciplinaSegura);
                }
            });

            // Converter para array e ordenar alfabeticamente
            const dadosDisciplinas = Array.from(disciplinasUnicas.values())
                .sort((a, b) => a.disciplina.localeCompare(b.disciplina));

            // Limpar container
            this.container.innerHTML = '';

            // Criar container para conteúdo
            const containerConteudo = document.createElement('div');
            containerConteudo.id = 'restricoes-container';
            containerConteudo.className = 'container-fluid';

            // Criar botão de voltar
            const botaoVoltar = document.createElement('button');
            botaoVoltar.className = 'btn btn-secondary mb-3';
            botaoVoltar.innerHTML = '← Voltar para Horário Principal';
            botaoVoltar.addEventListener('click', () => {
                this.container.innerHTML = '';
                this.renderizarHorario(this.dadosHorario);
                
                // Manter botões visíveis
                document.getElementById('btnHorariosProfessores').classList.remove('d-none');
            });

            // Criar título
            const titulo = document.createElement('h2');
            titulo.textContent = 'Restrições de Disciplinas';
            titulo.className = 'text-center mb-4';

            // Adicionar botão de salvar restrições
            const btnSalvarRestricoes = document.createElement('button');
            btnSalvarRestricoes.id = 'btnSalvarRestricoes';
            btnSalvarRestricoes.className = 'btn btn-primary mt-3 mb-3';
            btnSalvarRestricoes.textContent = 'Salvar Restrições';
            btnSalvarRestricoes.addEventListener('click', () => this.salvarRestricoes());

            // Adicionar botão de voltar e título ao container
            containerConteudo.appendChild(botaoVoltar);
            containerConteudo.appendChild(titulo);
            containerConteudo.appendChild(btnSalvarRestricoes);

            // Criar container para tabela
            const containerTabela = document.createElement('div');
            containerTabela.className = 'table-responsive';

            // Criar tabela
            const tabela = document.createElement('table');
            tabela.className = 'table table-bordered table-striped';

            // Cabeçalho da tabela
            const cabecalho = `
                <thead>
                    <tr>
                        <th>Disciplina</th>
                        <th class="text-center">Seg</th>
                        <th class="text-center">Ter</th>
                        <th class="text-center">Qua</th>
                        <th class="text-center">Qui</th>
                        <th class="text-center">Sex</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    ${dadosDisciplinas.map((disciplina, index) => `
                        <tr>
                            <td title="${disciplina.disciplina}">
                                ${this.simplificarNomeDisciplina(disciplina.disciplina)}
                            </td>
                            ${['r_seg', 'r_ter', 'r_qua', 'r_qui', 'r_sex'].map(dia => `
                                <td class="text-center">
                                    ${[1,2,3,4,5,6,7].map(hora => `
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input dia-checkbox" type="checkbox" 
                                                   id="${disciplina.disciplina}-${dia}-${hora}"
                                                   data-disciplina="${disciplina.disciplina}"
                                                   data-dia="${dia}"
                                                   data-hora="${hora}"
                                                   value="${hora}"
                                                   ${disciplina[dia] && disciplina[dia].split(',').includes(hora.toString()) ? 'checked' : ''}>
                                            <label class="form-check-label" for="${disciplina.disciplina}-${dia}-${hora}">
                                                ${hora}
                                            </label>
                                        </div>
                                    `).join('')}
                                </td>
                            `).join('')}
                            <td class="text-center">
                                <div class="btn-group-vertical btn-group-sm" role="group">
                                    <div class="btn-group btn-group-sm mb-1" role="group">
                                        <button type="button" class="btn btn-success btn-selecionar-linha" data-linha="${index}">
                                            Sel. Tudo
                                        </button>
                                        <button type="button" class="btn btn-danger btn-limpar-linha" data-linha="${index}">
                                            Limpar
                                        </button>
                                    </div>
                                    <div class="btn-group btn-group-sm" role="group">
                                        <button type="button" class="btn btn-warning btn-limpar-ter" data-linha="${index}">
                                            BH
                                        </button>
                                        <button type="button" class="btn btn-info btn-limpar-qua" data-linha="${index}">
                                            BN
                                        </button>
                                        <button type="button" class="btn btn-primary btn-limpar-qui" data-linha="${index}">
                                            BL
                                        </button>
                                        <button type="button" class="btn btn-secondary btn-limpar-seg-sex" data-linha="${index}">
                                            PCA
                                        </button>
                                    </div>
                                    <div class="btn-group btn-group-sm mt-1" role="group">
                                        ${[1,2,3,4,5,6,7].map(numero => `
                                            <button type="button" class="btn btn-outline-primary btn-selecionar-hora" 
                                                    data-linha="${index}" 
                                                    data-hora="${numero}">
                                                ${numero}
                                            </button>
                                        `).join('')}
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            `;

            tabela.innerHTML = cabecalho;
            containerTabela.appendChild(tabela);
            containerConteudo.appendChild(containerTabela);

            // Adicionar informação do total de linhas
            const totalLinhas = document.createElement('div');
            totalLinhas.className = 'alert alert-info mt-3';
            totalLinhas.innerHTML = `<strong>Total de Disciplinas:</strong> ${dadosDisciplinas.length}`;
            containerConteudo.appendChild(totalLinhas);

            this.container.appendChild(containerConteudo);

            // Adicionar event listeners para botões de seleção
            document.querySelectorAll('.btn-selecionar-linha').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxes = linha.querySelectorAll('.dia-checkbox');
                    checkboxes.forEach(checkbox => {
                        checkbox.checked = true;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-linha').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxes = linha.querySelectorAll('.dia-checkbox');
                    checkboxes.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            // Novos botões de ações específicas
            document.querySelectorAll('.btn-limpar-ter').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesTer = linha.querySelectorAll('.dia-checkbox[data-dia="r_ter"]');
                    checkboxesTer.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-qua').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesQua = linha.querySelectorAll('.dia-checkbox[data-dia="r_qua"]');
                    checkboxesQua.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-qui').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesQui = linha.querySelectorAll('.dia-checkbox[data-dia="r_qui"]');
                    checkboxesQui.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-seg-sex').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesSegSex = linha.querySelectorAll('.dia-checkbox[data-dia="r_seg"], .dia-checkbox[data-dia="r_sex"]');
                    checkboxesSegSex.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            // Botões para selecionar/limpar horas específicas
            document.querySelectorAll('.btn-selecionar-hora').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const hora = e.target.getAttribute('data-hora');
                    
                    // Selecionar/desmarcar checkboxes da hora específica
                    const checkboxesHora = linha.querySelectorAll(`.dia-checkbox[data-hora="${hora}"]`);
                    
                    // Verificar estado atual dos checkboxes
                    const todosChecked = Array.from(checkboxesHora).every(checkbox => checkbox.checked);
                    
                    checkboxesHora.forEach(checkbox => {
                        checkbox.checked = !todosChecked;
                    });
                });
            });

            // Adicionar event listeners para checkboxes
            document.querySelectorAll('.dia-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const disciplina = e.target.getAttribute('data-disciplina');
                    const dia = e.target.getAttribute('data-dia');
                    const hora = e.target.getAttribute('data-hora');
                    const valorCompleto = `${disciplina}-${dia}-${hora}`;

                    if (e.target.checked) {
                        this.adicionarSelecaoPersistente('restricoes', 'disciplina', valorCompleto);
                    } else {
                        this.removerSelecaoPersistente('restricoes', 'disciplina', valorCompleto);
                    }
                });
            });

            // Aplicar seleções persistentes após renderizar
            this.aplicarSelecoesPersistentes('restricoes');

        } catch (error) {
            console.error('Erro ao carregar dados de disciplinas:', error);
            this.mostrarMensagem(`Erro ao carregar dados de disciplinas: ${error.message}`, 'danger');
        }
    }

    async salvarRestricoes() {
        try {
            // Desabilitar botão durante o salvamento
            const btnSalvarRestricoes = document.getElementById('btnSalvarRestricoes');
            btnSalvarRestricoes.disabled = true;
            btnSalvarRestricoes.innerHTML = 'Salvando...';

            // Coletar restrições de todas as disciplinas
            const restricoes = {};
            
            // Selecionar todas as disciplinas na tabela
            const linhasDisciplinas = document.querySelectorAll('.table tbody tr');
            
            linhasDisciplinas.forEach(linha => {
                const nomeDisciplina = linha.querySelector('td:first-child').getAttribute('title');
                const restricoesDisciplina = {
                    'r_seg': this.coletarRestricaoDia(linha, 'r_seg'),
                    'r_ter': this.coletarRestricaoDia(linha, 'r_ter'),
                    'r_qua': this.coletarRestricaoDia(linha, 'r_qua'),
                    'r_qui': this.coletarRestricaoDia(linha, 'r_qui'),
                    'r_sex': this.coletarRestricaoDia(linha, 'r_sex')
                };
                
                restricoes[nomeDisciplina] = restricoesDisciplina;
            });
            
            // Enviar restrições para o backend
            const resposta = await fetch('/api/salvar_restricoes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(restricoes)
            });
            
            const resultado = await resposta.json();
            
            if (resposta.ok) {
                this.mostrarMensagem(
                    `Restrições salvas com sucesso! ${resultado.total_disciplinas_atualizadas} disciplinas atualizadas.`, 
                    'success'
                );
            } else {
                throw new Error(resultado.error || 'Erro ao salvar restrições');
            }
        } catch (error) {
            console.error('Erro ao salvar restrições:', error);
            this.mostrarMensagem(`Erro: ${error.message}`, 'danger');
        } finally {
            // Reabilitar botão
            const btnSalvarRestricoes = document.getElementById('btnSalvarRestricoes');
            btnSalvarRestricoes.disabled = false;
            btnSalvarRestricoes.innerHTML = 'Salvar Restrições';
        }
    }

    // Método auxiliar para coletar restrição de um dia específico
    coletarRestricaoDia(linha, dia) {
        const checkboxesDia = linha.querySelectorAll(`.dia-checkbox[data-dia="${dia}"]:checked`);
        const horasDia = Array.from(checkboxesDia)
            .map(checkbox => checkbox.value)
            .filter(hora => hora && hora.trim() !== '');  // Remover valores vazios
        
        // Remover duplicatas e ordenar
        const horasUnicas = [...new Set(horasDia)].sort((a, b) => parseInt(a) - parseInt(b));
        
        return horasUnicas.join(',');
    }

    async navegarParaDisponibilidades() {
        try {
            // Buscar dados dos professores
            const resposta = await fetch('/api/professores');
            
            if (!resposta.ok) {
                // Tentar obter detalhes do erro
                const erro = await resposta.json();
                throw new Error(erro.error || 'Erro desconhecido ao carregar professores');
            }
            
            const dadosProfessoresOriginal = await resposta.json();

            // Verificar se há dados
            if (!dadosProfessoresOriginal || dadosProfessoresOriginal.length === 0) {
                throw new Error('Nenhum professor encontrado');
            }

            // Remover duplicatas baseado no nome do professor e ordenar alfabeticamente
            const professoresUnicos = new Map();

            dadosProfessoresOriginal.forEach(professor => {
                if (!professoresUnicos.has(professor.nome)) {
                    // Garantir que as colunas de disponibilidade sejam strings
                    const professorProcessado = {...professor};
                    ['d_seg', 'd_ter', 'd_qua', 'd_qui', 'd_sex'].forEach(dia => {
                        professorProcessado[dia] = (professorProcessado[dia] || '').toString();
                    });
                    professoresUnicos.set(professor.nome, professorProcessado);
                }
            });

            // Converter para array e ordenar alfabeticamente
            const dadosProfessores = Array.from(professoresUnicos.values())
                .sort((a, b) => a.nome.localeCompare(b.nome));

            // Limpar container
            this.container.innerHTML = '';

            // Criar container para conteúdo
            const containerConteudo = document.createElement('div');
            containerConteudo.id = 'disponibilidades-container';
            containerConteudo.className = 'container-fluid';

            // Criar botão de voltar
            const botaoVoltar = document.createElement('button');
            botaoVoltar.className = 'btn btn-secondary mb-3';
            botaoVoltar.innerHTML = '← Voltar para Horário Principal';
            botaoVoltar.addEventListener('click', () => {
                this.container.innerHTML = '';
                this.renderizarHorario(this.dadosHorario);
                
                // Manter botões visíveis
                document.getElementById('btnHorariosProfessores').classList.remove('d-none');
            });

            // Criar título
            const titulo = document.createElement('h2');
            titulo.textContent = 'Disponibilidades dos Professores';
            titulo.className = 'text-center mb-4';

            // Adicionar botão de salvar disponibilidades
            const btnSalvarDisponibilidades = document.createElement('button');
            btnSalvarDisponibilidades.id = 'btnSalvarDisponibilidades';
            btnSalvarDisponibilidades.className = 'btn btn-primary mt-3 mb-3';
            btnSalvarDisponibilidades.textContent = 'Salvar Disponibilidades';
            btnSalvarDisponibilidades.addEventListener('click', () => this.salvarDisponibilidades());

            // Adicionar botão de voltar e título ao container
            containerConteudo.appendChild(botaoVoltar);
            containerConteudo.appendChild(titulo);
            containerConteudo.appendChild(btnSalvarDisponibilidades);

            // Criar container para tabela
            const containerTabela = document.createElement('div');
            containerTabela.className = 'table-responsive';

            // Criar tabela
            const tabela = document.createElement('table');
            tabela.className = 'table table-bordered table-striped';

            // Cabeçalho da tabela
            const cabecalho = `
                <thead>
                    <tr>
                        <th>Nome</th>
                        <th class="text-center">Seg</th>
                        <th class="text-center">Ter</th>
                        <th class="text-center">Qua</th>
                        <th class="text-center">Qui</th>
                        <th class="text-center">Sex</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    ${dadosProfessores.map((professor, index) => `
                        <tr>
                            <td>${professor.nome}</td>
                            ${['d_seg', 'd_ter', 'd_qua', 'd_qui', 'd_sex'].map(dia => `
                                <td class="text-center">
                                    ${[1,2,3,4,5,6,7].map(hora => `
                                        <div class="form-check form-check-inline">
                                            <input class="form-check-input dia-checkbox" type="checkbox" 
                                                   id="${professor.nome}-${dia}-${hora}"
                                                   data-professor="${professor.nome}"
                                                   data-dia="${dia}"
                                                   data-hora="${hora}"
                                                   value="${hora}"
                                                   ${professor[dia] && professor[dia].split(',').includes(hora.toString()) ? 'checked' : ''}>
                                            <label class="form-check-label" for="${professor.nome}-${dia}-${hora}">
                                                ${hora}
                                            </label>
                                        </div>
                                    `).join('')}
                                </td>
                            `).join('')}
                            <td class="text-center">
                                <div class="btn-group-vertical btn-group-sm" role="group">
                                    <div class="btn-group btn-group-sm mb-1" role="group">
                                        <button type="button" class="btn btn-success btn-selecionar-linha" data-linha="${index}">
                                            Sel. Tudo
                                        </button>
                                        <button type="button" class="btn btn-danger btn-limpar-linha" data-linha="${index}">
                                            Limpar
                                        </button>
                                    </div>
                                    <div class="btn-group btn-group-sm" role="group">
                                        <button type="button" class="btn btn-warning btn-limpar-ter" data-linha="${index}">
                                            BH
                                        </button>
                                        <button type="button" class="btn btn-info btn-limpar-qua" data-linha="${index}">
                                            BN
                                        </button>
                                        <button type="button" class="btn btn-primary btn-limpar-qui" data-linha="${index}">
                                            BL
                                        </button>
                                        <button type="button" class="btn btn-secondary btn-limpar-seg-sex" data-linha="${index}">
                                            PCA
                                        </button>
                                    </div>
                                    <div class="btn-group btn-group-sm mt-1" role="group">
                                        ${[1,2,3,4,5,6,7].map(numero => `
                                            <button type="button" class="btn btn-outline-primary btn-selecionar-hora" 
                                                    data-linha="${index}" 
                                                    data-hora="${numero}">
                                                ${numero}
                                            </button>
                                        `).join('')}
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            `;

            tabela.innerHTML = cabecalho;
            containerTabela.appendChild(tabela);
            containerConteudo.appendChild(containerTabela);

            // Adicionar informação do total de linhas
            const totalLinhas = document.createElement('div');
            totalLinhas.className = 'alert alert-info mt-3';
            totalLinhas.innerHTML = `<strong>Total de Professores:</strong> ${dadosProfessores.length}`;
            containerConteudo.appendChild(totalLinhas);

            this.container.appendChild(containerConteudo);

            // Adicionar event listeners para botões de seleção
            document.querySelectorAll('.btn-selecionar-linha').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxes = linha.querySelectorAll('.dia-checkbox');
                    checkboxes.forEach(checkbox => {
                        checkbox.checked = true;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-linha').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxes = linha.querySelectorAll('.dia-checkbox');
                    checkboxes.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            // Novos botões de ações específicas
            document.querySelectorAll('.btn-limpar-ter').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesTer = linha.querySelectorAll('.dia-checkbox[data-dia="d_ter"]');
                    checkboxesTer.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-qua').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesQua = linha.querySelectorAll('.dia-checkbox[data-dia="d_qua"]');
                    checkboxesQua.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-qui').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesQui = linha.querySelectorAll('.dia-checkbox[data-dia="d_qui"]');
                    checkboxesQui.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            document.querySelectorAll('.btn-limpar-seg-sex').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const checkboxesSegSex = linha.querySelectorAll('.dia-checkbox[data-dia="d_seg"], .dia-checkbox[data-dia="d_sex"]');
                    checkboxesSegSex.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });
            });

            // Botões para selecionar/limpar horas específicas
            document.querySelectorAll('.btn-selecionar-hora').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    const hora = e.target.getAttribute('data-hora');
                    
                    // Selecionar/desmarcar checkboxes da hora específica
                    const checkboxesHora = linha.querySelectorAll(`.dia-checkbox[data-hora="${hora}"]`);
                    
                    // Verificar estado atual dos checkboxes
                    const todosChecked = Array.from(checkboxesHora).every(checkbox => checkbox.checked);
                    
                    checkboxesHora.forEach(checkbox => {
                        checkbox.checked = !todosChecked;
                    });
                });
            });

            // Adicionar event listeners para checkboxes
            document.querySelectorAll('.dia-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const professor = e.target.getAttribute('data-professor');
                    const dia = e.target.getAttribute('data-dia');
                    const hora = e.target.getAttribute('data-hora');
                    const valorCompleto = `${professor}-${dia}-${hora}`;

                    if (e.target.checked) {
                        this.adicionarSelecaoPersistente('disponibilidades', 'professor', valorCompleto);
                    } else {
                        this.removerSelecaoPersistente('disponibilidades', 'professor', valorCompleto);
                    }
                });
            });

            // Aplicar seleções persistentes após renderizar
            this.aplicarSelecoesPersistentes('disponibilidades');

        } catch (error) {
            console.error('Erro ao buscar dados de professores:', error);
            this.mostrarMensagem('Erro ao carregar professores', 'danger');
        }
    }

    navegarParaHorariosProfessores() {
        if (!this.dadosHorario) {
            this.mostrarMensagem('Primeiro gere um horário', 'warning');
            return;
        }

        // Limpar container
        this.container.innerHTML = '';

        // Criar container para conteúdo
        const containerConteudo = document.createElement('div');
        containerConteudo.className = 'container-fluid';

        // Criar botão de voltar
        const botaoVoltar = document.createElement('button');
        botaoVoltar.className = 'btn btn-secondary mb-3';
        botaoVoltar.innerHTML = '← Voltar para Horário Principal';
        botaoVoltar.addEventListener('click', () => {
            this.container.innerHTML = '';
            this.renderizarHorario(this.dadosHorario);
            
            // Manter botão de horários de professores visível
            document.getElementById('btnHorariosProfessores').classList.remove('d-none');
        });

        // Criar título
        const titulo = document.createElement('h2');
        titulo.textContent = 'Horários dos Professores';
        titulo.className = 'text-center mb-4';

        // Adicionar botão de voltar e título ao container
        containerConteudo.appendChild(botaoVoltar);
        containerConteudo.appendChild(titulo);

        // Criar container para tabelas de professores
        const containerProfessores = document.createElement('div');
        containerProfessores.className = 'row professores-container';

        // Extrair lista de professores
        const professores = new Set();
        Object.keys(this.dadosHorario)
            .filter(turma => turma !== '_alocacoes_incompletas')
            .forEach(turma => {
                Object.values(this.dadosHorario[turma].dias).forEach(dia => {
                    Object.values(dia).forEach(aula => {
                        if (aula && aula.professor && aula.professor !== '---') {
                            professores.add(aula.professor);
                        }
                    });
                });
            });

        // Ordenar professores alfabeticamente
        const professoresOrdenados = Array.from(professores).sort((a, b) => a.localeCompare(b));

        // Gerar tabela para cada professor
        professoresOrdenados.forEach(professor => {
            const colunaProfessor = document.createElement('div');
            colunaProfessor.className = 'col-professor col-md-6 mb-4';
            
            const tabelaProfessor = document.createElement('div');
            tabelaProfessor.className = 'tabela-professor card h-100';
            
            tabelaProfessor.innerHTML = `
                <div class="card-header text-center">
                    <h4 class="mb-0">${professor}</h4>
                </div>
                <div class="card-body p-0">
                    <table class="table table-bordered horario-professor-table mb-0">
                        <thead>
                            <tr>
                                <th>Horário</th>
                                <th>Segunda</th>
                                <th>Terça</th>
                                <th>Quarta</th>
                                <th>Quinta</th>
                                <th>Sexta</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${this.gerarLinhasTabelaProfessor(professor)}
                        </tbody>
                    </table>
                </div>
            `;
            
            colunaProfessor.appendChild(tabelaProfessor);
            containerProfessores.appendChild(colunaProfessor);
        });

        // Adicionar tudo ao container principal
        containerConteudo.appendChild(containerProfessores);
        this.container.appendChild(containerConteudo);
    }

    gerarLinhasTabelaProfessor(professorBuscado) {
        const dias = ['seg', 'ter', 'qua', 'qui', 'sex'];
        const numLinhas = {
            'Intermediario': 7,
            'Vespertino': 6,
            'Noturno': 3
        }[this.turnoSelect.value];

        let linhas = '';
        for (let horario = 1; horario <= numLinhas; horario++) {
            linhas += `
                <tr>
                    <td class="horario">${horario}ª Aula</td>
                    ${dias.map(dia => {
                        // Buscar aula do professor neste dia e horário
                        const aulasProfessor = [];
                        
                        Object.keys(this.dadosHorario)
                            .filter(turma => turma !== '_alocacoes_incompletas')
                            .forEach(turma => {
                                const aula = this.dadosHorario[turma].dias[dia][horario];
                                if (aula && aula.professor === professorBuscado) {
                                    aulasProfessor.push({
                                        turma: turma,
                                        disciplina: aula.disciplina
                                    });
                                }
                            });

                        // Formatar células com aulas do professor
                        if (aulasProfessor.length > 0) {
                            // Adicionar classe de múltiplas aulas se houver mais de uma aula
                            const classeMultiplasAulas = aulasProfessor.length > 1 ? 'multiplas-aulas' : '';
                            
                            return `
                                <td class="${classeMultiplasAulas}">
                                    ${aulasProfessor.map(aula => `
                                        <div class="aula-professor">
                                            <div class="turma">${aula.turma}</div>
                                            <div class="disciplina" title="${aula.disciplina}">
                                                ${this.simplificarNomeDisciplina(aula.disciplina)}
                                            </div>
                                        </div>
                                    `).join('<hr class="my-1">')}
                                </td>
                            `;
                        } else {
                            return '<td>---</td>';
                        }
                    }).join('')}
                </tr>
            `;
        }
        return linhas;
    }

    async carregarHorario() {
        try {
            // Limpar container e mensagens anteriores
            this.container.innerHTML = '';
            this.mensagem.style.display = 'none';
            
            // Mostrar barra de progresso
            this.progressContainer.style.display = 'block';
            this.progressBar.style.width = '0%';
            this.progressBar.textContent = 'Iniciando geração de horário...';
            
            // Obter turno selecionado
            const turno = this.turnoSelect.value;
            console.log(`🔍 Carregando horário para turno: ${turno}`);
            
            // Fazer requisição para API
            const resposta = await fetch(`/api/horarios/${turno}`);
            
            console.log('📡 Resposta da API recebida:', resposta);
            
            // Verificar se a resposta foi bem-sucedida
            if (!resposta.ok) {
                const erro = await resposta.json();
                console.error('❌ Erro na geração do horário:', erro);
                
                this.progressContainer.style.display = 'none';
                this.mensagem.textContent = `Erro: ${erro.error || 'Falha ao gerar horário'}`;
                this.mensagem.className = 'alert alert-danger';
                this.mensagem.style.display = 'block';
                return;
            }
            
            // Parsear dados do horário
            const dadosHorario = await resposta.json();
            console.log('📊 Dados do horário recebidos:', dadosHorario);
            
            // Verificar se há dados válidos
            if (!dadosHorario || Object.keys(dadosHorario).length === 0) {
                console.warn('⚠️ Nenhum dado de horário encontrado');
                
                this.progressContainer.style.display = 'none';
                this.mensagem.textContent = 'Nenhum horário gerado. Verifique as configurações.';
                this.mensagem.className = 'alert alert-warning';
                this.mensagem.style.display = 'block';
                return;
            }
            
            // Armazenar dados do horário
            this.dadosHorario = dadosHorario;
            
            // Renderizar horário
            this.renderizarHorario(dadosHorario);
            
            // Ocultar barra de progresso
            this.progressContainer.style.display = 'none';
            
            // Mostrar botão de horários de professores
            document.getElementById('btnHorariosProfessores').classList.remove('d-none');
            
        } catch (erro) {
            console.error('❌ Erro crítico:', erro);
            
            this.progressContainer.style.display = 'none';
            this.mensagem.textContent = `Erro inesperado: ${erro.message}`;
            this.mensagem.className = 'alert alert-danger';
            this.mensagem.style.display = 'block';
        }
    }
    
    renderizarHorario(dadosHorario) {
        console.log('🎨 Iniciando renderização do horário:', dadosHorario);
        
        // Limpar container
        this.container.innerHTML = '';
        
        // Verificar se há dados
        if (!dadosHorario || Object.keys(dadosHorario).length === 0) {
            console.warn('⚠️ Nenhum dado de horário para renderizar');
            this.container.innerHTML = '<div class="alert alert-warning">Nenhum horário disponível</div>';
            return;
        }
        
        // Criar container principal
        const containerHorarios = document.createElement('div');
        containerHorarios.className = 'row';
        
        // Iterar sobre as turmas
        Object.entries(dadosHorario).forEach(([turma, dadosTurma]) => {
            console.log(`🏫 Renderizando turma: ${turma}`);
            
            // Pular chaves especiais como '_alocacoes_incompletas'
            if (turma.startsWith('_')) return;
            
            // Criar card para a turma
            const cardTurma = document.createElement('div');
            cardTurma.className = 'col-12 mb-4';
            
            const tituloTurma = document.createElement('h3');
            tituloTurma.textContent = `Horário - ${turma}`;
            tituloTurma.className = 'text-center mb-3';
            
            const tabelaHorario = document.createElement('table');
            tabelaHorario.className = 'table table-bordered table-striped table-hover';
            
            // Cabeçalho da tabela
            const cabecalho = `
                <thead>
                    <tr>
                        <th>Horário</th>
                        ${this.dias.map(dia => `<th>${this.diasNomes[dia]}</th>`).join('')}
                    </tr>
                </thead>
            `;
            
            // Corpo da tabela
            const corpoTabela = `
                <tbody>
                    ${[1, 2, 3, 4, 5, 6, 7].map(horario => `
                        <tr>
                            <td class="text-center fw-bold">${horario}º</td>
                            ${this.dias.map(dia => {
                                const aula = dadosTurma.dias[dia]?.[horario];
                                const conteudoCelula = aula 
                                    ? `${aula.disciplina}<br><small class="text-muted">${aula.professor}</small>` 
                                    : '';
                                return `<td class="text-center ${aula ? 'table-active' : ''}">${conteudoCelula}</td>`;
                            }).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            `;
            
            tabelaHorario.innerHTML = cabecalho + corpoTabela;
            
            cardTurma.appendChild(tituloTurma);
            cardTurma.appendChild(tabelaHorario);
            
            containerHorarios.appendChild(cardTurma);
        });
        
        // Adicionar alocações incompletas, se existirem
        if (dadosHorario['_alocacoes_incompletas']) {
            const alocacoesIncompletas = document.createElement('div');
            alocacoesIncompletas.className = 'col-12 alert alert-warning';
            alocacoesIncompletas.innerHTML = `
                <h4>Alocações Incompletas</h4>
                <ul>
                    ${dadosHorario['_alocacoes_incompletas'].map(alocacao => `
                        <li>
                            Turma: ${alocacao.turma}, 
                            Disciplina: ${alocacao.disciplina}, 
                            Aulas Previstas: ${alocacao.aulas_previstas}, 
                            Aulas Alocadas: ${alocacao.aulas_alocadas}
                        </li>
                    `).join('')}
                </ul>
            `;
            containerHorarios.appendChild(alocacoesIncompletas);
        }

        // Adicionar sugestões de ML se existirem
        if (dadosHorario['_sugestoes_melhoria'] && dadosHorario['_sugestoes_melhoria'].length > 0) {
            const containerSugestoes = document.createElement('div');
            containerSugestoes.className = 'col-12 alert alert-info';
            containerSugestoes.innerHTML = `
                <h4>Sugestões de Melhoria (ML)</h4>
                <ul>
                    ${dadosHorario['_sugestoes_melhoria'].map(sugestao => `
                        <li>${sugestao.mensagem}</li>
                    `).join('')}
                </ul>
            `;
            containerHorarios.appendChild(containerSugestoes);
        }
        
        // Adicionar ao container principal
        this.container.appendChild(containerHorarios);
        
        console.log('✅ Renderização do horário concluída');
    }
    
    simplificarNomeDisciplina(disciplina) {
        try {
            if (!disciplina) return '---';
            
            disciplina = String(disciplina).trim();
            
            if (disciplina.split(' ').length === 1) {
                return disciplina.substring(0, 3).toUpperCase();
            }
            
            const palavras = disciplina.split(' ').filter(palavra => palavra.length > 2);
            
            if (palavras.length === 2) {
                return (
                    palavras[0][0].toUpperCase() + 
                    palavras[1].substring(0, 3).toUpperCase()
                );
            }
            
            return disciplina
                .split(' ')
                .filter(palavra => palavra.length > 3)
                .map(palavra => palavra[0].toUpperCase())
                .join('') || disciplina.substring(0, 3).toUpperCase();
        } catch (error) {
            console.error('Erro ao simplificar nome da disciplina:', error);
            return '---';
        }
    }

    gerarLinhasTabelaDia(dados, dia) {
        const turmas = Object.keys(dados).filter(turma => turma !== '_alocacoes_incompletas');
        
        const numLinhas = {
            'Intermediario': 7,
            'Vespertino': 6,
            'Noturno': 3
        }[this.turnoSelect.value];

        let linhas = '';
        for (let horario = 1; horario <= numLinhas; horario++) {
            linhas += `
                <tr>
                    <td class="horario">${horario}ª Aula</td>
                    ${turmas.map(turma => {
                        const aula = dados[turma].dias[dia][horario] || {};
                        
                        return `
                            <td>
                                ${aula.disciplina ? `
                                    <div class="aula-info">
                                        <div class="disciplina" title="${aula.disciplina}">
                                            ${this.simplificarNomeDisciplina(aula.disciplina)}
                                        </div>
                                        <div class="professor" style="background-color: ${this.gerarCorParaProfessor(aula.professor)}; 
                                                                     padding: 2px 4px; 
                                                                     border-radius: 3px; 
                                                                     display: inline-block;">
                                            ${aula.professor || '---'}
                                        </div>
                                    </div>
                                ` : '---'}
                            </td>
                        `;
                    }).join('')}
                </tr>
            `;
        }
        return linhas;
    }

    gerarCorParaProfessor(professor) {
        if (!professor || professor === '---') return '#f0f0f0';
        
        if (this.professoresCores[professor]) {
            return this.professoresCores[professor];
        }
        
        let hash = 0;
        for (let i = 0; i < professor.length; i++) {
            hash = professor.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        const hue = hash % 360;
        const cor = `hsl(${hue}, 70%, 80%)`;
        
        this.professoresCores[professor] = cor;
        
        return cor;
    }

    mostrarProgresso(show, totalAulas = 0, aulasAlocadas = 0) {
        if (show) {
            this.progressBar.style.display = 'block';
            
            // Calcular percentual real de alocações
            let percentual = totalAulas > 0 
                ? Math.round((aulasAlocadas / totalAulas) * 100) 
                : 0;
            
            // Garantir que o percentual esteja entre 0 e 100
            percentual = Math.max(0, Math.min(100, percentual));
            
            // Atualizar largura da barra de progresso
            this.progressBar.style.width = `${percentual}%`;
            
            // Adicionar texto de progresso
            this.progressBar.textContent = `${percentual}% (${aulasAlocadas}/${totalAulas})`;
            
            // Adicionar classes para feedback visual
            if (percentual < 30) {
                this.progressBar.classList.add('progress-low');
            } else if (percentual < 70) {
                this.progressBar.classList.remove('progress-low');
                this.progressBar.classList.add('progress-medium');
            } else {
                this.progressBar.classList.remove('progress-low', 'progress-medium');
                this.progressBar.classList.add('progress-high');
            }
        } else {
            this.progressBar.style.display = 'none';
        }
    }

    mostrarMensagem(texto, tipo = 'info') {
        this.mensagem.className = `alert alert-${tipo}`;
        this.mensagem.innerHTML = texto;
        this.mensagem.style.display = 'block';
    }

    async navegarParaExcecoes() {
        try {
            // Buscar professores, disciplinas e exceções existentes
            const [respProfessores, respDisciplinas, respExcecoes] = await Promise.all([
                fetch('/api/professores'),
                fetch('/api/disciplinas'),
                fetch('/api/carregar_excecoes')
            ]);

            const professores = await respProfessores.json();
            const disciplinas = await respDisciplinas.json();
            
            // Tratamento de erro para exceções
            let excecoes = [];
            try {
                const respExcecoesText = await respExcecoes.text();
                console.log('Resposta de exceções (texto bruto):', respExcecoesText);
                
                // Tentar parsear JSON
                try {
                    excecoes = JSON.parse(respExcecoesText);
                    console.log('Exceções parseadas:', excecoes);
                } catch (parseError) {
                    console.error('Erro ao parsear JSON:', parseError);
                    console.log('Conteúdo que falhou no parse:', respExcecoesText);
                    
                    // Tentar parsear manualmente
                    try {
                        // Substituir NÃƒO por NÃO
                        const textoCorrigido = respExcecoesText.replace(/NÃƒO/g, 'NÃO');
                        excecoes = JSON.parse(textoCorrigido);
                        console.log('Exceções parseadas após correção:', excecoes);
                    } catch (manualParseError) {
                        console.error('Erro ao parsear JSON manualmente:', manualParseError);
                        this.mostrarMensagem('Erro ao carregar exceções. Formato de dados inválido.', 'warning');
                        return;
                    }
                }
            } catch (error) {
                console.error('Erro ao processar exceções:', error);
                this.mostrarMensagem('Erro ao carregar exceções. Verifique o arquivo CSV.', 'warning');
                return;
            }

            // Log para verificar disciplinas
            console.log('Professores carregados:', professores);
            console.log('Disciplinas carregadas:', disciplinas);
            console.log('Exceções carregadas:', excecoes);

            // Garantir que excecoes seja um array
            const excecoesSafe = Array.isArray(excecoes) ? excecoes : [];

            // Limpar container
            this.container.innerHTML = '';

            // Criar container para conteúdo
            const containerConteudo = document.createElement('div');
            containerConteudo.id = 'excecoes-container';
            containerConteudo.className = 'container-fluid';

            // Criar botão de voltar
            const botaoVoltar = document.createElement('button');
            botaoVoltar.className = 'btn btn-secondary mb-3';
            botaoVoltar.innerHTML = '← Voltar para Horário Principal';
            botaoVoltar.addEventListener('click', () => {
                this.container.innerHTML = '';
                this.renderizarHorario(this.dadosHorario);
                
                // Manter botões visíveis
                document.getElementById('btnHorariosProfessores').classList.remove('d-none');
            });

            // Criar título
            const titulo = document.createElement('h2');
            titulo.textContent = 'Exceções';
            titulo.className = 'text-center mb-4';

            // Adicionar botão de salvar exceções
            const btnSalvarExcecoes = document.createElement('button');
            btnSalvarExcecoes.id = 'btnSalvarExcecoes';
            btnSalvarExcecoes.className = 'btn btn-primary mt-3 mb-3';
            btnSalvarExcecoes.textContent = 'Salvar Exceções';
            btnSalvarExcecoes.addEventListener('click', () => this.salvarExcecoes());

            // Adicionar botão de adicionar exceção
            const btnAdicionarExcecao = document.createElement('button');
            btnAdicionarExcecao.id = 'btnAdicionarExcecao';
            btnAdicionarExcecao.className = 'btn btn-success mt-3 mb-3 ml-2';
            btnAdicionarExcecao.textContent = '+ Adicionar Exceção';
            btnAdicionarExcecao.addEventListener('click', () => this.adicionarLinhaExcecao());

            // Container para botões
            const containerBotoes = document.createElement('div');
            containerBotoes.className = 'd-flex justify-content-start align-items-center';
            containerBotoes.appendChild(btnSalvarExcecoes);
            containerBotoes.appendChild(btnAdicionarExcecao);

            // Adicionar botão de voltar, título e botões ao container
            containerConteudo.appendChild(botaoVoltar);
            containerConteudo.appendChild(titulo);
            containerConteudo.appendChild(containerBotoes);

            // Criar container para tabela
            const containerTabela = document.createElement('div');
            containerTabela.className = 'table-responsive';

            // Criar tabela
            const tabela = document.createElement('table');
            tabela.id = 'tabelaExcecoes';
            tabela.className = 'table table-bordered table-striped';

            // Cabeçalho da tabela
            const cabecalho = `
                <thead>
                    <tr>
                        <th>Professor</th>
                        <th>Disciplina</th>
                        <th>Turma</th>
                        <th>Tipo</th>
                        <th>Dias</th>
                        <th>Aulas</th>
                        <th>Até 2 aulas/dia</th>
                        <th>Geminadas</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    ${excecoesSafe.map(excecao => `
                        <tr>
                            <td>
                                <select class="form-control professor-select">
                                    <option value="">Selecione</option>
                                    ${professores.map(prof => `
                                        <option value="${prof.nome}" ${prof.nome === excecao.professor ? 'selected' : ''}>
                                            ${prof.nome}
                                        </option>
                                    `).join('')}
                                </select>
                            </td>
                            <td>
                                <select class="form-control disciplina-select">
                                    <option value="">Selecione</option>
                                    ${disciplinas.map(disc => `
                                        <option value="${disc.disciplina}" ${disc.disciplina === excecao.disciplina ? 'selected' : ''}>
                                            ${this.simplificarNomeDisciplina(disc.disciplina)}
                                        </option>
                                    `).join('')}
                                </select>
                            </td>
                            <td>
                                <input type="text" class="form-control turma-input" placeholder="Ex: 2i01" value="${excecao.turma || ''}">
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-tipo ${excecao.tipo === 'SIM' ? 'btn-primary' : 'btn-outline-primary'}" data-tipo="SIM">
                                        SIM
                                    </button>
                                    <button type="button" class="btn btn-tipo ${excecao.tipo === 'NÃO' ? 'btn-primary' : 'btn-outline-primary'}" data-tipo="NÃO">
                                        NÃO
                                    </button>
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    ${['seg', 'ter', 'qua', 'qui', 'sex'].map(dia => `
                                        <button type="button" class="btn btn-dia ${(excecao.dias || '').split(',').includes(dia) ? 'active btn-primary' : 'btn-outline-primary'}" data-dia="${dia}">
                                            ${dia.toUpperCase()}
                                        </button>
                                    `).join('')}
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    ${[1,2,3,4,5,6,7].map(hora => `
                                        <button type="button" class="btn btn-hora ${(excecao.horas || '').split(',').includes(hora.toString()) ? 'active btn-primary' : 'btn-outline-primary'}" data-hora="${hora}">
                                            ${hora}
                                        </button>
                                    `).join('')}
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-limite-duas-aulas ${excecao.limite_duas_aulas === 'SIM' ? 'btn-primary' : 'btn-outline-primary'}" data-limite="SIM">
                                        SIM
                                    </button>
                                    <button type="button" class="btn btn-limite-duas-aulas ${excecao.limite_duas_aulas === 'NÃO' ? 'btn-primary' : 'btn-outline-primary'}" data-limite="NÃO">
                                        NÃO
                                    </button>
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-geminadas ${excecao.geminadas === 'SIM' ? 'btn-primary' : 'btn-outline-primary'}" data-geminadas="SIM">
                                        SIM
                                    </button>
                                    <button type="button" class="btn btn-geminadas ${excecao.geminadas === 'NÃO' ? 'btn-primary' : 'btn-outline-primary'}" data-geminadas="NÃO">
                                        NÃO
                                    </button>
                                </div>
                            </td>
                            <td class="text-center">
                                <button class="btn btn-danger btn-sm btn-remover-excecao">
                                    Remover
                                </button>
                            </td>
                        </tr>
                    `).join('') || `
                        <tr>
                            <td>
                                <select class="form-control professor-select">
                                    <option value="">Selecione</option>
                                    ${professores.map(prof => `
                                        <option value="${prof.nome}">${prof.nome}</option>
                                    `).join('')}
                                </select>
                            </td>
                            <td>
                                <select class="form-control disciplina-select">
                                    <option value="">Selecione</option>
                                    ${disciplinas.map(disc => `
                                        <option value="${disc.disciplina}">
                                            ${this.simplificarNomeDisciplina(disc.disciplina)}
                                        </option>
                                    `).join('')}
                                </select>
                            </td>
                            <td>
                                <input type="text" class="form-control turma-input" placeholder="Ex: 2i01">
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-tipo btn-outline-primary" data-tipo="SIM">
                                        SIM
                                    </button>
                                    <button type="button" class="btn btn-tipo btn-outline-primary" data-tipo="NÃO">
                                        NÃO
                                    </button>
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    ${['seg', 'ter', 'qua', 'qui', 'sex'].map(dia => `
                                        <button type="button" class="btn btn-outline-primary btn-dia" data-dia="${dia}">
                                            ${dia.toUpperCase()}
                                        </button>
                                    `).join('')}
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    ${[1,2,3,4,5,6,7].map(hora => `
                                        <button type="button" class="btn btn-outline-primary btn-hora" data-hora="${hora}">
                                            ${hora}
                                        </button>
                                    `).join('')}
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-limite-duas-aulas btn-outline-primary" data-limite="SIM">
                                        SIM
                                    </button>
                                    <button type="button" class="btn btn-limite-duas-aulas btn-outline-primary" data-limite="NÃO">
                                        NÃO
                                    </button>
                                </div>
                            </td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-geminadas btn-outline-primary" data-geminadas="SIM">
                                        SIM
                                    </button>
                                    <button type="button" class="btn btn-geminadas btn-outline-primary" data-geminadas="NÃO">
                                        NÃO
                                    </button>
                                </div>
                            </td>
                            <td class="text-center">
                                <button class="btn btn-danger btn-sm btn-remover-excecao">
                                    Remover
                                </button>
                            </td>
                        </tr>
                    `}
                </tbody>
            `;

            tabela.innerHTML = cabecalho;
            containerTabela.appendChild(tabela);
            containerConteudo.appendChild(containerTabela);

            // Adicionar informação do total de linhas
            const totalLinhas = document.createElement('div');
            totalLinhas.className = 'alert alert-info mt-3';
            totalLinhas.innerHTML = `<strong>Total de Exceções:</strong> ${excecoesSafe.length}`;
            containerConteudo.appendChild(totalLinhas);

            this.container.appendChild(containerConteudo);

            // Adicionar event listeners para botões de dias
            document.querySelectorAll('.btn-dia').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    e.target.classList.toggle('active');
                    e.target.classList.toggle('btn-primary');
                    e.target.classList.toggle('btn-outline-primary');
                });
            });

            // Adicionar event listeners para botões de horas
            document.querySelectorAll('.btn-hora').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    e.target.classList.toggle('active');
                    e.target.classList.toggle('btn-primary');
                    e.target.classList.toggle('btn-outline-primary');
                });
            });

            // Adicionar event listeners para botões de tipo
            document.querySelectorAll('.btn-tipo').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const grupo = e.target.closest('.btn-group');
                    const botoes = grupo.querySelectorAll('.btn-tipo');
                    botoes.forEach(btn => {
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-outline-primary');
                    });
                    e.target.classList.remove('btn-outline-primary');
                    e.target.classList.add('btn-primary');
                });
            });

            // Adicionar event listener para botão de remoção
            document.querySelectorAll('.btn-remover-excecao').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const linha = e.target.closest('tr');
                    linha.remove();
                    this.atualizarTotalExcecoes();
                });
            });

            // Adicionar event listener para botão de adicionar exceção
            document.getElementById('btnAdicionarExcecao').addEventListener('click', () => this.adicionarLinhaExcecao());

            // Adicionar event listeners para botões de limite de duas aulas
            document.querySelectorAll('.btn-limite-duas-aulas').forEach(botao => {
                console.log('Adicionando event listener para botão de limite de duas aulas:', botao);
                botao.addEventListener('click', (e) => {
                    console.log('Botão de limite de duas aulas clicado:', e.target);
                    const grupo = e.target.closest('.btn-group');
                    const botoes = grupo.querySelectorAll('.btn-limite-duas-aulas');
                    botoes.forEach(btn => {
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-outline-primary');
                    });
                    e.target.classList.remove('btn-outline-primary');
                    e.target.classList.add('btn-primary');
                });
            });

            // Adicionar event listeners para botões de geminadas
            document.querySelectorAll('.btn-geminadas').forEach(botao => {
                botao.addEventListener('click', (e) => {
                    const grupo = e.target.closest('.btn-group');
                    const botoes = grupo.querySelectorAll('.btn-geminadas');
                    botoes.forEach(btn => {
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-outline-primary');
                    });
                    e.target.classList.remove('btn-outline-primary');
                    e.target.classList.add('btn-primary');
                });
            });

        } catch (error) {
            console.error('Erro ao carregar dados para exceções:', error);
            this.mostrarMensagem(`Erro: ${error.message}`, 'danger');
        }
    }

    adicionarLinhaExcecao() {
        const tabela = document.getElementById('tabelaExcecoes');
        const tbody = tabela.querySelector('tbody');
        const professores = document.querySelector('.professor-select').innerHTML;
        const disciplinas = document.querySelector('.disciplina-select').innerHTML;

        const novaLinha = document.createElement('tr');
        novaLinha.innerHTML = `
            <td>
                <select class="form-control professor-select">
                    ${professores}
                </select>
            </td>
            <td>
                <select class="form-control disciplina-select">
                    ${disciplinas}
                </select>
            </td>
            <td>
                <input type="text" class="form-control turma-input" placeholder="Ex: 2i01">
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-tipo btn-outline-primary" data-tipo="SIM">
                        SIM
                    </button>
                    <button type="button" class="btn btn-tipo btn-outline-primary" data-tipo="NÃO">
                        NÃO
                    </button>
                </div>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm" role="group">
                    ${['seg', 'ter', 'qua', 'qui', 'sex'].map(dia => `
                        <button type="button" class="btn btn-outline-primary btn-dia" data-dia="${dia}">
                            ${dia.toUpperCase()}
                        </button>
                    `).join('')}
                </div>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm" role="group">
                    ${[1,2,3,4,5,6,7].map(hora => `
                        <button type="button" class="btn btn-outline-primary btn-hora" data-hora="${hora}">
                            ${hora}
                        </button>
                    `).join('')}
                </div>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-limite-duas-aulas btn-outline-primary" data-limite="SIM">
                        SIM
                    </button>
                    <button type="button" class="btn btn-limite-duas-aulas btn-outline-primary" data-limite="NÃO">
                        NÃO
                    </button>
                </div>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-geminadas btn-outline-primary" data-geminadas="SIM">
                        SIM
                    </button>
                    <button type="button" class="btn btn-geminadas btn-outline-primary" data-geminadas="NÃO">
                        NÃO
                    </button>
                </div>
            </td>
            <td class="text-center">
                <button class="btn btn-danger btn-sm btn-remover-excecao">
                    Remover
                </button>
            </td>
        `;

        tbody.appendChild(novaLinha);

        // Adicionar event listeners para botões de dias
        novaLinha.querySelectorAll('.btn-dia').forEach(botao => {
            botao.addEventListener('click', (e) => {
                e.target.classList.toggle('active');
                e.target.classList.toggle('btn-primary');
                e.target.classList.toggle('btn-outline-primary');
            });
        });

        // Adicionar event listeners para botões de horas
        novaLinha.querySelectorAll('.btn-hora').forEach(botao => {
            botao.addEventListener('click', (e) => {
                e.target.classList.toggle('active');
                e.target.classList.toggle('btn-primary');
                e.target.classList.toggle('btn-outline-primary');
            });
        });

        // Adicionar event listeners para botões de tipo
        novaLinha.querySelectorAll('.btn-tipo').forEach(botao => {
            botao.addEventListener('click', (e) => {
                const grupo = e.target.closest('.btn-group');
                const botoes = grupo.querySelectorAll('.btn-tipo');
                botoes.forEach(btn => {
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-outline-primary');
                });
                e.target.classList.remove('btn-outline-primary');
                e.target.classList.add('btn-primary');
            });
        });

        // Adicionar event listeners para botões de limite de duas aulas
        novaLinha.querySelectorAll('.btn-limite-duas-aulas').forEach(botao => {
            botao.addEventListener('click', (e) => {
                console.log('Botão de limite de duas aulas clicado:', e.target);
                const grupo = e.target.closest('.btn-group');
                const botoes = grupo.querySelectorAll('.btn-limite-duas-aulas');
                botoes.forEach(btn => {
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-outline-primary');
                });
                e.target.classList.remove('btn-outline-primary');
                e.target.classList.add('btn-primary');
            });
        });

        // Adicionar event listeners para botões de geminadas
        novaLinha.querySelectorAll('.btn-geminadas').forEach(botao => {
            botao.addEventListener('click', (e) => {
                const grupo = e.target.closest('.btn-group');
                const botoes = grupo.querySelectorAll('.btn-geminadas');
                botoes.forEach(btn => {
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-outline-primary');
                });
                e.target.classList.remove('btn-outline-primary');
                e.target.classList.add('btn-primary');
            });
        });

        // Adicionar event listener para botão de remoção
        novaLinha.querySelector('.btn-remover-excecao').addEventListener('click', (e) => {
            const linha = e.target.closest('tr');
            linha.remove();
            this.atualizarTotalExcecoes();
        });

        this.atualizarTotalExcecoes();
    }

    async salvarExcecoes() {
        try {
            // Desabilitar botão durante o salvamento
            const btnSalvarExcecoes = document.getElementById('btnSalvarExcecoes');
            btnSalvarExcecoes.disabled = true;
            btnSalvarExcecoes.innerHTML = 'Salvando...';

            // Coletar exceções da tabela
            const excecoes = [];
            
            // Selecionar todas as linhas da tabela
            const linhasExcecoes = document.querySelectorAll('#tabelaExcecoes tbody tr');
            
            linhasExcecoes.forEach(linha => {
                const professorSelect = linha.querySelector('.professor-select');
                const disciplinaSelect = linha.querySelector('.disciplina-select');
                const turmaInput = linha.querySelector('.turma-input');
                const tipoSelecionado = linha.querySelector('.btn-tipo.btn-primary');
                
                // Coletar dias selecionados
                const diasSelecionados = Array.from(linha.querySelectorAll('.btn-dia.active'))
                    .map(btn => btn.getAttribute('data-dia'));
                
                // Coletar horas selecionadas
                const horasSelecionadas = Array.from(linha.querySelectorAll('.btn-hora.active'))
                    .map(btn => btn.getAttribute('data-hora'));

                // Coletar limite de duas aulas
                const limiteDuasAulasBtn = linha.querySelector('.btn-limite-duas-aulas.btn-primary');

                // Coletar geminadas
                const geminadasBtn = linha.querySelector('.btn-geminadas.btn-primary');

                const excecao = {
                    professor: professorSelect.value,
                    disciplina: disciplinaSelect.value,
                    turma: turmaInput.value,
                    tipo: tipoSelecionado ? tipoSelecionado.getAttribute('data-tipo') : '',
                    limite_duas_aulas: limiteDuasAulasBtn ? limiteDuasAulasBtn.getAttribute('data-limite') : 'NÃO',
                    geminadas: geminadasBtn ? geminadasBtn.getAttribute('data-geminadas') : 'NÃO',
                    dias: diasSelecionados.join(','),
                    horas: horasSelecionadas.join(',')
                };

                console.log('Exceção coletada:', {
                    ...excecao,
                    limiteDuasAulasBtn: limiteDuasAulasBtn ? limiteDuasAulasBtn.outerHTML : 'Nenhum botão selecionado',
                    geminadasBtn: geminadasBtn ? geminadasBtn.outerHTML : 'Nenhum botão selecionado'
                });

                // Adicionar apenas se pelo menos um campo estiver preenchido
                if (Object.values(excecao).some(val => val && val.trim() !== '')) {
                    excecoes.push(excecao);
                }
            });
            
            // Enviar exceções para o backend
            const resposta = await fetch('/api/salvar_excecoes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(excecoes)
            });
            
            console.log('Exceções sendo salvas:', excecoes);
            
            const resultado = await resposta.json();
            
            if (resposta.ok) {
                this.mostrarMensagem(
                    `Exceções salvas com sucesso! ${resultado.total_excecoes_atualizadas} exceções atualizadas.`, 
                    'success'
                );
            } else {
                throw new Error(resultado.error || 'Erro ao salvar exceções');
            }
        } catch (error) {
            console.error('Erro ao salvar exceções:', error);
            this.mostrarMensagem(`Erro: ${error.message}`, 'danger');
        } finally {
            // Reabilitar botão
            const btnSalvarExcecoes = document.getElementById('btnSalvarExcecoes');
            btnSalvarExcecoes.disabled = false;
            btnSalvarExcecoes.innerHTML = 'Salvar Exceções';
        }
    }

    // Método para salvar seleções no localStorage
    salvarSelecoesPersistentes() {
        try {
            // Criar uma cópia profunda para evitar referências
            const selecoesSalvas = JSON.parse(JSON.stringify(this.selecoesPersistentes));
            
            // Limpar arrays vazios para economizar espaço
            Object.keys(selecoesSalvas.disponibilidades).forEach(key => {
                if (selecoesSalvas.disponibilidades[key].length === 0) {
                    delete selecoesSalvas.disponibilidades[key];
                }
            });

            Object.keys(selecoesSalvas.restricoes).forEach(key => {
                if (selecoesSalvas.restricoes[key].length === 0) {
                    delete selecoesSalvas.restricoes[key];
                }
            });

            selecoesSalvas.excecoes.disciplinaDuasAulas = 
                selecoesSalvas.excecoes.disciplinaDuasAulas.filter(Boolean);
            selecoesSalvas.excecoes.disciplinaConsecutivas = 
                selecoesSalvas.excecoes.disciplinaConsecutivas.filter(Boolean);
            selecoesSalvas.excecoes.professorDuasAulas = 
                selecoesSalvas.excecoes.professorDuasAulas.filter(Boolean);

            localStorage.setItem('horarioSelecoes', JSON.stringify(selecoesSalvas));
        } catch (error) {
            console.error('Erro ao salvar seleções:', error);
        }
    }

    // Método para carregar seleções do localStorage
    carregarSelecoesPersistentes() {
        try {
            const selecoesSalvas = localStorage.getItem('horarioSelecoes');
            if (selecoesSalvas) {
                // Estrutura padrão
                const estruturaPadrao = {
                    disponibilidades: {},
                    restricoes: {},
                    excecoes: {
                        disciplinaDuasAulas: [],
                        disciplinaConsecutivas: [],
                        professorDuasAulas: []
                    }
                };

                // Mesclar dados salvos com estrutura padrão
                const dadosSalvos = JSON.parse(selecoesSalvas);
                this.selecoesPersistentes = {
                    disponibilidades: dadosSalvos.disponibilidades || {},
                    restricoes: dadosSalvos.restricoes || {},
                    excecoes: {
                        disciplinaDuasAulas: dadosSalvos.excecoes?.disciplinaDuasAulas || [],
                        disciplinaConsecutivas: dadosSalvos.excecoes?.disciplinaConsecutivas || [],
                        professorDuasAulas: dadosSalvos.excecoes?.professorDuasAulas || []
                    }
                };
            }
        } catch (error) {
            console.error('Erro ao carregar seleções:', error);
            // Reiniciar seleções em caso de erro
            this.selecoesPersistentes = {
                disponibilidades: {},
                restricoes: {},
                excecoes: {
                    disciplinaDuasAulas: [],
                    disciplinaConsecutivas: [],
                    professorDuasAulas: []
                }
            };
        }
    }

    // Método para adicionar seleção persistente
    adicionarSelecaoPersistente(pagina, tipo, valor) {
        // Garantir que o objeto de seleções exista
        if (!this.selecoesPersistentes[pagina]) {
            this.selecoesPersistentes[pagina] = {};
        }

        // Garantir que o tipo de seleção exista
        if (!this.selecoesPersistentes[pagina][tipo]) {
            this.selecoesPersistentes[pagina][tipo] = [];
        }
        
        // Adicionar valor se não existir
        if (!this.selecoesPersistentes[pagina][tipo].includes(valor)) {
            this.selecoesPersistentes[pagina][tipo].push(valor);
        }
        
        // Salvar no localStorage
        this.salvarSelecoesPersistentes();
    }

    // Método para remover seleção persistente
    removerSelecaoPersistente(pagina, tipo, valor) {
        // Verificar se o objeto de seleções existe
        if (this.selecoesPersistentes[pagina] && this.selecoesPersistentes[pagina][tipo]) {
            // Remover valor específico
            this.selecoesPersistentes[pagina][tipo] = 
                this.selecoesPersistentes[pagina][tipo].filter(v => v !== valor);
            
            // Salvar no localStorage
            this.salvarSelecoesPersistentes();
        }
    }

    // Método para aplicar seleções persistentes
    aplicarSelecoesPersistentes(pagina) {
        if (pagina === 'disponibilidades') {
            // Aplicar seleções de disponibilidades
            if (this.selecoesPersistentes.disponibilidades.professor) {
                this.selecoesPersistentes.disponibilidades.professor.forEach(valorCompleto => {
                    const [professor, dia, hora] = valorCompleto.split('-');
                    const checkbox = document.querySelector(
                        `.dia-checkbox[data-professor="${professor}"][data-dia="${dia}"][data-hora="${hora}"]`
                    );
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }
        } else if (pagina === 'restricoes') {
            // Aplicar seleções de restrições
            if (this.selecoesPersistentes.restricoes.disciplina) {
                this.selecoesPersistentes.restricoes.disciplina.forEach(valorCompleto => {
                    const [disciplina, dia, hora] = valorCompleto.split('-');
                    const checkbox = document.querySelector(
                        `.dia-checkbox[data-disciplina="${disciplina}"][data-dia="${dia}"][data-hora="${hora}"]`
                    );
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }
        } else if (pagina === 'excecoes') {
            // Aplicar exceções
            const tipos = ['disciplinaDuasAulas', 'disciplinaConsecutivas', 'professorDuasAulas'];
            tipos.forEach(tipo => {
                const listaId = {
                    'disciplinaDuasAulas': 'listaDisciplinaDuasAulas',
                    'disciplinaConsecutivas': 'listaDisciplinaConsecutivas',
                    'professorDuasAulas': 'listaProfessorDuasAulas'
                }[tipo];

                const lista = document.getElementById(listaId);
                
                if (lista && this.selecoesPersistentes.excecoes[tipo]) {
                    // Limpar lista existente
                    lista.innerHTML = '';

                    // Adicionar itens salvos
                    this.selecoesPersistentes.excecoes[tipo].forEach(valor => {
                        const itemLista = document.createElement('li');
                        itemLista.className = 'list-group-item d-flex justify-content-between align-items-center';
                        itemLista.innerHTML = `
                            ${valor}
                            <button class="btn btn-danger btn-sm btn-excluir-excecao" 
                                    data-tipo="${tipo}" 
                                    data-valor="${valor}">
                                Excluir
                            </button>
                        `;
                        
                        lista.appendChild(itemLista);

                        // Adicionar event listener para botão de exclusão
                        itemLista.querySelector('.btn-excluir-excecao').addEventListener('click', (e) => {
                            const tipoExcecao = e.target.getAttribute('data-tipo');
                            const valorExcecao = e.target.getAttribute('data-valor');
                            
                            // Remover da lista de exceções
                            this.removerSelecaoPersistente('excecoes', tipoExcecao, valorExcecao);
                            
                            // Remover da lista visualmente
                            lista.removeChild(itemLista);
                        });
                    });
                }
            });
        }
    }

    // Método para limpar todas as seleções persistentes
    limparSelecoesPersistentes() {
        // Reiniciar objeto de seleções
        this.selecoesPersistentes = {
            disponibilidades: {},
            restricoes: {},
            excecoes: {
                disciplinaDuasAulas: [],
                disciplinaConsecutivas: [],
                professorDuasAulas: []
            }
        };

        // Limpar localStorage
        localStorage.removeItem('horarioSelecoes');

        // Desmarcar todos os checkboxes
        document.querySelectorAll('.dia-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Limpar listas de exceções
        ['listaDisciplinaDuasAulas', 'listaDisciplinaConsecutivas', 'listaProfessorDuasAulas']
            .forEach(listaId => {
                const lista = document.getElementById(listaId);
                if (lista) {
                    lista.innerHTML = '';
                }
            });
    }

    // Adicionar método para inicializar listeners de persistência
    inicializarListenersPersistencia() {
        // Botão de limpar seleções
        const btnLimparSelecoes = document.createElement('button');
        btnLimparSelecoes.id = 'btnLimparSelecoes';
        btnLimparSelecoes.className = 'btn btn-danger mt-3 me-2';
        btnLimparSelecoes.textContent = 'Limpar Todas as Seleções';
        btnLimparSelecoes.addEventListener('click', () => {
            this.limparSelecoesPersistentes();
        });

        // Botão de salvar seleções
        const btnSalvarSelecoes = document.createElement('button');
        btnSalvarSelecoes.id = 'btnSalvarSelecoes';
        btnSalvarSelecoes.className = 'btn btn-success mt-3 me-2';
        btnSalvarSelecoes.textContent = 'Salvar Seleções';
        btnSalvarSelecoes.addEventListener('click', () => {
            this.salvarSelecoesComo();
        });

        // Botão de carregar seleções
        const btnCarregarSelecoes = document.createElement('button');
        btnCarregarSelecoes.id = 'btnCarregarSelecoes';
        btnCarregarSelecoes.className = 'btn btn-primary mt-3';
        btnCarregarSelecoes.textContent = 'Carregar Seleções';
        btnCarregarSelecoes.addEventListener('click', () => {
            this.carregarSelecoes();
        });

        // Criar container para botões
        const containerBotoes = document.createElement('div');
        containerBotoes.className = 'd-flex justify-content-start align-items-center';
        containerBotoes.appendChild(btnLimparSelecoes);
        containerBotoes.appendChild(btnSalvarSelecoes);
        containerBotoes.appendChild(btnCarregarSelecoes);

        // Adicionar botões em locais apropriados
        const containerDisponibilidades = document.getElementById('disponibilidades-container');
        const containerRestricoes = document.getElementById('restricoes-container');
        const containerExcecoes = document.getElementById('excecoes-container');

        if (containerDisponibilidades) {
            containerDisponibilidades.appendChild(containerBotoes.cloneNode(true));
        }
        if (containerRestricoes) {
            containerRestricoes.appendChild(containerBotoes.cloneNode(true));
        }
        if (containerExcecoes) {
            containerExcecoes.appendChild(containerBotoes.cloneNode(true));
        }
    }

    // Método para salvar seleções em arquivo JSON
    async salvarSelecoesComo() {
        try {
            // Preparar dados para salvar
            const selecoesSalvas = {
                disponibilidades: this.selecoesPersistentes.disponibilidades,
                restricoes: this.selecoesPersistentes.restricoes,
                excecoes: this.selecoesPersistentes.excecoes,
                timestamp: new Date().toISOString()
            };

            // Criar blob com os dados
            const blob = new Blob([JSON.stringify(selecoesSalvas, null, 2)], {type: 'application/json'});
            
            // Criar link de download
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `selecoes_horario_${new Date().toISOString().replace(/:/g, '-')}.json`;
            
            // Adicionar link ao documento e disparar download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Mostrar mensagem de sucesso
            this.mostrarMensagem('Seleções salvas com sucesso!', 'success');
        } catch (error) {
            console.error('Erro ao salvar seleções:', error);
            this.mostrarMensagem('Erro ao salvar seleções', 'danger');
        }
    }

    // Método para carregar seleções de arquivo JSON
    async carregarSelecoes() {
        try {
            // Criar input para seleção de arquivo
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            
            input.onchange = async (event) => {
                const file = event.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    
                    reader.onload = async (e) => {
                        try {
                            const conteudo = e.target.result;
                            const selecoesSalvas = JSON.parse(conteudo);
                            
                            // Atualizar seleções persistentes
                            this.selecoesPersistentes = {
                                disponibilidades: selecoesSalvas.disponibilidades || {},
                                restricoes: selecoesSalvas.restricoes || {},
                                excecoes: selecoesSalvas.excecoes || {
                                    disciplinaDuasAulas: [],
                                    disciplinaConsecutivas: [],
                                    professorDuasAulas: []
                                }
                            };
                            
                            // Salvar no localStorage
                            this.salvarSelecoesPersistentes();
                            
                            // Aplicar seleções em todas as páginas
                            this.aplicarSelecoesPersistentes('disponibilidades');
                            this.aplicarSelecoesPersistentes('restricoes');
                            this.aplicarSelecoesPersistentes('excecoes');
                            
                            // Mostrar mensagem de sucesso
                            this.mostrarMensagem('Seleções carregadas com sucesso!', 'success');
                        } catch (parseError) {
                            console.error('Erro ao parsear arquivo JSON:', parseError);
                            this.mostrarMensagem('Erro ao carregar seleções. Arquivo inválido.', 'danger');
                        }
                    };
                    
                    reader.readAsText(file);
                }
            };
            
            // Disparar seleção de arquivo
            input.click();
        } catch (error) {
            console.error('Erro ao carregar seleções:', error);
            this.mostrarMensagem('Erro ao carregar seleções', 'danger');
        }
    }

    async salvarDisponibilidades() {
        try {
            // Desabilitar botão durante o salvamento
            const btnSalvarDisponibilidades = document.getElementById('btnSalvarDisponibilidades');
            btnSalvarDisponibilidades.disabled = true;
            btnSalvarDisponibilidades.innerHTML = 'Salvando...';

            // Coletar disponibilidades de todos os professores
            const disponibilidades = {};
            
            // Selecionar todos os professores na tabela
            const linhasProfessores = document.querySelectorAll('.table tbody tr');
            
            linhasProfessores.forEach(linha => {
                const nomeProfessor = linha.querySelector('td:first-child').textContent.trim();
                const disponibilidadesProfessor = {
                    'd_seg': this.coletarDisponibilidadeDia(linha, 'd_seg'),
                    'd_ter': this.coletarDisponibilidadeDia(linha, 'd_ter'),
                    'd_qua': this.coletarDisponibilidadeDia(linha, 'd_qua'),
                    'd_qui': this.coletarDisponibilidadeDia(linha, 'd_qui'),
                    'd_sex': this.coletarDisponibilidadeDia(linha, 'd_sex')
                };
                
                disponibilidades[nomeProfessor] = disponibilidadesProfessor;
            });
            
            // Enviar disponibilidades para o backend
            const resposta = await fetch('/api/salvar_disponibilidades', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(disponibilidades)
            });
            
            const resultado = await resposta.json();
            
            if (resposta.ok) {
                this.mostrarMensagem(
                    `Disponibilidades salvas com sucesso! ${resultado.total_professores_atualizados} professores atualizados.`, 
                    'success'
                );
            } else {
                throw new Error(resultado.error || 'Erro ao salvar disponibilidades');
            }
        } catch (error) {
            console.error('Erro ao salvar disponibilidades:', error);
            this.mostrarMensagem(`Erro: ${error.message}`, 'danger');
        } finally {
            // Reabilitar botão
            const btnSalvarDisponibilidades = document.getElementById('btnSalvarDisponibilidades');
            btnSalvarDisponibilidades.disabled = false;
            btnSalvarDisponibilidades.innerHTML = 'Salvar Disponibilidades';
        }
    }

    // Método auxiliar para coletar disponibilidade de um dia específico
    coletarDisponibilidadeDia(linha, dia) {
        const checkboxesDia = linha.querySelectorAll(`.dia-checkbox[data-dia="${dia}"]:checked`);
        const horasDia = Array.from(checkboxesDia)
            .map(checkbox => checkbox.value)
            .filter(hora => hora && hora.trim() !== '');  // Remover valores vazios
        
        // Remover duplicatas e ordenar
        const horasUnicas = [...new Set(horasDia)].sort((a, b) => parseInt(a) - parseInt(b));
        
        return horasUnicas.join(',');
    }

    atualizarTotalExcecoes() {
        const tabela = document.getElementById('tabelaExcecoes');
        const totalLinhas = tabela.querySelectorAll('tbody tr').length;
        const totalLinhasElement = document.querySelector('.alert-info');
        totalLinhasElement.innerHTML = `<strong>Total de Exceções:</strong> ${totalLinhas}`;
    }

    calcularTotalAulas() {
        // Método para calcular o número total de aulas necessárias
        const turno = this.turnoSelect.value;
        const numAulasPorTurno = {
            'Intermediario': 7,
            'Vespertino': 6,
            'Noturno': 3
        }[turno];

        let total = 0;
        console.log('🔢 Calculando total de aulas:');
        console.log('Turno:', turno);
        console.log('Número de aulas por turno:', numAulasPorTurno);
        
        for (let turma in this.turmas) {
            const numDisciplinas = this.turmas[turma].disciplinas.length;
            const totalAulasTurma = numDisciplinas * numAulasPorTurno;
            console.log(`Turma ${turma}: ${numDisciplinas} disciplinas x ${numAulasPorTurno} aulas = ${totalAulasTurma}`);
            total += totalAulasTurma;
        }

        const totalFinal = total * 5;
        console.log('Total de aulas (por turma * dias):', totalFinal);
        
        return totalFinal;
    }

    criarBotaoProgresso() {
        // Criar container para o botão flutuante
        const botaoProgresso = document.createElement('div');
        botaoProgresso.id = 'botao-progresso-alocacao';
        botaoProgresso.className = 'btn btn-info btn-lg position-fixed bottom-0 end-0 m-3 shadow-lg d-none';
        botaoProgresso.style.zIndex = '1050';
        botaoProgresso.innerHTML = 'Alocação: 0%';
        
        // Adicionar ao body
        document.body.appendChild(botaoProgresso);
        
        return botaoProgresso;
    }

    atualizarProgresso(percentual, tempoDecorrido = 0) {
        // Criar botão se não existir
        let botaoProgresso = document.getElementById('botao-progresso-alocacao');
        if (!botaoProgresso) {
            botaoProgresso = this.criarBotaoProgresso();
        }
        
        // Atualizar texto e visibilidade
        const textoProgresso = tempoDecorrido > 0 
            ? `Alocação: ${Math.round(percentual)}% (${tempoDecorrido.toFixed(1)}s)` 
            : `Alocação: ${Math.round(percentual)}%`;
        
        botaoProgresso.textContent = textoProgresso;
        botaoProgresso.classList.remove('d-none');
        
        // Alterar cor baseado no percentual
        if (percentual < 25) {
            botaoProgresso.className = 'btn btn-danger btn-lg position-fixed bottom-0 end-0 m-3 shadow-lg';
        } else if (percentual < 50) {
            botaoProgresso.className = 'btn btn-warning btn-lg position-fixed bottom-0 end-0 m-3 shadow-lg';
        } else if (percentual < 75) {
            botaoProgresso.className = 'btn btn-info btn-lg position-fixed bottom-0 end-0 m-3 shadow-lg';
        } else {
            botaoProgresso.className = 'btn btn-success btn-lg position-fixed bottom-0 end-0 m-3 shadow-lg';
        }
        
        // Esconder após 5 segundos se chegar a 100%
        if (percentual >= 100) {
            setTimeout(() => {
                botaoProgresso.classList.add('d-none');
            }, 5000);
        }
    }
}

new HorarioView();