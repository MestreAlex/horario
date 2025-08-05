import logging
import os
import json
from datetime import datetime
from typing import Dict, Any

class HorarioLogger:
    def __init__(self, log_dir: str = 'logs'):
        """
        Inicializa o sistema de logs
        
        :param log_dir: Diretório onde os logs serão salvos
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Configurar logger principal
        self.logger = logging.getLogger('horario_generator')
        self.logger.setLevel(logging.INFO)
        
        # Handler para arquivo
        log_file = os.path.join(log_dir, f'horario_generator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatador
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Adicionar handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Métricas de geração
        self.metricas = {
            'inicio_geracao': None,
            'fim_geracao': None,
            'total_aulas_alocadas': 0,
            'total_conflitos': 0,
            'total_janelas': 0,
            'alocacoes_por_turma': {},
            'conflitos_por_professor': {},
            'avisos': []
        }
    
    def iniciar_geracao(self):
        """Registra início da geração de horários"""
        self.metricas['inicio_geracao'] = datetime.now()
        self.logger.info('🚀 Iniciando a geração de horários...')
    
    def finalizar_geracao(self):
        """Registra fim da geração de horários"""
        self.metricas['fim_geracao'] = datetime.now()
        tempo_total = self.metricas['fim_geracao'] - self.metricas['inicio_geracao']
        
        self.logger.info(f'✅ Geração finalizada! Tempo total: {tempo_total.total_seconds():.2f} segundos')
        self.logger.info(f'📊 Resumo da geração:')
        self.logger.info(f'   • Total de aulas alocadas: {self.metricas["total_aulas_alocadas"]}')
        self.logger.info(f'   • Total de conflitos: {self.metricas["total_conflitos"]}')
        self.logger.info(f'   • Total de janelas: {self.metricas["total_janelas"]}')
    
    def registrar_alocacao(self, turma: str, disciplina: str, professor: str, 
                          dia: str, horario: int, resultado_validacao: Dict[str, Any]):
        """
        Registra uma alocação de aula
        """
        # Atualizar métricas
        self.metricas['total_aulas_alocadas'] += 1
        
        if turma not in self.metricas['alocacoes_por_turma']:
            self.metricas['alocacoes_por_turma'][turma] = 0
        self.metricas['alocacoes_por_turma'][turma] += 1
        
        # Registrar conflitos se houver
        if not resultado_validacao['valido']:
            self.metricas['total_conflitos'] += len(resultado_validacao['conflitos'])
            
            if professor not in self.metricas['conflitos_por_professor']:
                self.metricas['conflitos_por_professor'][professor] = []
            
            self.metricas['conflitos_por_professor'][professor].extend(
                resultado_validacao['conflitos']
            )
            
            # Log detalhado de conflitos
            for conflito in resultado_validacao['conflitos']:
                self.logger.warning(
                    f'⚠️ Conflito detectado:\n'
                    f'   • Turma: {turma}\n'
                    f'   • Disciplina: {disciplina}\n'
                    f'   • Professor: {professor}\n'
                    f'   • Horário: {dia}, {horario}ª aula\n'
                    f'   • Motivo: {conflito}'
                )
        
        # Registrar avisos se houver
        if resultado_validacao.get('avisos'):
            self.metricas['avisos'].extend(resultado_validacao['avisos'])
            for aviso in resultado_validacao['avisos']:
                self.logger.info(
                    f'Aviso em {turma} - {disciplina} com {professor} '
                    f'({dia} {horario}ª aula): {aviso}'
                )
    
    def registrar_janela(self, professor: str, dia: str, horario: int):
        """Registra uma janela no horário"""
        self.metricas['total_janelas'] += 1
        self.logger.info(f'ℹ️ Janela detectada:\n   • Professor: {professor}\n   • Horário: {dia}, {horario}ª aula')
    
    def gerar_relatorio(self) -> Dict[str, Any]:
        """
        Gera relatório completo da geração de horários
        
        :return: Dicionário com todas as métricas e estatísticas
        """
        if not self.metricas['fim_geracao']:
            self.finalizar_geracao()
        
        tempo_total = self.metricas['fim_geracao'] - self.metricas['inicio_geracao']
        
        return {
            'tempo_execucao_segundos': tempo_total.total_seconds(),
            'total_aulas_alocadas': self.metricas['total_aulas_alocadas'],
            'total_conflitos': self.metricas['total_conflitos'],
            'total_janelas': self.metricas['total_janelas'],
            'media_aulas_por_turma': sum(self.metricas['alocacoes_por_turma'].values()) / 
                                   len(self.metricas['alocacoes_por_turma']) 
                                   if self.metricas['alocacoes_por_turma'] else 0,
            'alocacoes_por_turma': self.metricas['alocacoes_por_turma'],
            'conflitos_por_professor': self.metricas['conflitos_por_professor'],
            'avisos': self.metricas['avisos']
        }
    
    def salvar_relatorio(self, caminho: str = None):
        """
        Salva o relatório em arquivo JSON
        
        :param caminho: Caminho onde salvar o arquivo. Se None, usa o diretório de logs
        """
        if not caminho:
            caminho = os.path.join(
                self.log_dir, 
                f'relatorio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
        
        relatorio = self.gerar_relatorio()
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=4, ensure_ascii=False)
        
        self.logger.info(f'📄 Relatório salvo com sucesso em {caminho}')