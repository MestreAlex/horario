import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
import random
import logging
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import json
import traceback

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Usar sys.stdout para melhor suporte Unicode
        logging.FileHandler('schedule_generator.log', mode='w', encoding='utf-8')  # Especificar encoding
    ]
)

class ScheduleGenerator:
    def __init__(self, data_path):
        """
        Inicializa o gerador de horários
        
        :param data_path: Caminho para a pasta com arquivos de dados
        """
        self.data_path = data_path
        self.dias = ['seg', 'ter', 'qua', 'qui', 'sex']
        
        # Estado para backtracking
        self.estados_alocacao = []
        self.max_tentativas_backtrack = 5
        
        # Carregar dados
        self.professores_df = pd.read_csv(os.path.join(data_path, 'professores_disciplinas_turmas.csv'))
        
        # Log de dados do CSV
        print("🔍 DADOS DO CSV:")
        print(self.professores_df.head())
        print("\nColunas:", list(self.professores_df.columns))
        print("\nTurnos únicos:", self.professores_df['turno'].unique())
        
        # Pré-processamento de dados
        self.professores_df['total_aulas_disciplina'] = self.professores_df.groupby(['turma', 'disciplina'])['carga_horaria'].transform('first')
        self.professores_df.reset_index(inplace=True)  # Restaurar o índice original
        
        # Adicionar log para verificar o DataFrame
        print("🔍 DADOS DO CSV APÓS PROCESSAMENTO:")
        print(self.professores_df.head())
        print("\nColunas:", list(self.professores_df.columns))
        
        # Estrutura global para rastrear alocações
        self.grade_horarios_global = {
            dia: np.array([None] * 35) for dia in self.dias
        }
        
        # Dicionário para rastrear alocações por turma
        self.grade_horarios_turmas = {}
        
        # Dicionário para rastrear disponibilidade dos professores
        self.disponibilidade_professores = {}
        
        # Inicializar vetores de disponibilidade para todos os professores
        for professor in self.professores_df.reset_index()['nome'].unique():
            self.disponibilidade_professores[professor] = np.zeros(35, dtype=bool)
        
        # Lista de alocações incompletas
        self.alocacoes_incompletas = []
        
        # Carregar exceções
        try:
            self.excecoes_df = pd.read_csv(os.path.join(data_path, 'excecoes.csv'))
            print("✅ Exceções carregadas com sucesso")
            
            # Filtro específico para Eletiva
            self.excecoes_eletiva = self.excecoes_df[
                (self.excecoes_df['disciplina'] == 'ELETIVA') & 
                (self.excecoes_df['limite_duas_aulas'] == 'SIM')
            ]
        except Exception as e:
            print(f"❌ Erro ao carregar exceções: {e}")
            self.excecoes_df = pd.DataFrame()  # DataFrame vazio se falhar
            self.excecoes_eletiva = pd.DataFrame()
    
    @lru_cache(maxsize=1000)
    def verificar_conflito_global(self, posicao):
        """
        Verifica se há conflito global em uma posição específica com memoização
        
        :param posicao: Posição no vetor de horários
        :return: True se houver conflito, False caso contrário
        """
        return any(
            grade[posicao] is not None 
            for grade in self.grade_horarios_global.values()
        )
    
    @lru_cache(maxsize=1000)
    def professor_ja_alocado_no_dia(self, professor, posicao):
        """
        Verifica se o professor já está alocado em algum dia nesta posição com memoização
        
        :param professor: Nome do professor
        :param posicao: Posição no vetor de horários
        :return: True se já alocado, False caso contrário
        """
        return any(
            grade[posicao] is not None and 
            grade[posicao]['professor'] == professor
            for grade in self.grade_horarios_global.values()
        )
    
    def professor_ja_alocado_em_turmas(self, professor, posicao, turma_atual):
        """
        Verifica se o professor já está alocado em uma posição específica em outras turmas
        
        :param professor: Nome do professor
        :param posicao: Posição no vetor de horários
        :param turma_atual: Turma atual sendo processada
        :return: True se já alocado, False caso contrário
        """
        # Criar uma cópia da lista de turmas para evitar modificação durante iteração
        turmas = list(self.grade_horarios_turmas.keys())
        
        for turma in turmas:
            if turma == turma_atual:
                continue
            
            grade = self.grade_horarios_turmas.get(turma, [None] * 35)
            
            if grade[posicao] is not None and grade[posicao]['professor'] == professor:
                return True
        
        return False
    
    def alocar_aulas_turma(self, turma):
        """
        Aloca aulas para uma turma específica com verificações rigorosas
        
        :param turma: Nome da turma
        :return: Dicionário com horário da turma
        """
        print(f"🏫 INICIANDO ALOCAÇÃO PARA TURMA: {turma}")
        
        # Inicializar grade de horários para a turma
        self.grade_horarios_turmas[turma] = {
            dia: np.array([None] * 7) for dia in self.dias
        }
        
        # Obter disciplinas para a turma
        disciplinas_turma = self.professores_df[
            self.professores_df['turma'] == turma
        ].drop_duplicates(subset=['disciplina'])
        
        # Ordenar disciplinas por carga horária (priorizar disciplinas com mais aulas)
        disciplinas_turma = disciplinas_turma.sort_values('total_aulas_disciplina', ascending=False)
        
        print(f"📝 DISCIPLINAS PARA {turma}: {list(disciplinas_turma['disciplina'])}")
        
        # Iterar sobre disciplinas
        for _, disciplina_row in disciplinas_turma.iterrows():
            disciplina = disciplina_row['disciplina']
            carga_horaria = disciplina_row['total_aulas_disciplina']
            
            print(f"🔬 ALOCANDO DISCIPLINA: {disciplina}")
            print(f"⏱️ CARGA HORÁRIA: {carga_horaria}")
            
            # Acompanhar aulas alocadas
            aulas_alocadas = 0
            
            # Tentar alocar aulas em dias e posições diferentes
            for dia in self.dias:
                for posicao in range(7):
                    # Verificar se já atingiu a carga horária
                    if aulas_alocadas >= carga_horaria:
                        break
                    
                    # Verificar conflitos globais e na turma
                    if (self.verificar_conflito_global(posicao) or 
                        self.grade_horarios_turmas[turma][dia][posicao] is not None):
                        continue
                    
                    # Selecionar professor para a disciplina
                    professor = self.selecionar_professor_para_disciplina(
                        disciplina, turma, dia, posicao
                    )
                    
                    # Se professor encontrado, alocar aula
                    if professor:
                        aula = {
                            'disciplina': disciplina,
                            'professor': professor,
                            'turma': turma
                        }
                        
                        # Registrar alocação
                        self.grade_horarios_global[dia][posicao] = aula
                        self.grade_horarios_turmas[turma][dia][posicao] = aula
                        
                        # Marcar disponibilidade do professor
                        self.disponibilidade_professores[professor][posicao] = True
                        
                        print(f"✅ AULA ALOCADA: {disciplina} - {professor} - Dia {dia} - Posição {posicao}")
                        
                        aulas_alocadas += 1
            
            # Verificar se todas as aulas foram alocadas
            if aulas_alocadas < carga_horaria:
                print(f"⚠️ ALOCAÇÃO INCOMPLETA: {disciplina}")
                print(f"   Aulas previstas: {carga_horaria}")
                print(f"   Aulas alocadas: {aulas_alocadas}")
                
                self.alocacoes_incompletas.append({
                    'turma': turma,
                    'disciplina': disciplina,
                    'aulas_previstas': carga_horaria,
                    'aulas_alocadas': aulas_alocadas
                })
        
        print(f"🏁 FINALIZADA ALOCAÇÃO PARA TURMA: {turma}")
        
        return self.grade_horarios_turmas[turma]
    
    def limpar_disponibilidade_professores(self):
        """
        Limpa os vetores de disponibilidade de todos os professores
        """
        for professor in self.disponibilidade_professores:
            self.disponibilidade_professores[professor] = np.zeros(35, dtype=bool)
    
    def notificar_progresso(self, progresso, etapa=None, detalhes=None):
        """
        Método para notificar o frontend sobre o progresso de geração de horário
        
        :param progresso: Percentual de progresso (0-100)
        :param etapa: Etapa atual do processo
        :param detalhes: Detalhes adicionais sobre o progresso
        """
        try:
            # Formatar mensagem de status
            status = f"\n{'=' * 50}\n"
            status += f"🔄 PROGRESSO DA GERAÇÃO: {progresso:.1f}%\n"
            
            if etapa:
                status += f"📍 ETAPA ATUAL: {etapa}\n"
            if detalhes:
                status += f"ℹ️ DETALHES: {detalhes}\n"
                
            status += f"{'=' * 50}"
            
            print(status)
            
            # Notificar frontend
            from scheduler.api.app import notificar_progresso
            notificar_progresso(progresso)
            
        except Exception as e:
            print(f"\n⚠️ ERRO AO NOTIFICAR PROGRESSO: {e}")
    
    def salvar_estado(self):
        """Salva o estado atual das alocações para backtracking"""
        estado = {
            'global': {dia: grade.copy() for dia, grade in self.grade_horarios_global.items()},
            'turmas': {turma: {dia: grade.copy() for dia, grade in grades.items()} 
                      for turma, grades in self.grade_horarios_turmas.items()},
            'disponibilidade': {prof: disp.copy() 
                              for prof, disp in self.disponibilidade_professores.items()},
            'incompletas': self.alocacoes_incompletas.copy()
        }
        self.estados_alocacao.append(estado)
        
    def restaurar_estado(self):
        """Restaura o último estado salvo das alocações"""
        if self.estados_alocacao:
            estado = self.estados_alocacao.pop()
            self.grade_horarios_global = estado['global']
            self.grade_horarios_turmas = estado['turmas']
            self.disponibilidade_professores = estado['disponibilidade']
            self.alocacoes_incompletas = estado['incompletas']
            return True
        return False
    
    def gerar_horario(self, turno=None):
        """
        Gera horário para um turno específico usando abordagem centrada no professor com backtracking
        
        :param turno: Turno a ser processado (opcional)
        :return: Dicionário com grades de horários
        """
        max_tentativas_geracao = 50
        max_backtrack_depth = 10
        
        # Mapear turno
        turno_map = {'I': 'Intermediario', 'T': 'Vespertino', 'N': 'Noturno'}
        turno_nome = turno_map.get(turno, turno)
        
        # Filtrar e validar turmas
        df_filtrado = self.professores_df.copy()
        if turno_nome:
            df_filtrado = df_filtrado[df_filtrado['turno'] == turno_nome]
        
        # Obter lista única de turmas
        turmas = df_filtrado['turma'].unique()
        
        if len(turmas) == 0:
            print(f"❌ ERRO: Nenhuma turma encontrada para o turno {turno_nome}")
            print("Por favor, verifique se o arquivo 'professores_disciplinas_turmas.csv' está correto.")
            return {}
        
        print(f"✅ Turmas encontradas: {turmas}")
        
        melhor_solucao = None
        menor_conflitos = float('inf')
        
        for tentativa in range(max_tentativas_geracao):
            print(f"🔍 INICIANDO GERAÇÃO DE HORÁRIO - TURNO: {turno_nome} - TENTATIVA {tentativa + 1}")
            
            self.notificar_progresso((tentativa / max_tentativas_geracao) * 100)
            
            # Limpar estruturas
            self.grade_horarios_global = {dia: np.array([None] * 35) for dia in self.dias}
            self.grade_horarios_turmas = {}
            self.alocacoes_incompletas = []
            self.limpar_disponibilidade_professores()
            self.estados_alocacao = []
            
            # Inicializar grades das turmas
            for turma in turmas:
                self.grade_horarios_turmas[turma] = {dia: np.array([None] * 7) for dia in self.dias}
                print(f"✅ Grade inicializada para a turma: {turma}")
            
            # Salvar estado inicial
            self.salvar_estado()
            
            backtrack_count = 0
            progresso_anterior = 0
            
            # Tentar alocar aulas para cada turma
            for turma in turmas:
                disciplinas_turma = df_filtrado[df_filtrado['turma'] == turma].sort_values('total_aulas_disciplina', ascending=False)
                
                for _, disciplina_row in disciplinas_turma.iterrows():
                    if not self.alocar_disciplina(turma, disciplina_row):
                        # Se falhar, tentar backtracking
                        if backtrack_count < max_backtrack_depth and self.restaurar_estado():
                            backtrack_count += 1
                            print(f"🔄 Tentando backtracking #{backtrack_count} para a turma {turma}")
                            continue
                        break
                    
                    # Salvar estado após alocação bem-sucedida
                    self.salvar_estado()
                    
                    # Calcular progresso
                    progresso_atual = len([x for x in self.grade_horarios_turmas[turma].values() if x is not None])
                    if progresso_atual > progresso_anterior:
                        progresso_anterior = progresso_atual
                        self.notificar_progresso((tentativa / max_tentativas_geracao) * 100 + (progresso_atual / len(turmas)) * 100)
            
            # Avaliar solução atual
            conflitos_atuais = len(self.alocacoes_incompletas)
            if conflitos_atuais < menor_conflitos:
                menor_conflitos = conflitos_atuais
                melhor_solucao = {
                    'global': self.grade_horarios_global.copy(),
                    'turmas': {t: g.copy() for t, g in self.grade_horarios_turmas.items()}
                }
                
                if conflitos_atuais == 0:
                    print("✨ Solução ótima encontrada!")
                    break
        
        # Restaurar melhor solução encontrada
        if melhor_solucao:
            self.grade_horarios_global = melhor_solucao['global']
            self.grade_horarios_turmas = melhor_solucao['turmas']
            
        return self.grade_horarios_turmas
    
    def tentar_alocacao_temporaria(self, professor, disciplina, turma, dia, posicao):
        """
        Tenta uma alocação temporária antes de confirmar
        """
        # Create temporary allocation
        aula = {
            'disciplina': disciplina,
            'professor': professor,
            'turma': turma
        }
        
        # Initialize temporary structures if needed
        if dia not in self.alocacoes_temporarias['global']:
            self.alocacoes_temporarias['global'][dia] = np.array([None] * 7)
        if turma not in self.alocacoes_temporarias['turmas']:
            self.alocacoes_temporarias['turmas'][turma] = {d: np.array([None] * 7) for d in self.dias}
        if professor not in self.alocacoes_temporarias['disponibilidade']:
            self.alocacoes_temporarias['disponibilidade'][professor] = np.zeros(7, dtype=bool)
        
        # Check for conflicts in temporary allocation
        if (self.alocacoes_temporarias['global'][dia][posicao] is not None or
            self.alocacoes_temporarias['turmas'][turma][dia][posicao] is not None):
            return False
            
        # Make temporary allocation
        self.alocacoes_temporarias['global'][dia][posicao] = aula
        self.alocacoes_temporarias['turmas'][turma][dia][posicao] = aula
        self.alocacoes_temporarias['disponibilidade'][professor][posicao] = True
        
        return True
    
    def confirmar_alocacao_temporaria(self):
        """
        Confirma alocações temporárias como permanentes
        """
        self.grade_horarios_global.update(self.alocacoes_temporarias['global'])
        
        for turma, grade in self.alocacoes_temporarias['turmas'].items():
            if turma not in self.grade_horarios_turmas:
                self.grade_horarios_turmas[turma] = {}
            self.grade_horarios_turmas[turma].update(grade)
        
        for prof, disp in self.alocacoes_temporarias['disponibilidade'].items():
            if prof not in self.disponibilidade_professores:
                self.disponibilidade_professores[prof] = np.zeros(7, dtype=bool)
            self.disponibilidade_professores[prof] |= disp
        
        # Clear temporary allocations
        self.alocacoes_temporarias = {
            'global': {},
            'turmas': {},
            'disponibilidade': {}
        }
        
    def desfazer_alocacao_temporaria(self):
        """
        Desfaz todas as alocações temporárias
        """
        self.alocacoes_temporarias = {
            'global': {},
            'turmas': {},
            'disponibilidade': {}
        }
        self.tentativas_por_slot = {}
    def tentar_alocacao_temporaria(self, professor, disciplina, turma, dia, posicao):
        """
        Tenta uma alocação temporária antes de confirmar
        """
        # Create temporary allocation
        aula = {
            'disciplina': disciplina,
            'professor': professor,
            'turma': turma
        }
        
        # Initialize temporary structures if needed
        if dia not in self.alocacoes_temporarias['global']:
            self.alocacoes_temporarias['global'][dia] = np.array([None] * 7)
        if turma not in self.alocacoes_temporarias['turmas']:
            self.alocacoes_temporarias['turmas'][turma] = {d: np.array([None] * 7) for d in self.dias}
        if professor not in self.alocacoes_temporarias['disponibilidade']:
            self.alocacoes_temporarias['disponibilidade'][professor] = np.zeros(7, dtype=bool)
        
        # Check for conflicts in temporary allocation
        if (self.alocacoes_temporarias['global'][dia][posicao] is not None or
            self.alocacoes_temporarias['turmas'][turma][dia][posicao] is not None):
            return False
            
        # Make temporary allocation
        self.alocacoes_temporarias['global'][dia][posicao] = aula
        self.alocacoes_temporarias['turmas'][turma][dia][posicao] = aula
        self.alocacoes_temporarias['disponibilidade'][professor][posicao] = True
        
        return True
    
    def confirmar_alocacao_temporaria(self):
        """
        Confirma alocações temporárias como permanentes
        """
        self.grade_horarios_global.update(self.alocacoes_temporarias['global'])
        
        for turma, grade in self.alocacoes_temporarias['turmas'].items():
            if turma not in self.grade_horarios_turmas:
                self.grade_horarios_turmas[turma] = {}
            self.grade_horarios_turmas[turma].update(grade)
        
        for prof, disp in self.alocacoes_temporarias['disponibilidade'].items():
            if prof not in self.disponibilidade_professores:
                self.disponibilidade_professores[prof] = np.zeros(7, dtype=bool)
            self.disponibilidade_professores[prof] |= disp
        
        # Clear temporary allocations
        self.alocacoes_temporarias = {
            'global': {},
            'turmas': {},
            'disponibilidade': {}
        }
        
    def desfazer_alocacao_temporaria(self):
        """
        Desfaz todas as alocações temporárias
        """
        self.alocacoes_temporarias = {
            'global': {},
            'turmas': {},
            'disponibilidade': {}
        }
        self.tentativas_por_slot = {}

    def alocar_disciplina(self, turma, disciplina_row):
        """Aloca uma disciplina específica para uma turma
        
        :param turma: Nome da turma
        :param disciplina_row: Linha do DataFrame com informações da disciplina
        :return: True se alocação foi bem sucedida, False caso contrário
        """
        disciplina = disciplina_row['disciplina']
        carga_horaria = int(disciplina_row['total_aulas_disciplina'])
        aulas_alocadas = 0
        
        print(f"\n📚 Alocando {disciplina} para {turma} - CH: {carga_horaria}")
        
        # Tentar alocar em diferentes dias e horários
        for dia in self.dias:
            for posicao in range(7):
                if aulas_alocadas >= carga_horaria:
                    break
                    
                # Verificar se o slot está livre
                if (self.verificar_conflito_global(posicao) or 
                    self.grade_horarios_turmas[turma][dia][posicao] is not None):
                    continue
                
                # Selecionar professor disponível
                professores_disponiveis = self.professores_df[
                    (self.professores_df['disciplina'] == disciplina) &
                    (self.professores_df['turma'] == turma)
                ]['nome'].unique()
                
                professor_alocado = None
                for professor in professores_disponiveis:
                    if not self.professor_ja_alocado_no_dia(professor, posicao):
                        professor_alocado = professor
                        break
                
                if professor_alocado:
                    # Tentar alocação temporária
                    if self.tentar_alocacao_temporaria(professor_alocado, disciplina, turma, dia, posicao):
                        print(f"✅ Aula alocada: {disciplina} - {professor_alocado} - {dia} {posicao+1}ª aula")
                        aulas_alocadas += 1
                        self.confirmar_alocacao_temporaria()
                    else:
                        self.desfazer_alocacao_temporaria()
        
        # Verificar se todas as aulas foram alocadas
        if aulas_alocadas < carga_horaria:
            print(f"⚠️ Alocação incompleta: {disciplina} para {turma}")
            print(f"   Aulas previstas: {carga_horaria}")
            print(f"   Aulas alocadas: {aulas_alocadas}")
            
            self.alocacoes_incompletas.append({
                'turma': turma,
                'disciplina': disciplina,
                'aulas_previstas': carga_horaria,
                'aulas_alocadas': aulas_alocadas
            })
            return False
        
        return True

    def alocar_aulas_professor(self, professor, turmas):
        """Aloca todas as aulas de um professor nas suas turmas e disciplinas"""
        aulas_professor = self.professores_df[
            (self.professores_df['nome'] == professor) & 
            (self.professores_df['turma'].isin(turmas))
        ].copy()
        
        if aulas_professor.empty:
            print(f"⚠️ Nenhuma aula encontrada para o professor {professor}")
            return True
            
        print(f"🔍 Alocando aulas para professor {professor}")
        print(f"📚 Disciplinas/Turmas: {aulas_professor[['disciplina', 'turma']].values.tolist()}")
        
        # Para cada disciplina/turma do professor
        for _, aula in aulas_professor.iterrows():
            disciplina = aula['disciplina']
            turma = aula['turma']
            carga_horaria = int(aula['carga_horaria'])
            aulas_alocadas = 0
            
            print(f"\n📝 Alocando {disciplina} para turma {turma} - CH: {carga_horaria}")
            
            # Tentar alocar cada aula
            for dia in self.dias:
                for posicao in range(7):
                    if aulas_alocadas >= carga_horaria:
                        break
                        
                    # Verificar disponibilidade e restrições
                    if not self.verificar_disponibilidade_professor(professor, dia, posicao):
                        continue
                        
                    # Verificar se o slot já está ocupado na turma
                    if self.grade_horarios_turmas[turma][dia][posicao] is not None:
                        continue
                        
                    # Verificar se o professor já está alocado em outra turma no mesmo horário
                    if self.professor_ja_alocado_em_turmas(professor, posicao, turma):
                        continue
                        
                    # Verificar exceções específicas
                    if not self.verificar_excecoes_professor(professor, disciplina, turma, dia, posicao):
                        continue
                    
                    # Alocar aula
                    aula_obj = {
                        'disciplina': disciplina,
                        'professor': professor,
                        'turma': turma
                    }
                    
                    self.grade_horarios_global[dia][posicao] = aula_obj
                    self.grade_horarios_turmas[turma][dia][posicao] = aula_obj
                    self.disponibilidade_professores[professor][posicao] = True
                    
                    print(f"✅ Aula alocada: {dia} - Horário {posicao + 1}")
                    aulas_alocadas += 1
            
            # Se não conseguiu alocar todas as aulas
            if aulas_alocadas < carga_horaria:
                print(f"❌ Não foi possível alocar todas as aulas de {disciplina} para {turma}")
                print(f"   Aulas previstas: {carga_horaria}")
                print(f"   Aulas alocadas: {aulas_alocadas}")
                
                self.alocacoes_incompletas.append({
                    'professor': professor,
                    'turma': turma,
                    'disciplina': disciplina,
                    'aulas_previstas': carga_horaria,
                    'aulas_alocadas': aulas_alocadas
                })
                return False
        
        return True
    def salvar_resultados(self):
        """
        Salva os resultados da alocação de horários em um arquivo CSV
        """
        try:
            # Preparar lista para armazenar todas as aulas alocadas
            aulas_alocadas = []
        except Exception as e:
            print(f"❌ Erro ao salvar resultados: {e}")
            return False
            
    def alocar_aulas_eletiva(self, turmas):
        """
        Aloca aulas de Eletiva na segunda-feira, horários 4 e 5
        """
        try:
            print("🔍 INICIANDO ALOCAÇÃO DE AULAS ELETIVA")
            
            # Dia fixo: segunda-feira (SEG)
            dia_eletiva = 'seg'
            
            # Horários fixos: 4 e 5
            horarios_eletiva = [4, 5]
            
            for turma in turmas:
                for horario in horarios_eletiva:
                    # Verificar se já existe alocação
                    if (self.grade_horarios_turmas[turma][dia_eletiva][horario] is not None):
                        continue
                        
                    # Tentar alocar professor de Eletiva
                    professor = self.selecionar_professor_para_disciplina('Eletiva', turma, dia_eletiva, horario)
                    
                    if professor:
                        aula = {
                            'disciplina': 'Eletiva',
                            'professor': professor,
                            'turma': turma
                        }
                        
                        # Registrar alocação
                        self.grade_horarios_global[dia_eletiva][horario] = aula
                        self.grade_horarios_turmas[turma][dia_eletiva][horario] = aula
                        self.disponibilidade_professores[professor][horario] = True
                        
                        print(f"✅ AULA ELETIVA ALOCADA: {professor} - Turma {turma} - Horário {horario}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao alocar aulas eletivas: {e}")
            return False
        horarios_eletiva = [4, 5]
        
        # Processar cada turma
        for turma in turmas:
            # Verificar se a turma tem disciplina Eletiva
            disciplinas_turma = self.professores_df[
                self.professores_df['turma'] == turma
            ]['disciplina'].unique()
            
            if len(disciplinas_turma) == 0:
                print(f"❌ Turma {turma} não encontrada")
                continue
            
            if 'ELETIVA' not in disciplinas_turma:
                print(f"❌ Turma {turma} não possui Eletiva")
                continue
            
            # Encontrar professor de Eletiva para esta turma
            professor_eletiva_df = self.professores_df[
                (self.professores_df['turma'] == turma) &
                (self.professores_df['disciplina'] == 'ELETIVA')
            ]['nome']
            if professor_eletiva_df.empty:
                print(f"❌ Professor de Eletiva não encontrado para turma {turma}")
                continue
                
            professor_eletiva = professor_eletiva_df.iloc[0]
            if professor_eletiva_df.empty:
                print(f"❌ Professor de Eletiva não encontrado para turma {turma}")
                continue
            
            # Inicializar grade da turma se não existir
            if turma not in self.grade_horarios_turmas:
                self.grade_horarios_turmas[turma] = [None] * 35
            
            # Alocar aulas de Eletiva nos horários fixos
            for horario in horarios_eletiva:
                # Calcular posição no vetor de 35 posições
                posicao = self.dias.index(dia_eletiva) * 7 + (horario - 1)
                
                # Verificar disponibilidade do professor
                if not self.verificar_disponibilidade_professor(professor_eletiva, dia_eletiva, posicao):
                    print(f"❌ Professor {professor_eletiva} não disponível na posição {posicao}")
                    continue
                
                # Alocar aula de Eletiva
                grade_turma = self.grade_horarios_turmas[turma]
                grade_turma[posicao] = {
                    'professor': professor_eletiva,
                    'disciplina': 'ELETIVA',
                    'dia': dia_eletiva,
                    'eletiva': True
                }
                
                # Atualizar grade global e disponibilidade
                self.grade_horarios_global[dia_eletiva][posicao] = {
                    'professor': professor_eletiva,
                    'turma': turma,
                    'disciplina': 'ELETIVA'
                }
                
                self.disponibilidade_professores[professor_eletiva][posicao] = True
                
                print(f"✅ Alocada Eletiva para Turma {turma} no horário {horario}")
        
        return True

def executar_geracao_horario(data_path=None):
    """
    Método alternativo para execução da geração de horário
    
    :param data_path: Caminho opcional para a pasta de dados
    """
    print("🚀 INICIANDO EXECUÇÃO DO GERADOR DE HORÁRIOS")
    print("=" * 50)
    
    if data_path is None:
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
    
    print(f"📂 CAMINHO DOS DADOS: {data_path}")
    
    # Verificar se o arquivo CSV existe
    csv_path = os.path.join(data_path, 'professores_disciplinas_turmas.csv')
    if not os.path.exists(csv_path):
        print(f"❌ ERRO: Arquivo CSV não encontrado em {csv_path}")
        print("Por favor, verifique se o arquivo 'professores_disciplinas_turmas.csv' existe no diretório correto.")
        return None
    
    # Imprimir conteúdo do CSV para verificação
    print("\n📋 CONTEÚDO DO ARQUIVO CSV:")
    try:
        df_teste = pd.read_csv(csv_path)
        print(df_teste.head())
        print(f"\nTotal de registros: {len(df_teste)}")
        print(f"Colunas encontradas: {list(df_teste.columns)}")
    except Exception as e:
        print(f"❌ ERRO AO LER O ARQUIVO CSV: {e}")
        return None
    
    print("\n" + "=" * 50)
    
    logging.info("INICIANDO EXECUÇÃO ALTERNATIVA DE GERAÇÃO DE HORÁRIO")
    logging.info(f"CAMINHO DOS DADOS: {data_path}")
    
    try:
        # Inicializar gerador
        gerador = ScheduleGenerator(data_path)
        print("✅ GERADOR DE HORÁRIOS INICIALIZADO COM SUCESSO")
        
        # Gerar horário
        print("\n🕒 INICIANDO GERAÇÃO DE HORÁRIO...")
        logging.info("INICIANDO GERAÇÃO DE HORÁRIO")
        horario = gerador.gerar_horario()
        logging.info("GERAÇÃO DE HORÁRIO CONCLUÍDA")
        
        # Verificar resultados
        print("\n📊 RESULTADOS DA GERAÇÃO:")
        print(f"Total de turmas processadas: {len(horario)}")
        print(f"Alocações incompletas: {len(gerador.alocacoes_incompletas)}")
        
        logging.info(f"TOTAL DE TURMAS PROCESSADAS: {len(horario)}")
        logging.info(f"ALOCAÇÕES INCOMPLETAS: {len(gerador.alocacoes_incompletas)}")
        
        print("\n✨ HORÁRIO GERADO COM SUCESSO!")
        logging.info("PROGRAMA CONCLUÍDO COM SUCESSO")
        
        return horario
    
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO DURANTE A EXECUÇÃO: {e}")
        logging.error(f"ERRO DURANTE A EXECUÇÃO: {e}", exc_info=True)
        print("Detalhes do erro:")
        import traceback
        traceback.print_exc()
        raise
# Adicionar método main para execução direta
def main():
    executar_geracao_horario()

# Adicionar método para facilitar importação e execução
if __name__ == "__main__":
    main()

