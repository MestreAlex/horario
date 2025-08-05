import numpy as np
import pandas as pd
from typing import Dict, List, Any
from scheduler.config import FEATURE_ENGINEERING

class FeatureProcessor:
    def __init__(self):
        self.feature_config = FEATURE_ENGINEERING
        self.cached_features = {}
        
    def extract_features(self, horario: Dict[str, Any], turma: str = None) -> np.ndarray:
        """
        Extrai features de um horário completo ou de uma turma específica
        """
        features = []
        
        if turma:
            features.extend(self._extract_turma_features(horario, turma))
        else:
            # Extrair features globais
            features.extend(self._extract_global_features(horario))
            
            # Features por turma
            for turma in horario.keys():
                if turma != '_alocacoes_incompletas' and turma != '_sugestoes_melhoria':
                    features.extend(self._extract_turma_features(horario, turma))
        
        return np.array(features)
    
    def _extract_global_features(self, horario: Dict[str, Any]) -> List[float]:
        """Extrai características globais do horário"""
        features = []
        
        # Total de aulas alocadas
        total_aulas = 0
        # Total de janelas
        total_janelas = 0
        # Distribuição de professores
        prof_count = {}
        # Distribuição de disciplinas
        disc_count = {}
        
        for turma, dados in horario.items():
            if turma not in ['_alocacoes_incompletas', '_sugestoes_melhoria']:
                for dia, aulas in dados['dias'].items():
                    # Contar aulas e janelas
                    aulas_dia = 0
                    ultimo_horario = None
                    
                    for horario, aula in sorted(aulas.items()):
                        if aula:
                            total_aulas += 1
                            aulas_dia += 1
                            
                            # Contagem de professores e disciplinas
                            prof_count[aula['professor']] = prof_count.get(aula['professor'], 0) + 1
                            disc_count[aula['disciplina']] = disc_count.get(aula['disciplina'], 0) + 1
                            
                            # Verificar janelas
                            if ultimo_horario and int(horario) - int(ultimo_horario) > 1:
                                total_janelas += 1
                            
                            ultimo_horario = horario
        
        # Features de distribuição global
        features.extend([
            total_aulas,
            total_janelas,
            len(prof_count),  # Número de professores únicos
            len(disc_count),  # Número de disciplinas únicas
            np.std(list(prof_count.values())),  # Desvio padrão da carga dos professores
            np.std(list(disc_count.values()))   # Desvio padrão da distribuição de disciplinas
        ])
        
        return features
    
    def _extract_turma_features(self, horario: Dict[str, Any], turma: str) -> List[float]:
        """Extrai características específicas de uma turma"""
        features = []
        dados_turma = horario[turma]['dias']
        
        # Features temporais
        for dia in ['seg', 'ter', 'qua', 'qui', 'sex']:
            aulas_dia = dados_turma.get(dia, {})
            
            # Features do dia
            features.extend(self._extract_daily_features(aulas_dia))
            
            # Features de professores no dia
            features.extend(self._extract_teacher_features(aulas_dia))
            
            # Features de distribuição
            features.extend(self._extract_distribution_features(aulas_dia))
        
        return features
    
    def _extract_daily_features(self, aulas_dia: Dict[int, Dict]) -> List[float]:
        """Extrai características de um dia específico"""
        features = []
        
        # Total de aulas no dia
        total_aulas = len([a for a in aulas_dia.values() if a])
        
        # Distribuição ao longo do dia
        horarios = sorted([int(h) for h in aulas_dia.keys()])
        if horarios:
            primeiro_horario = min(horarios)
            ultimo_horario = max(horarios)
            janelas = sum(1 for h in range(primeiro_horario, ultimo_horario)
                         if h not in aulas_dia or not aulas_dia[h])
        else:
            janelas = 0
        
        features.extend([
            total_aulas,
            janelas,
            primeiro_horario if horarios else 0,
            ultimo_horario if horarios else 0
        ])
        
        return features
    
    def _extract_teacher_features(self, aulas_dia: Dict[int, Dict]) -> List[float]:
        """Extrai características relacionadas aos professores"""
        features = []
        
        # Contagem de aulas por professor
        prof_count = {}
        for aula in aulas_dia.values():
            if aula:
                prof = aula['professor']
                prof_count[prof] = prof_count.get(prof, 0) + 1
        
        # Features de distribuição de professores
        features.extend([
            len(prof_count),  # Número de professores diferentes
            max(prof_count.values()) if prof_count else 0,  # Máximo de aulas por professor
            np.mean(list(prof_count.values())) if prof_count else 0  # Média de aulas por professor
        ])
        
        return features
    
    def _extract_distribution_features(self, aulas_dia: Dict[int, Dict]) -> List[float]:
        """Extrai características da distribuição de aulas"""
        features = []
        
        # Aulas seguidas da mesma disciplina
        max_seguidas = 0
        curr_seguidas = 0
        ultima_disc = None
        
        for horario in sorted(aulas_dia.keys()):
            aula = aulas_dia[horario]
            if aula:
                if ultima_disc == aula['disciplina']:
                    curr_seguidas += 1
                    max_seguidas = max(max_seguidas, curr_seguidas)
                else:
                    curr_seguidas = 1
                ultima_disc = aula['disciplina']
            else:
                curr_seguidas = 0
                ultima_disc = None
        
        features.extend([
            max_seguidas,
            len(set(a['disciplina'] for a in aulas_dia.values() if a))  # Disciplinas únicas
        ])
        
        return features