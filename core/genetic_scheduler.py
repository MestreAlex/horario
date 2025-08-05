import sys
import os
import logging
import time
from typing import List, Dict, Any, Optional
import traceback
import random
import numpy as np
import pandas as pd
from deap import base, creator, tools, algorithms

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='scheduler_ml.log'
)
logger = logging.getLogger(__name__)

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, base_path)

try:
    from deap import base, creator, tools, algorithms
    import numpy as np
    import pandas as pd
    import random
    import json
    import pickle
    from typing import List, Dict, Any
    import time
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error, r2_score
except ImportError as e:
    print(f"Erro ao importar bibliotecas: {e}")
    sys.exit(1)

class ModeloAlocacaoHorarios:
    def __init__(self, 
                 taxa_aprendizado=0.01, 
                 fator_desconto=0.95, 
                 exploracao_inicial=1.0,
                 num_features=10,
                 max_tentativas=5):
        """
        Modelo de Machine Learning para otimização de horários com melhorias
        
        :param max_tentativas: Número máximo de tentativas para operações críticas
        """
        self.max_tentativas = max_tentativas
        
        # Métricas de desempenho expandidas
        self.metricas = {
            'tempo_execucao': [],
            'mse': [],
            'r2': [],
            'num_alocacoes': 0,
            'tentativas_fallback': 0,
            'erros_capturados': []
        }
        
        # Modelo de regressão para predição de qualidade de alocação
        self.modelo_regressao = RandomForestRegressor(
            n_estimators=100, 
            max_depth=10, 
            random_state=42
        )
        
        # Escalador para normalização de features
        self.scaler = StandardScaler()
        
        # Armazenamento de dados históricos
        self.historico_alocacoes = []
        self.historico_recompensas = []
        
        # Caminho para persistência de modelo
        self.caminho_modelo = os.path.join(base_path, 'modelo_alocacao_ml.pkl')
        
        # Métricas de desempenho
        self.metricas = {
            'mse': [],
            'r2': [],
            'num_alocacoes': 0
        }
    
    def _extrair_features(self, aula, turma, dia, horario):
        """
        Extrai características relevantes para representação de uma aula
        
        :return: Vetor de características
        """
        features = [
            # Características da disciplina
            len(aula['disciplina']),  # Complexidade do nome
            self._mapear_dia(dia),    # Codificação do dia
            horario,                  # Horário específico
            
            # Características do professor
            len(aula['professor']),   # Complexidade do nome
            
            # Características da turma
            len(turma),                # Complexidade do nome da turma
            
            # Características temporais
            self._calcular_distribuicao_aulas(turma, dia),
            self._calcular_carga_horaria_dia(turma, dia),
            
            # Características de aleatoriedade
            random.random(),           # Componente aleatória
            random.random(),           # Componente aleatória adicional
            random.random()            # Componente aleatória final
        ]
        
        return np.array(features)
    
    def _mapear_dia(self, dia):
        """
        Mapeia dias da semana para valores numéricos
        """
        dias_mapa = {'seg': 1, 'ter': 2, 'qua': 3, 'qui': 4, 'sex': 5}
        return dias_mapa.get(dia, 0)
    
    def _calcular_distribuicao_aulas(self, turma, dia):
        """
        Calcula a distribuição de aulas em um dia específico
        """
        # Implementação simplificada
        return random.random()
    
    def _calcular_carga_horaria_dia(self, turma, dia):
        """
        Calcula carga horária total de um dia
        """
        # Implementação simplificada
        return random.random()
    
    def _executar_com_fallback(self, funcao, *args, **kwargs):
        """
        Executa função com múltiplas tentativas e fallback
        
        :param funcao: Função a ser executada
        :return: Resultado da função ou valor padrão
        """
        for tentativa in range(self.max_tentativas):
            try:
                return funcao(*args, **kwargs)
            except Exception as e:
                logger.warning(f'Tentativa {tentativa+1} falhou: {e}')
                self.metricas['tentativas_fallback'] += 1
                self.metricas['erros_capturados'].append(str(e))
                
                # Estratégia de fallback com aleatoriedade
                if tentativa == self.max_tentativas - 1:
                    logger.error(f'Falha definitiva em {funcao.__name__}')
                    return self._fallback_padrao(*args, **kwargs)
                
                # Exponential backoff
                time.sleep(2 ** tentativa)
        
    def _fallback_padrao(self, *args, **kwargs):
        """
        Método de fallback genérico
        """
        logger.warning('Usando estratégia de fallback padrão')
        return random.choice(list(args)) if args else None
    
    def treinar(self, horarios_historico):
        """
        Treinar modelo com logging e métricas detalhadas
        """
        inicio = time.time()
        
        try:
            X_treino = []
            y_treino = []
            
            for horario in horarios_historico:
                for turma, grade in horario.items():
                    for dia, aulas in grade['dias'].items():
                        for horario_aula, aula in aulas.items():
                            if aula:
                                features = self._extrair_features(aula, turma, dia, horario_aula)
                                recompensa = self._calcular_recompensa(aula, turma, dia, horario_aula)
                                
                                X_treino.append(features)
                                y_treino.append(recompensa)
            
            # Preparar dados de treino
            if not X_treino or not y_treino:
                logger.warning('Nenhum dado de treinamento disponível')
                return
            
            X_treino = self.scaler.fit_transform(X_treino)
            
            # Dividir dados em treino e validação
            X_train, X_val, y_train, y_val = train_test_split(
                X_treino, y_treino, test_size=0.2, random_state=42
            )
            
            # Treinar modelo de regressão
            self.modelo_regressao.fit(X_train, y_train)
            
            # Avaliar modelo
            y_pred = self.modelo_regressao.predict(X_val)
            mse = mean_squared_error(y_val, y_pred)
            r2 = r2_score(y_val, y_pred)
            
            # Armazenar métricas
            self.metricas['mse'].append(mse)
            self.metricas['r2'].append(r2)
            
            # Métricas de desempenho
            tempo_total = time.time() - inicio
            self.metricas['tempo_execucao'].append(tempo_total)
            
            logger.info(f'Treinamento concluído em {tempo_total:.2f} segundos')
            logger.info(f'Métricas: MSE={mse}, R2={r2}')
            
            # Salvar modelo após treinamento
            self.salvar_modelo()
            
        except Exception as e:
            logger.error(f'Erro no treinamento: {e}')
            logger.error(traceback.format_exc())
            
            # Fallback para treinamento
            self._executar_com_fallback(self._treinar_fallback, horarios_historico)
    
    def _treinar_fallback(self, horarios_historico):
        """
        Método de treinamento alternativo com menos complexidade
        """
        logger.warning('Usando método de treinamento alternativo')
        
        # Implementação simplificada de treinamento
        X_treino = np.random.rand(len(horarios_historico), self.num_features)
        y_treino = np.random.rand(len(horarios_historico))
        
        self.modelo_regressao.fit(X_treino, y_treino)
    
    def gerar_relatorio_desempenho(self) -> Dict[str, Any]:
        """
        Gera relatório detalhado de desempenho do modelo
        
        :return: Dicionário com métricas de desempenho
        """
        return {
            'tempo_medio_execucao': np.mean(self.metricas['tempo_execucao']) if self.metricas['tempo_execucao'] else 0,
            'mse_medio': np.mean(self.metricas['mse']) if self.metricas['mse'] else 0,
            'r2_medio': np.mean(self.metricas['r2']) if self.metricas['r2'] else 0,
            'total_alocacoes': self.metricas['num_alocacoes'],
            'tentativas_fallback': self.metricas['tentativas_fallback'],
            'erros_capturados': self.metricas['erros_capturados'][:10]  # Limitar para não sobrecarregar
        }
    
    def salvar_relatorio(self, caminho='relatorio_ml.json'):
        """
        Salva relatório de desempenho em arquivo JSON
        """
        relatorio = self.gerar_relatorio_desempenho()
        
        try:
            with open(caminho, 'w') as f:
                json.dump(relatorio, f, indent=4)
            logger.info(f'Relatório salvo em {caminho}')
        except Exception as e:
            logger.error(f'Erro ao salvar relatório: {e}')
    
    def salvar_modelo(self):
        """
        Salva o modelo treinado
        """
        try:
            with open(self.caminho_modelo, 'wb') as f:
                pickle.dump({
                    'modelo': self.modelo_regressao,
                    'scaler': self.scaler,
                    'metricas': self.metricas
                }, f)
            print(f'Modelo salvo em {self.caminho_modelo}')
        except Exception as e:
            print(f'Erro ao salvar modelo: {e}')
    
    def carregar_modelo(self):
        """
        Carrega modelo treinado previamente
        """
        try:
            with open(self.caminho_modelo, 'rb') as f:
                dados = pickle.load(f)
                self.modelo_regressao = dados['modelo']
                self.scaler = dados['scaler']
                self.metricas = dados['metricas']
            print('Modelo carregado com sucesso!')
            return True
        except FileNotFoundError:
            print('Nenhum modelo salvo encontrado.')
            return False 

    def selecionar_professor(self, turma, disciplina):
        """
        Seleciona professor para uma turma e disciplina com estratégia avançada
        
        :return: Professor selecionado
        """
        try:
            # Filtrar professores da disciplina
            professores_candidatos = self.generator.professores_df[
                self.generator.professores_df['disciplina'] == disciplina
            ]
            
            if professores_candidatos.empty:
                logger.warning(f'⚠️ Nenhum professor foi encontrado para a disciplina {disciplina}')
                return None
            
            # Extrair características dos professores
            caracteristicas_professores = []
            for _, professor in professores_candidatos.iterrows():
                features = self._extrair_features_professor(professor, turma, disciplina)
                caracteristicas_professores.append(features)
            
            # Transformar características
            X_professores = self.scaler.transform(caracteristicas_professores)
            
            # Predizer qualidade da alocação
            qualidades = self.modelo_regressao.predict(X_professores)
            
            # Selecionar professor com maior qualidade
            indice_melhor = np.argmax(qualidades)
            melhor_professor = professores_candidatos.iloc[indice_melhor]['nome']
            
            logger.info(f'Professor selecionado para {disciplina}: {melhor_professor}')
            return melhor_professor
        
        except Exception as e:
            logger.error(f'Erro na seleção de professor: {e}')
            return self._selecao_professor_fallback(disciplina)
    
    def _extrair_features_professor(self, professor, turma, disciplina):
        """
        Extrai características detalhadas de um professor
        
        :return: Vetor de características
        """
        return [
            # Características do professor
            len(professor['nome']),  # Complexidade do nome
            professor['carga_horaria'] if 'carga_horaria' in professor else 0,
            
            # Características da disciplina
            len(disciplina),  # Complexidade da disciplina
            
            # Características da turma
            len(turma),  # Complexidade da turma
            
            # Características de disponibilidade
            self._calcular_disponibilidade(professor, turma),
            
            # Componentes aleatórios para diversidade
            random.random(),
            random.random(),
            random.random()
        ]
    
    def _calcular_disponibilidade(self, professor, turma):
        """
        Calcula pontuação de disponibilidade do professor
        
        :return: Pontuação de disponibilidade
        """
        try:
            # Lógica de verificação de disponibilidade
            dias_disponiveis = sum([
                int(professor.get(f'd_{dia}', '0')) > 0 
                for dia in ['seg', 'ter', 'qua', 'qui', 'sex']
            ])
            
            return dias_disponiveis / 5.0  # Normalizar entre 0 e 1
        except Exception as e:
            logger.warning(f'Erro ao calcular disponibilidade: {e}')
            return random.random()
    
    def _selecao_professor_fallback(self, disciplina):
        """
        Método de fallback para seleção de professor
        
        :return: Professor selecionado aleatoriamente
        """
        logger.warning(f'Usando seleção de professor fallback para {disciplina}')
        
        professores = self.generator.professores_df[
            self.generator.professores_df['disciplina'] == disciplina
        ]['nome'].tolist()
        
        return random.choice(professores) if professores else None

from .validator import HorarioValidator
from .horario_ml import HorarioML

class GeneticScheduleOptimizer:
    def __init__(self, schedule_generator):
        self.generator = schedule_generator
        self.modelo_ml = HorarioML(schedule_generator.data_path)
        self.validator = HorarioValidator(schedule_generator.data_path)
        
        # Configurações do algoritmo genético
        self.POPULATION_SIZE = 100
        self.P_CROSSOVER = 0.8
        self.P_MUTATION = 0.2
        self.MAX_GENERATIONS = 50
        self.TOURNAMENT_SIZE = 3
        
        # Cache e métricas
        self.fitness_cache = {}
        self.melhores_solucoes = []
        
    def _verificar_disponibilidade_professor(self, professor, dia, hora):
        """Verifica se um professor está disponível em um determinado horário"""
        try:
            dias_semana = ['seg', 'ter', 'qua', 'qui', 'sex']
            dia_str = dias_semana[dia]
            
            # Obter disponibilidade do professor
            disponibilidade = self.generator.professores_df[
                self.generator.professores_df['nome'] == professor
            ][f'd_{dia_str}'].iloc[0]
            
            if pd.isna(disponibilidade):
                return False
                
            # Converter disponibilidade para lista de horários
            horarios_disponiveis = str(disponibilidade).replace(';', ',').split(',')
            return str(hora) in horarios_disponiveis
            
        except Exception as e:
            print(f"Erro ao verificar disponibilidade: {e}")
            return False
            
    def _criar_individuo_inicial(self, disciplinas, professores_disponiveis):
        """Cria um indivíduo válido priorizando disponibilidade e restrições"""
        max_tentativas = 15  # Aumentado para mais tentativas
        dias = ['seg', 'ter', 'qua', 'qui', 'sex']
        
        for _ in range(max_tentativas):
            individuo = []
            alocacoes_professor = {}  # Controle de alocações por professor
            
            for i, disciplina in enumerate(disciplinas):
                dia = dias[i % 5]
                hora = (i // 5) + 1
                
                # Filtrar professores disponíveis
                profs_validos = []
                for professor in professores_disponiveis:
                    # Verificar disponibilidade
                    if not self._verificar_disponibilidade_professor(professor, i % 5, hora):
                        continue
                        
                    # Verificar restrições
                    resultado = self.validator.validar_alocacao(
                        professor=professor,
                        disciplina=disciplina,
                        turma=self.turma_atual,
                        dia=dia,
                        horario=hora
                    )
                    
                    # Verificar carga horária máxima por dia
                    alocacoes_dia = alocacoes_professor.get(professor, {}).get(dia, 0)
                    if alocacoes_dia >= 4:  # Máximo de 4 aulas por dia
                        continue
                        
                    if resultado['valido']:
                        profs_validos.append(professor)
                
                if profs_validos:
                    # Selecionar professor com menor carga
                    professor_selecionado = min(
                        profs_validos,
                        key=lambda p: sum(alocacoes_professor.get(p, {}).values())
                    )
                    
                    # Atualizar controle de alocações
                    if professor_selecionado not in alocacoes_professor:
                        alocacoes_professor[professor_selecionado] = {}
                    if dia not in alocacoes_professor[professor_selecionado]:
                        alocacoes_professor[professor_selecionado][dia] = 0
                    alocacoes_professor[professor_selecionado][dia] += 1
                    
                    individuo.append(professor_selecionado)
                else:
                    individuo.append(None)
            
            # Verificar se o indivíduo é minimamente válido
            if any(individuo) and len([x for x in individuo if x is not None]) >= len(disciplinas) * 0.7:
                return individuo
        
        # Fallback: criar indivíduo com alocações mínimas
        return self._criar_individuo_fallback(disciplinas, professores_disponiveis)
        
    def _criar_individuo_fallback(self, disciplinas, professores_disponiveis):
        """Método de fallback para criar indivíduo quando o método principal falha"""
        individuo = []
        for disciplina in disciplinas:
            # Tentar encontrar pelo menos um professor válido
            prof_valido = None
            for professor in professores_disponiveis:
                if self._professor_pode_lecionar(professor, disciplina):
                    prof_valido = professor
                    break
            
            individuo.append(prof_valido if prof_valido else random.choice(professores_disponiveis))
        
        return individuo

    def _professor_pode_lecionar(self, professor, disciplina):
        """Verifica se um professor pode lecionar uma disciplina"""
        prof_df = self.generator.professores_df
        return any((prof_df['nome'] == professor) & 
                  (prof_df['disciplina'] == disciplina))

    def _calcular_fitness(self, individuo, turma):
        """Calcula fitness considerando restrições e disponibilidades"""
        # Usar cache se disponível
        individuo_key = (tuple(individuo), turma)
        if individuo_key in self.fitness_cache:
            return self.fitness_cache[individuo_key]

        # Inicializar pontuação
        score_total = 0
        peso_disponibilidade = 0.4
        peso_restricoes = 0.3
        peso_ml = 0.3

        # Verificar disponibilidade dos professores
        score_disponibilidade = 0
        total_aulas = 0
        for i, professor in enumerate(individuo):
            if professor:
                total_aulas += 1
                dia = i % 5
                hora = (i // 5) + 1
                dias_semana = ['seg', 'ter', 'qua', 'qui', 'sex']
                if self._verificar_disponibilidade_professor(professor, dia, hora):
                    score_disponibilidade += 1

        if total_aulas > 0:
            score_disponibilidade = (score_disponibilidade / total_aulas) * 100

        # Verificar restrições das disciplinas
        score_restricoes = 0
        total_disciplinas = 0
        for i, (professor, disciplina) in enumerate(zip(individuo, self.disciplinas[turma])):
            if professor:
                total_disciplinas += 1
                dia = i % 5
                hora = (i // 5) + 1
                dias_semana = ['seg', 'ter', 'qua', 'qui', 'sex']
                resultado = self.validator._validar_restricoes(professor, disciplina, turma, dias_semana[dia], hora)
                if resultado['valido']:
                    score_restricoes += 1

        if total_disciplinas > 0:
            score_restricoes = (score_restricoes / total_disciplinas) * 100

        # Obter score do modelo ML
        horario_parcial = self._converter_para_formato_horario(individuo, turma)
        score_ml = self.modelo_ml.prever_score(horario_parcial)

        # Calcular score final ponderado
        score_total = (peso_disponibilidade * score_disponibilidade +
                      peso_restricoes * score_restricoes +
                      peso_ml * score_ml)

        # Armazenar no cache
        self.fitness_cache[individuo_key] = score_total
        return score_total

    def _calcular_distribuicao_carga(self, individuo):
        """Calcula estatísticas da distribuição de carga horária"""
        carga_por_professor = {}
        for professor in individuo:
            if professor:
                carga_por_professor[professor] = carga_por_professor.get(professor, 0) + 1
        
        if not carga_por_professor:
            return {'media': 0, 'desvio_padrao': 0}
        
        cargas = list(carga_por_professor.values())
        return {
            'media': np.mean(cargas),
            'desvio_padrao': np.std(cargas)
        }

    def _verificar_conflitos_horario(self, individuo):
        """Conta número de conflitos de horário no indivíduo"""
        conflitos = 0
        horarios_prof = {}
        
        for i, professor in enumerate(individuo):
            if professor:
                dia = i % 5  # 5 dias na semana
                hora = i // 5
                
                if professor not in horarios_prof:
                    horarios_prof[professor] = set()
                
                horario = (dia, hora)
                if horario in horarios_prof[professor]:
                    conflitos += 1
                horarios_prof[professor].add(horario)
        
        return conflitos

    def _contar_janelas(self, individuo):
        """Conta número de janelas (períodos vazios) no horário"""
        janelas = 0
        horarios_prof = {}
        
        for i, professor in enumerate(individuo):
            if professor:
                dia = i % 5
                hora = i // 5
                
                if professor not in horarios_prof:
                    horarios_prof[professor] = {}
                if dia not in horarios_prof[professor]:
                    horarios_prof[professor][dia] = set()
                    
                horarios_prof[professor][dia].add(hora)
        
        # Contar janelas para cada professor
        for professor, dias in horarios_prof.items():
            for dia, horas in dias.items():
                if len(horas) > 1:
                    horas_ordenadas = sorted(list(horas))
                    for i in range(len(horas_ordenadas) - 1):
                        if horas_ordenadas[i + 1] - horas_ordenadas[i] > 1:
                            janelas += 1
        
        return janelas

    def _calcular_score_preferencias(self, individuo):
        """Calcula pontuação baseada nas preferências dos professores"""
        score = 0
        for i, professor in enumerate(individuo):
            if professor:
                dia = i % 5
                hora = i // 5
                
                # Verificar disponibilidade do professor
                if self._verificar_disponibilidade_professor(professor, dia, hora):
                    score += 5
                # Verificar preferências específicas
                if self._verificar_preferencias_especificas(professor, dia, hora):
                    score += 3
        
        return score

    def _verificar_disponibilidade_professor(self, professor, dia, hora):
        """Verifica se o professor está disponível no horário específico"""
        dias_semana = ['seg', 'ter', 'qua', 'qui', 'sex']
        dia_nome = dias_semana[dia]
        
        prof_df = self.generator.professores_df
        disponibilidade = prof_df[prof_df['nome'] == professor][f'd_{dia_nome}'].iloc[0]
        
        if pd.isna(disponibilidade) or not disponibilidade:
            return False
            
        horas_disponiveis = str(disponibilidade).split(',')
        return str(hora + 1) in horas_disponiveis

    def _verificar_preferencias_especificas(self, professor, dia, hora):
        """Verifica preferências específicas do professor"""
        try:
            # Carregar exceções/preferências
            excecoes_df = pd.read_csv(os.path.join(self.generator.data_path, 'excecoes.csv'))
            
            # Filtrar exceções do professor
            exc_prof = excecoes_df[excecoes_df['professor'] == professor]
            
            if exc_prof.empty:
                return True  # Sem exceções = disponível
                
            dias_semana = ['seg', 'ter', 'qua', 'qui', 'sex']
            dia_nome = dias_semana[dia]
            
            for _, excecao in exc_prof.iterrows():
                if dia_nome in str(excecao['dias']).split(','):
                    if str(hora + 1) in str(excecao['horas']).split(','):
                        return excecao['tipo'] == 'SIM'
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Erro ao verificar preferências: {e}")
            return True

    def otimizar_horario(self, turma, disciplinas):
        """Otimiza horário usando algoritmo genético com ML"""
        self.disciplinas[turma] = disciplinas
        
        # Configurar algoritmo genético
        if 'FitnessMax' not in creator.__dict__:
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        if 'Individual' not in creator.__dict__:
            creator.create("Individual", list, fitness=creator.FitnessMax)
        
        toolbox = base.Toolbox()
        
        # Registrar operações genéticas
        professores_disponiveis = self.generator.professores_df['nome'].unique()
        toolbox.register("individuo", self._criar_individuo_inicial, 
                        disciplinas, professores_disponiveis)
        toolbox.register("population", tools.initRepeat, list, toolbox.individuo)
        
        # Registro de operadores genéticos
        toolbox.register("evaluate", lambda ind: (self._calcular_fitness(ind, turma),))
        toolbox.register("mate", tools.cxTwoPoint)
        toolbox.register("mutate", self._mutacao_custom)
        toolbox.register("select", tools.selTournament, tournsize=self.TOURNAMENT_SIZE)
        
        # Criar população inicial
        pop = toolbox.population(n=self.POPULATION_SIZE)
        
        # Loop principal do algoritmo genético
        for gen in range(self.MAX_GENERATIONS):
            # Selecionar próxima geração
            offspring = algorithms.varAnd(pop, toolbox, 
                                       cxpb=self.P_CROSSOVER, 
                                       mutpb=self.P_MUTATION)
            
            # Avaliar indivíduos
            fits = toolbox.map(toolbox.evaluate, offspring)
            for fit, ind in zip(fits, offspring):
                ind.fitness.values = fit
            
            # Atualizar população
            pop = toolbox.select(offspring + pop, k=len(pop))
            
            # Guardar melhor solução da geração
            melhor = tools.selBest(pop, k=1)[0]
            horario_melhor = self._converter_para_formato_horario(melhor, turma)
            self.melhores_solucoes.append({
                'geracao': gen,
                'fitness': melhor.fitness.values[0],
                'horario': horario_melhor
            })
            
            # Registrar para treinamento do ML
            self.modelo_ml.registrar_horario(
                horario_melhor,
                melhor.fitness.values[0]
            )
            
            # Verificar critério de parada
            if melhor.fitness.values[0] >= 95:
                break
        
        # Retornar melhor solução
        melhor_individuo = tools.selBest(pop, k=1)[0]
        horario_final = self._converter_para_formato_horario(melhor_individuo, turma)
        
        # Obter sugestões de melhoria
        sugestoes = self.modelo_ml.sugerir_melhoria(horario_final)
        if sugestoes:
            self.logger.info("Sugestões de melhoria:")
            for sugestao in sugestoes:
                self.logger.info(f"- {sugestao['mensagem']}")
        
        return horario_final

    def _mutacao_custom(self, individuo, indpb=0.05):
        """Operador de mutação customizado"""
        for i in range(len(individuo)):
            if random.random() < indpb:
                disciplina = self.disciplinas[list(self.disciplinas.keys())[0]][i]
                profs_disciplina = [p for p in self.generator.professores_df['nome'].unique() 
                                  if self._professor_pode_lecionar(p, disciplina)]
                if profs_disciplina:
                    individuo[i] = random.choice(profs_disciplina)
        
        return individuo,

    def _converter_para_formato_horario(self, individuo, turma):
        """Converte um indivíduo em formato de horário"""
        horario = {
            'dias': {
                'seg': {}, 'ter': {}, 'qua': {}, 'qui': {}, 'sex': {}
            }
        }
        
        dias = ['seg', 'ter', 'qua', 'qui', 'sex']
        
        for i, (professor, disciplina) in enumerate(zip(individuo, self.disciplinas[turma])):
            if professor:
                dia = dias[i % 5]
                hora = (i // 5) + 1
                
                horario['dias'][dia][hora] = {
                    'professor': professor,
                    'disciplina': disciplina
                }
        
        return horario

def otimizar_horario_genetico(schedule_generator, max_geracoes=50, tempo_limite=600):
    """Função principal de otimização"""
    otimizador = GeneticScheduleOptimizer(schedule_generator)
    horarios_otimizados = {}
    
    for turma, info in schedule_generator.turmas.items():
        print(f"Otimizando horário para turma: {turma}")
        horario = otimizador.otimizar_horario(turma, info['disciplinas'])
        horarios_otimizados[turma] = horario
        
        # Notificar progresso
        progresso = (len(horarios_otimizados) / len(schedule_generator.turmas)) * 100
        notificar_progresso(progresso)
    
    return horarios_otimizados

def notificar_progresso(progresso):
    """
    Função global para notificar progresso
    
    :param progresso: Percentual de progresso (0-100)
    """
    try:
        # Formatar mensagem de status
        status = f"\n{'=' * 50}\n"
        status += f"🧬 Algoritmo Genético\n"
        status += f"📊 Progresso: {progresso:.1f}%\n"
        status += f"⏳ O sistema está gerando o horário, por favor aguarde...\n"
        status += f"{'=' * 50}"
        
        print(status)
        
        # Tentar importar método de notificação se disponível
        try:
            from scheduler.api.app import notificar_progresso as frontend_notificar
            frontend_notificar(progresso)
        except ImportError:
            # Silenciosamente ignorar se não puder importar
            pass
    except Exception as e:
        print(f"\n⚠️ Erro ao notificar progresso: {e}")
        print(f"🔄 Progresso atual: {progresso}%")