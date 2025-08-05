import pandas as pd
import logging
from typing import Dict, List, Any, Optional
import os

class HorarioValidator:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        
        # Carregar dados necessários
        self.professores_df = pd.read_csv(os.path.join(data_path, 'professores.csv'))
        self.disciplinas_df = pd.read_csv(os.path.join(data_path, 'disciplinas.csv'))
        self.excecoes_df = pd.read_csv(os.path.join(data_path, 'excecoes.csv'))
        
        # Cache de validações para otimização
        self.cache_validacoes = {}
        
    def validar_alocacao(self, professor: str, disciplina: str, turma: str, 
                        dia: str, horario: int) -> Dict[str, Any]:
        """
        Valida uma alocação específica de professor/disciplina/horário
        """
        # Criar chave de cache
        cache_key = f"{professor}-{disciplina}-{turma}-{dia}-{horario}"
        if cache_key in self.cache_validacoes:
            return self.cache_validacoes[cache_key]
            
        resultado = {
            'valido': True,
            'conflitos': [],
            'avisos': []
        }
        
        # 1. Validar professor x disciplina
        if not self._validar_professor_disciplina(professor, disciplina):
            resultado['valido'] = False
            resultado['conflitos'].append(
                f"Professor {professor} não está habilitado para disciplina {disciplina}"
            )
            
        # 2. Validar disponibilidade de horário
        if not self._validar_disponibilidade(professor, dia, horario):
            resultado['valido'] = False
            resultado['conflitos'].append(
                f"Professor {professor} não está disponível {dia} no horário {horario}"
            )
            
        # 3. Validar restrições
        restricoes = self._validar_restricoes(professor, disciplina, turma, dia, horario)
        if not restricoes['valido']:
            resultado['valido'] = False
            resultado['conflitos'].extend(restricoes['conflitos'])
            
        # 4. Validar exceções
        excecoes = self._validar_excecoes(professor, disciplina, turma, dia, horario)
        if not excecoes['valido']:
            resultado['valido'] = False
            resultado['conflitos'].extend(excecoes['conflitos'])
            
        # 5. Validar carga horária
        carga_horaria = self._validar_carga_horaria(professor, dia)
        if not carga_horaria['valido']:
            resultado['avisos'].extend(carga_horaria['avisos'])
            
        # Armazenar no cache
        self.cache_validacoes[cache_key] = resultado
        return resultado
        
    def _validar_professor_disciplina(self, professor: str, disciplina: str) -> bool:
        """Verifica se o professor pode lecionar a disciplina"""
        return any(
            (self.professores_df['nome'] == professor) & 
            (self.professores_df['disciplina'] == disciplina)
        )
        
    def _validar_disponibilidade(self, professor: str, dia: str, horario: int) -> bool:
        """Verifica disponibilidade do professor no horário"""
        disponibilidade = self.professores_df[
            self.professores_df['nome'] == professor
        ][f'd_{dia}'].iloc[0]
        
        if pd.isna(disponibilidade):
            return False
            
        horas_disponiveis = str(disponibilidade).split(',')
        return str(horario) in horas_disponiveis
        
    def _validar_restricoes(self, professor: str, disciplina: str, 
                          turma: str, dia: str, horario: int) -> Dict[str, Any]:
        """Valida restrições de horário para disciplina"""
        resultado = {
            'valido': True,
            'conflitos': []
        }
        
        restricao = self.disciplinas_df[
            self.disciplinas_df['disciplina'] == disciplina
        ][f'r_{dia}'].iloc[0]
        
        if not pd.isna(restricao):
            horarios_restricao = str(restricao).split(',')
            if str(horario) in horarios_restricao:
                resultado['valido'] = False
                resultado['conflitos'].append(
                    f"Horário {horario} restrito para disciplina {disciplina} em {dia}"
                )
                
        return resultado
        
    def _validar_excecoes(self, professor: str, disciplina: str,
                         turma: str, dia: str, horario: int) -> Dict[str, Any]:
        """Valida exceções específicas"""
        resultado = {
            'valido': True,
            'conflitos': []
        }
        
        # Filtrar exceções relevantes
        excecoes = self.excecoes_df[
            (self.excecoes_df['professor'] == professor) |
            (self.excecoes_df['disciplina'] == disciplina) |
            (self.excecoes_df['turma'] == turma)
        ]
        
        for _, excecao in excecoes.iterrows():
            # Verificar dias
            dias_excecao = str(excecao['dias']).split(',')
            if dia in dias_excecao:
                # Verificar horários
                horas_excecao = str(excecao['horas']).split(',')
                if str(horario) in horas_excecao:
                    if excecao['tipo'] == 'NÃO':
                        resultado['valido'] = False
                        resultado['conflitos'].append(
                            f"Exceção encontrada: {excecao['descricao'] if 'descricao' in excecao else 'Sem descrição'}"
                        )
                        
        return resultado
        
    def _validar_carga_horaria(self, professor: str, dia: str) -> Dict[str, Any]:
        """Valida carga horária diária do professor"""
        resultado = {
            'valido': True,
            'avisos': []
        }
        
        # Contar aulas no dia
        aulas_dia = len(str(self.professores_df[
            self.professores_df['nome'] == professor
        ][f'd_{dia}'].iloc[0]).split(','))
        
        if aulas_dia > 4:
            resultado['avisos'].append(
                f"Professor {professor} tem {aulas_dia} aulas em {dia} (máx. recomendado: 4)"
            )
            
        return resultado
        
    def limpar_cache(self):
        """Limpa o cache de validações"""
        self.cache_validacoes = {}