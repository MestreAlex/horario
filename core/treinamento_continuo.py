import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import json
import os
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

class TreinamentoContinuo:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        self.historico_path = os.path.join(data_path, 'historico_treinamento.json')
        
        # Métricas de aprendizado
        self.metricas = {
            'total_exemplos': 0,
            'exemplos_bem_sucedidos': 0,
            'melhoria_percentual': 0,
            'evolucao_scores': [],
            'distribuicao_conflitos': {},
            'tempo_medio_geracao': 0
        }
        
        # Carregar histórico existente
        self._carregar_historico()
        
    def _carregar_historico(self):
        """Carrega histórico de treinamento"""
        if os.path.exists(self.historico_path):
            try:
                with open(self.historico_path, 'r') as f:
                    historico = json.load(f)
                    self.metricas.update(historico)
            except Exception as e:
                self.logger.error(f"Erro ao carregar histórico: {e}")
    
    def registrar_geracao(self, horario: Dict[str, Any], metricas: Dict[str, Any], tempo_geracao: float):
        """Registra uma nova geração de horário para análise"""
        try:
            # Atualizar métricas
            self.metricas['total_exemplos'] += 1
            
            # Avaliar sucesso da geração
            sucesso = self._avaliar_sucesso_geracao(horario, metricas)
            if sucesso:
                self.metricas['exemplos_bem_sucedidos'] += 1
            
            # Atualizar média de tempo
            self.metricas['tempo_medio_geracao'] = (
                (self.metricas['tempo_medio_geracao'] * (self.metricas['total_exemplos'] - 1) +
                 tempo_geracao) / self.metricas['total_exemplos']
            )
            
            # Registrar score
            score = self._calcular_score_geracao(horario, metricas)
            self.metricas['evolucao_scores'].append({
                'timestamp': datetime.now().isoformat(),
                'score': score,
                'sucesso': sucesso
            })
            
            # Registrar distribuição de conflitos
            self._atualizar_distribuicao_conflitos(metricas)
            
            # Calcular melhoria percentual
            if len(self.metricas['evolucao_scores']) >= 2:
                scores = [s['score'] for s in self.metricas['evolucao_scores'][-10:]]
                if len(scores) >= 2:
                    self.metricas['melhoria_percentual'] = (
                        (scores[-1] - scores[0]) / scores[0] * 100
                    )
            
            # Salvar histórico atualizado
            self._salvar_historico()
            
        except Exception as e:
            self.logger.error(f"Erro ao registrar geração: {e}")
    
    def _avaliar_sucesso_geracao(self, horario: Dict[str, Any], metricas: Dict[str, Any]) -> bool:
        """Avalia se uma geração foi bem sucedida"""
        # Verificar alocações incompletas
        if '_alocacoes_incompletas' in horario and horario['_alocacoes_incompletas']:
            return False
            
        # Verificar conflitos graves
        if metricas.get('total_conflitos', 0) > 0:
            return False
            
        # Verificar janelas excessivas
        if metricas.get('total_janelas', 0) > metricas.get('total_aulas_alocadas', 0) * 0.2:
            return False
            
        return True
    
    def _calcular_score_geracao(self, horario: Dict[str, Any], metricas: Dict[str, Any]) -> float:
        """Calcula score de qualidade da geração"""
        score = 100.0  # Score inicial
        
        # Penalidades por conflitos
        score -= metricas.get('total_conflitos', 0) * 10
        
        # Penalidades por janelas
        score -= metricas.get('total_janelas', 0) * 5
        
        # Bônus por aulas alocadas
        score += metricas.get('total_aulas_alocadas', 0)
        
        # Bônus por aderência a preferências
        if 'preferencias_atendidas' in metricas:
            score += metricas['preferencias_atendidas'] * 2
            
        return max(0, score)
    
    def _atualizar_distribuicao_conflitos(self, metricas: Dict[str, Any]):
        """Atualiza estatísticas de distribuição de conflitos"""
        if 'conflitos_por_tipo' in metricas:
            for tipo, quantidade in metricas['conflitos_por_tipo'].items():
                if tipo not in self.metricas['distribuicao_conflitos']:
                    self.metricas['distribuicao_conflitos'][tipo] = 0
                self.metricas['distribuicao_conflitos'][tipo] += quantidade
    
    def _salvar_historico(self):
        """Salva histórico de treinamento atualizado"""
        try:
            # Limitar tamanho do histórico
            if len(self.metricas['evolucao_scores']) > 100:
                self.metricas['evolucao_scores'] = self.metricas['evolucao_scores'][-100:]
            
            with open(self.historico_path, 'w') as f:
                json.dump(self.metricas, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar histórico: {e}")
    
    def gerar_relatorio_aprendizado(self) -> Dict[str, Any]:
        """Gera relatório sobre o aprendizado do sistema"""
        return {
            'total_geracoes': self.metricas['total_exemplos'],
            'taxa_sucesso': (self.metricas['exemplos_bem_sucedidos'] / 
                           self.metricas['total_exemplos'] * 100 
                           if self.metricas['total_exemplos'] > 0 else 0),
            'melhoria_recente': self.metricas['melhoria_percentual'],
            'tempo_medio_geracao': self.metricas['tempo_medio_geracao'],
            'distribuicao_conflitos': self.metricas['distribuicao_conflitos'],
            'ultimos_scores': [s['score'] for s in self.metricas['evolucao_scores'][-10:]]
        }
    
    def analisar_tendencias(self) -> List[str]:
        """Analisa tendências nos dados históricos"""
        tendencias = []
        
        if len(self.metricas['evolucao_scores']) >= 10:
            scores_recentes = [s['score'] for s in self.metricas['evolucao_scores'][-10:]]
            media_atual = np.mean(scores_recentes[-3:])
            media_anterior = np.mean(scores_recentes[:-3])
            
            if media_atual > media_anterior * 1.1:
                tendencias.append("Melhoria significativa na qualidade dos horários")
            elif media_atual < media_anterior * 0.9:
                tendencias.append("Queda na qualidade dos horários")
            
            # Analisar tipos de conflitos
            if self.metricas['distribuicao_conflitos']:
                conflito_mais_comum = max(
                    self.metricas['distribuicao_conflitos'].items(),
                    key=lambda x: x[1]
                )[0]
                tendencias.append(f"Conflito mais frequente: {conflito_mais_comum}")
        
        return tendencias