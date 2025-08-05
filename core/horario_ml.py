from scheduler.core.feature_processor import FeatureProcessor
from ..config import ML_CONFIG, ML_METRICS
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
import logging
from datetime import datetime
from typing import Dict, List, Any
from .treinamento_continuo import TreinamentoContinuo
import json

class HorarioML:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        self.modelo_path = os.path.join(data_path, 'modelo_horario.joblib')
        self.historico_path = os.path.join(data_path, 'historico_horarios.json')
        
        # Inicializar processador de features
        self.feature_processor = FeatureProcessor()
        
        # Inicializar modelo com configurações
        self.modelo = RandomForestRegressor(**ML_CONFIG['model_params'])
        
        # Cache para otimização
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Carregar modelo existente
        self._carregar_modelo()
        
        # Métricas de desempenho
        self.metricas = {
            'total_predicoes': 0,
            'melhor_score': 0,
            'scores_recentes': [],
            'tempo_medio_predicao': 0
        }
        
        # Inicializar sistema de treinamento contínuo
        self.treinamento = TreinamentoContinuo(data_path)
    
    def _carregar_modelo(self):
        """Carrega o modelo de ML a partir do arquivo"""
        modelo_path = os.path.join(self.data_path, 'modelo_horario.joblib')
        if os.path.exists(modelo_path):
            self.modelo = joblib.load(modelo_path)
        else:
            self.modelo = RandomForestRegressor()

    def treinar_modelo(self):
        """Treina o modelo de ML e salva no arquivo"""
        # Implementação do treinamento do modelo
        # ...
        modelo_path = os.path.join(self.data_path, 'modelo_horario.joblib')
        joblib.dump(self.modelo, modelo_path)

    def prever_score(self, horario: Dict[str, Any]) -> float:
        """Prevê o score de um horário usando o modelo treinado"""
        inicio = datetime.now()
        
        try:
            # Verificar cache
            horario_key = self._gerar_cache_key(horario)
            if ML_CONFIG['cache']['enabled'] and horario_key in self.cache:
                self.cache_hits += 1
                return self.cache[horario_key]
            
            # Extrair features
            features = self.feature_processor.extract_features(horario)
            
            # Fazer previsão
            score = float(self.modelo.predict(features.reshape(1, -1))[0])
            
            # Atualizar métricas
            self.metricas['total_predicoes'] += 1
            self.metricas['melhor_score'] = max(self.metricas['melhor_score'], score)
            self.metricas['scores_recentes'] = (self.metricas['scores_recentes'][-9:] + [score])
            
            # Atualizar tempo médio
            tempo_predicao = (datetime.now() - inicio).total_seconds()
            self.metricas['tempo_medio_predicao'] = (
                (self.metricas['tempo_medio_predicao'] * (self.metricas['total_predicoes'] - 1) +
                 tempo_predicao) / self.metricas['total_predicoes']
            )
            
            # Armazenar em cache
            if ML_CONFIG['cache']['enabled']:
                self.cache[horario_key] = score
                self.cache_misses += 1
                self._limpar_cache_se_necessario()
            
            # Registrar geração para análise de tendências
            self.treinamento.registrar_geracao(
                horario=horario,
                metricas=self.metricas,
                tempo_geracao=(datetime.now() - inicio).total_seconds()
            )
            
            return score
            
        except Exception as e:
            self.logger.error(f"Erro ao prever score: {e}")
            return self._calcular_score_fallback(horario)
            
    def obter_relatorio_aprendizado(self) -> Dict[str, Any]:
        """Retorna relatório completo sobre o aprendizado do sistema"""
        relatorio = self.treinamento.gerar_relatorio_aprendizado()
        
        # Adicionar métricas do modelo
        relatorio.update({
            'cache_efficiency': {
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'ratio': self.cache_hits / (self.cache_hits + self.cache_misses) 
                         if (self.cache_hits + self.cache_misses) > 0 else 0
            },
            'model_metrics': {
                'total_predicoes': self.metricas['total_predicoes'],
                'melhor_score': self.metricas['melhor_score'],
                'tempo_medio_predicao': self.metricas['tempo_medio_predicao']
            }
        })
        
        return relatorio
        
    def analisar_tendencias(self) -> List[Dict[str, Any]]:
        """Analisa tendências e sugere melhorias"""
        tendencias = self.treinamento.analisar_tendencias()
        sugestoes = []
        
        for tendencia in tendencias:
            if "Queda na qualidade" in tendencia:
                sugestoes.append({
                    "tipo": "alerta",
                    "mensagem": tendencia,
                    "acao_sugerida": "Considerar retreinamento do modelo"
                })
            elif "Conflito mais frequente" in tendencia:
                sugestoes.append({
                    "tipo": "sugestao",
                    "mensagem": tendencia,
                    "acao_sugerida": "Revisar regras de alocação para este tipo de conflito"
                })
            else:
                sugestoes.append({
                    "tipo": "info",
                    "mensagem": tendencia
                })
        
        return sugestoes
        
    def registrar_horario(self, horario: Dict[str, Any], score: float):
        """Registra um horário para treinamento futuro"""
        try:
            # Extrair features
            features = self.feature_processor.extract_features(horario)
            
            # Preparar dados para salvar
            registro = {
                'timestamp': datetime.now().isoformat(),
                'features': features.tolist(),
                'score': float(score),
                'metricas': {
                    k: float(v) if isinstance(v, (int, float)) else v
                    for k, v in self._calcular_metricas_qualidade(horario).items()
                }
            }
            
            # Carregar histórico existente
            historico = []
            if os.path.exists(self.historico_path):
                with open(self.historico_path, 'r') as f:
                    historico = json.load(f)
            
            # Adicionar novo registro
            historico.append(registro)
            
            # Salvar histórico atualizado
            with open(self.historico_path, 'w') as f:
                json.dump(historico, f, indent=2)
            
            # Verificar se precisa retreinar
            if len(historico) % ML_CONFIG['training']['retrain_threshold'] == 0:
                self.treinar_modelo()
                
            # Registrar para análise de tendências
            self.treinamento.registrar_geracao(
                horario=horario,
                metricas=registro['metricas'],
                tempo_geracao=0  # Não temos o tempo de geração aqui
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao registrar horário: {e}")
    
    def _calcular_metricas_qualidade(self, horario: Dict[str, Any]) -> Dict[str, float]:
        """Calcula métricas de qualidade do horário"""
        metricas = {}
        
        # Balanced Workload
        cargas = self._calcular_cargas_professores(horario)
        metricas['balanced_workload'] = 1 - np.std(list(cargas.values()))
        
        # Teacher Satisfaction (baseado em preferências atendidas)
        metricas['teacher_satisfaction'] = self._calcular_satisfacao_professores(horario)
        
        # Schedule Compactness
        metricas['schedule_compactness'] = self._calcular_compactacao(horario)
        
        # Preference Adherence
        metricas['preference_adherence'] = self._calcular_aderencia_preferencias(horario)
        
        # Adicionar métricas de conflitos
        conflitos = self._analisar_conflitos(horario)
        metricas['conflitos_por_tipo'] = conflitos
        
        return metricas
    
    def _calcular_cargas_professores(self, horario: Dict[str, Any]) -> Dict[str, int]:
        """Calcula carga horária por professor"""
        cargas = {}
        
        for turma, dados in horario.items():
            if turma not in ['_alocacoes_incompletas', '_sugestoes_melhoria']:
                for dia, aulas in dados['dias'].items():
                    for aula in aulas.values():
                        if aula:
                            prof = aula['professor']
                            cargas[prof] = cargas.get(prof, 0) + 1
        
        return cargas
    
    def _calcular_satisfacao_professores(self, horario: Dict[str, Any]) -> float:
        """Calcula índice de satisfação dos professores"""
        total_aulas = 0
        aulas_preferidas = 0
        
        for turma, dados in horario.items():
            if turma not in ['_alocacoes_incompletas', '_sugestoes_melhoria']:
                for dia, aulas in dados['dias'].items():
                    for horario_aula, aula in aulas.items():
                        if aula:
                            total_aulas += 1
                            if self._verificar_preferencia_professor(
                                aula['professor'], dia, horario_aula
                            ):
                                aulas_preferidas += 1
        
        return aulas_preferidas / total_aulas if total_aulas > 0 else 0
    
    def _calcular_compactacao(self, horario: Dict[str, Any]) -> float:
        """Calcula índice de compactação do horário"""
        total_janelas = 0
        total_dias = 0
        
        for turma, dados in horario.items():
            if turma not in ['_alocacoes_incompletas', '_sugestoes_melhoria']:
                for dia, aulas in dados['dias'].items():
                    if aulas:
                        total_dias += 1
                        horarios = sorted([int(h) for h in aulas.keys()])
                        for i in range(len(horarios)-1):
                            if horarios[i+1] - horarios[i] > 1:
                                total_janelas += 1
        
        return 1 - (total_janelas / (total_dias * 2)) if total_dias > 0 else 0
    
    def _calcular_aderencia_preferencias(self, horario: Dict[str, Any]) -> float:
        """Calcula aderência às preferências gerais"""
        total_restricoes = 0
        restricoes_atendidas = 0
        
        for turma, dados in horario.items():
            if turma not in ['_alocacoes_incompletas', '_sugestoes_melhoria']:
                for dia, aulas in dados['dias'].items():
                    for horario_aula, aula in aulas.items():
                        if aula:
                            total_restricoes += 1
                            if self._verificar_restricoes(
                                aula['disciplina'], dia, horario_aula
                            ):
                                restricoes_atendidas += 1
        
        return restricoes_atendidas / total_restricoes if total_restricoes > 0 else 0
    
    def _verificar_preferencia_professor(self, professor: str, dia: str, horario: str) -> bool:
        """Verifica se um horário está nas preferências do professor"""
        try:
            df_professores = pd.read_csv(os.path.join(self.data_path, 'professores.csv'))
            prof_row = df_professores[df_professores['nome'] == professor]
            
            if not prof_row.empty:
                disponibilidade = str(prof_row[f'd_{dia}'].iloc[0])
                return str(horario) in disponibilidade.split(',')
            
            return False
        except Exception as e:
            self.logger.error(f"Erro ao verificar preferência: {e}")
            return False
    
    def _verificar_restricoes(self, disciplina: str, dia: str, horario: str) -> bool:
        """Verifica se um horário respeita as restrições da disciplina"""
        try:
            df_disciplinas = pd.read_csv(os.path.join(self.data_path, 'disciplinas.csv'))
            disc_row = df_disciplinas[df_disciplinas['disciplina'] == disciplina]
            
            if not disc_row.empty:
                restricoes = str(disc_row[f'r_{dia}'].iloc[0])
                return str(horario) not in restricoes.split(',')
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao verificar restrições: {e}")
            return True
    
    def _analisar_conflitos(self, horario: Dict[str, Any]) -> Dict[str, int]:
        """Analisa e categoriza conflitos no horário"""
        conflitos = {
            'sobreposicao_professor': 0,
            'janela_excessiva': 0,
            'restricao_violada': 0,
            'carga_horaria_excedida': 0
        }
        
        for turma, dados in horario.items():
            if turma not in ['_alocacoes_incompletas', '_sugestoes_melhoria']:
                for dia, aulas in dados['dias'].items():
                    # Verificar sobreposições
                    professores_horario = {}
                    for horario, aula in aulas.items():
                        if aula:
                            prof = aula['professor']
                            if prof in professores_horario.get(horario, []):
                                conflitos['sobreposicao_professor'] += 1
                            professores_horario[horario] = professores_horario.get(horario, []) + [prof]
                    
                    # Verificar janelas
                    horarios = sorted([int(h) for h in aulas.keys()])
                    for i in range(len(horarios)-1):
                        if horarios[i+1] - horarios[i] > 1:
                            conflitos['janela_excessiva'] += 1
                    
                    # Verificar restrições
                    for horario, aula in aulas.items():
                        if aula:
                            if not self._verificar_restricoes(aula['disciplina'], dia, horario):
                                conflitos['restricao_violada'] += 1
                    
                    # Verificar carga horária
                    cargas = self._calcular_cargas_professores(horario)
                    for prof, carga in cargas.items():
                        if carga > 4:  # Máximo de 4 aulas por dia
                            conflitos['carga_horaria_excedida'] += 1
        
        return conflitos