import datetime
import sys
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Iniciando aplicação...")

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, base_path)

def converter_tipos(obj):
    """
    Converte tipos não serializáveis para tipos nativos do Python
    """
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'tolist'):  # Adicionar tratamento genérico para outros tipos com método tolist
        return obj.tolist()
    return obj

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template, Response
import time
import pandas as pd
import numpy as np
import json
import queue
import threading

# Adicionar o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schedule_generator import ScheduleGenerator
from config import DB_CONFIG

# Importar Flask-CORS
from flask_cors import CORS

from scheduler.core.genetic_scheduler import otimizar_horario_genetico
from scheduler.core.horario_ml import HorarioML

app = Flask(__name__, 
    template_folder='../frontend',
    static_folder='../frontend/static'
)

# Adicionar CORS ao app
CORS(app)

# Fila global para progresso de alocações
progresso_queue = queue.Queue()

# Variável global para armazenar o último progresso
_ultimo_progresso = 0

# Definir caminho para pasta de dados
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    'scheduler', 'data'
)

def gerar_evento_progresso():
    """
    Gera eventos de progresso para o frontend
    """
    while True:
        try:
            # Aguardar novo progresso
            progresso = progresso_queue.get(timeout=30)
            yield f"data: {progresso}\n\n"
        except queue.Empty:
            # Manter conexão ativa com comentário
            yield ":\n\n"

@app.route("/")
def index():
    return render_template("index.html")

def converter_ndarray(obj):
    """
    Converte objetos ndarray para listas recursivamente
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: converter_ndarray(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [converter_ndarray(i) for i in obj]
    return obj

@app.route("/api/horarios/<turno>")
def gerar_horario(turno):
    try:
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data')
        gerador = ScheduleGenerator(data_path)
        horario = gerador.gerar_horario(turno)
        
        # Converter objetos ndarray para listas
        horario_serializable = converter_ndarray(horario)
        
        return jsonify({
            'horario': horario_serializable,
            'alocacoes_incompletas': gerador.alocacoes_incompletas
        })
    except Exception as e:
        logger.error(f"❌ Erro na geração de horário: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/professores")
def obter_professores():
    try:
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV
        csv_path = os.path.join(data_path, 'professores.csv')
        
        # Verificar se o arquivo existe
        if not os.path.exists(csv_path):
            return jsonify({
                "error": f"Arquivo CSV não encontrado: {csv_path}",
                "path": csv_path
            }), 404
        
        # Ler o arquivo CSV
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Tentar outros encodings
            encodings = ['latin1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding)
                    break
                except Exception as e:
                    logger.error(f"Erro ao ler com encoding {encoding}: {e}")
            else:
                raise ValueError("Não foi possível ler o arquivo com nenhum encoding")
        
        # Verificar colunas obrigatórias
        colunas_obrigatorias = ['nome', 'd_seg', 'd_ter', 'd_qua', 'd_qui', 'd_sex']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltantes:
            return jsonify({
                "error": f"Colunas faltantes no CSV: {colunas_faltantes}",
                "colunas_existentes": list(df.columns)
            }), 400
        
        # Tratar valores nulos ou vazios
        for coluna in ['d_seg', 'd_ter', 'd_qua', 'd_qui', 'd_sex']:
            df[coluna] = df[coluna].fillna('').astype(str)
        
        # Converter para lista de dicionários
        professores = df.to_dict('records')
        
        # Remover duplicatas baseado no nome do professor
        professores_unicos = []
        nomes_vistos = set()
        
        for professor in professores:
            nome = professor['nome']
            if nome not in nomes_vistos:
                professores_unicos.append(professor)
                nomes_vistos.add(nome)
        
        # Ordenar alfabeticamente
        professores_unicos.sort(key=lambda x: x['nome'])
        
        return jsonify(professores_unicos), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de professores: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/api/disciplinas")
def obter_disciplinas():
    try:
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV
        csv_path = os.path.join(data_path, 'disciplinas.csv')
        
        # Ler o arquivo CSV
        df = pd.read_csv(csv_path)
        
        # Substituir NaN por string vazia
        colunas_restricao = ['r_seg', 'r_ter', 'r_qua', 'r_qui', 'r_sex']
        for coluna in colunas_restricao:
            df[coluna] = df[coluna].fillna('').astype(str)
        
        # Converter para lista de dicionários
        disciplinas = df.to_dict('records')
        
        # Remover duplicatas baseado no nome da disciplina
        disciplinas_unicas = []
        disciplinas_vistas = set()
        
        for disciplina in disciplinas:
            nome = disciplina['disciplina']
            if nome not in disciplinas_vistas:
                disciplinas_unicas.append(disciplina)
                disciplinas_vistas.add(nome)
        
        # Ordenar alfabeticamente
        disciplinas_unicas.sort(key=lambda x: x['disciplina'])
        
        # Garantir que todos os valores sejam strings
        for disciplina in disciplinas_unicas:
            for coluna in colunas_restricao:
                disciplina[coluna] = str(disciplina[coluna]) if disciplina[coluna] is not None else ''
        
        return jsonify(disciplinas_unicas), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de disciplinas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route("/api/salvar_disponibilidades", methods=['POST'])
def salvar_disponibilidades():
    try:
        # Receber dados de disponibilidades
        dados_disponibilidades = request.json
        
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV de professores
        csv_path = os.path.join(data_path, 'professores.csv')
        
        # Ler o CSV atual
        df = pd.read_csv(csv_path)
        
        # Contador de professores atualizados
        total_atualizados = 0
        
        # Atualizar disponibilidades
        for professor, disponibilidades in dados_disponibilidades.items():
            # Filtrar linhas do professor
            mask = df['nome'] == professor
            
            # Atualizar colunas de disponibilidade
            for dia in ['d_seg', 'd_ter', 'd_qua', 'd_qui', 'd_sex']:
                # Converter para string vazia se não houver disponibilidade
                valor_dia = disponibilidades.get(dia, '')
                
                # Garantir que o valor seja uma string
                valor_dia = str(valor_dia) if valor_dia is not None else ''
                
                # Remover valores duplicados e ordenar
                if valor_dia:
                    valor_dia = ','.join(sorted(set(str(v).strip() for v in valor_dia.split(','))))
                
                df.loc[mask, dia] = valor_dia
            
            # Incrementar contador de professores atualizados
            total_atualizados += int(mask.sum())
        
        # Salvar CSV atualizado
        df.to_csv(csv_path, index=False)
        
        return jsonify({
            "message": "Disponibilidades salvas com sucesso!", 
            "total_professores_atualizados": total_atualizados
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao salvar disponibilidades: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/api/salvar_restricoes", methods=['POST'])
def salvar_restricoes():
    try:
        # Receber dados de restrições
        dados_restricoes = request.json
        
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV de disciplinas
        csv_path = os.path.join(data_path, 'disciplinas.csv')
        
        # Ler o CSV atual
        df = pd.read_csv(csv_path)
        
        # Contador de disciplinas atualizadas
        total_atualizadas = 0
        
        # Atualizar restrições
        for disciplina, restricoes in dados_restricoes.items():
            # Filtrar linhas da disciplina
            mask = df['disciplina'] == disciplina
            
            # Atualizar colunas de restrição
            for dia in ['r_seg', 'r_ter', 'r_qua', 'r_qui', 'r_sex']:
                # Converter para string vazia se não houver restrição
                valor_dia = restricoes.get(dia, '')
                
                # Garantir que o valor seja uma string
                valor_dia = str(valor_dia) if valor_dia is not None else ''
                
                # Remover valores duplicados e ordenar
                if valor_dia:
                    valor_dia = ','.join(sorted(set(str(v).strip() for v in valor_dia.split(','))))
                
                df.loc[mask, dia] = valor_dia
            
            # Incrementar contador de disciplinas atualizadas
            total_atualizadas += int(mask.sum())
        
        # Salvar CSV atualizado
        df.to_csv(csv_path, index=False)
        
        return jsonify({
            "message": "Restrições salvas com sucesso!", 
            "total_disciplinas_atualizadas": total_atualizadas
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao salvar restrições: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/api/salvar_excecoes", methods=['POST'])
def salvar_excecoes():
    try:
        # Receber dados de exceções
        dados_excecoes = request.json
        
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV de exceções
        csv_path = os.path.join(data_path, 'excecoes.csv')
        
        # Verificar se o arquivo existe, se não, criar com cabeçalho
        if not os.path.exists(csv_path):
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                f.write('professor,disciplina,turma,tipo,dias,horas,limite_duas_aulas,geminadas\n')
        
        # Ler o CSV atual
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Remover coluna 'descricao' se existir
        if 'descricao' in df.columns:
            df = df.drop(columns=['descricao'])
        
        # Adicionar colunas se não existirem
        colunas_necessarias = ['limite_duas_aulas', 'geminadas', 'dias', 'horas']
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                df[coluna] = ''
        
        # Contador de exceções atualizadas
        total_atualizadas = 0
        
        # Limpar exceções existentes antes de adicionar novas
        df = df.iloc[0:0]
        
        # Adicionar novas exceções
        for excecao in dados_excecoes:
            # Garantir que todos os campos sejam strings
            excecao_limpa = {
                'professor': str(excecao.get('professor', '')).strip(),
                'disciplina': str(excecao.get('disciplina', '')).strip(),
                'turma': str(excecao.get('turma', '')).strip(),
                'tipo': str(excecao.get('tipo', '')).strip(),
                'dias': str(excecao.get('dias', '')).strip(),
                'horas': str(excecao.get('horas', '')).strip(),
                'limite_duas_aulas': str(excecao.get('limite_duas_aulas', 'NÃO')).strip().upper(),
                'geminadas': str(excecao.get('geminadas', 'NÃO')).strip().upper()
            }
            
            # Garantir que limite_duas_aulas e geminadas sejam SIM ou NÃO
            for coluna in ['limite_duas_aulas', 'geminadas']:
                if excecao_limpa[coluna] not in ['SIM', 'NÃO']:
                    excecao_limpa[coluna] = 'NÃO'
            
            # Adicionar apenas se pelo menos um campo não estiver vazio
            if any(excecao_limpa.values()):
                df = pd.concat([df, pd.DataFrame([excecao_limpa])], ignore_index=True)
                total_atualizadas += 1
        
        # Salvar CSV atualizado
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        return jsonify({
            "message": "Exceções salvas com sucesso!", 
            "total_excecoes_atualizadas": total_atualizadas
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao salvar exceções: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/api/excecoes")
def obter_excecoes():
    try:
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV de exceções
        csv_path = os.path.join(data_path, 'excecoes.csv')
        
        # Verificar se o arquivo existe
        if not os.path.exists(csv_path):
            return jsonify([]), 200
        
        # Ler o arquivo CSV
        df = pd.read_csv(csv_path)
        
        # Substituir NaN por string vazia
        colunas = ['professor', 'disciplina', 'turma', 'tipo', 'descricao', 'limite_duas_aulas']
        for coluna in colunas:
            df[coluna] = df[coluna].fillna('').astype(str)
        
        # Converter para lista de dicionários
        excecoes = df.to_dict('records')
        
        # Processar descrição para dias e horas
        for excecao in excecoes:
            partes = excecao['descricao'].split(',')
            excecao['dias'] = [p for p in partes if p in ['seg', 'ter', 'qua', 'qui', 'sex']]
            excecao['horas'] = [p for p in partes if p.isdigit()]
            excecao['dias'] = ','.join(excecao['dias'])
            excecao['horas'] = ','.join(excecao['horas'])
            
            # Garantir que limite_duas_aulas seja SIM ou NÃO
            if excecao['limite_duas_aulas'] not in ['SIM', 'NÃO']:
                excecao['limite_duas_aulas'] = 'NÃO'
        
        return jsonify(excecoes), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de exceções: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route("/api/carregar_excecoes")
def carregar_excecoes():
    try:
        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Caminho completo do arquivo CSV de exceções
        csv_path = os.path.join(data_path, 'excecoes.csv')
        
        # Verificar se o arquivo existe
        if not os.path.exists(csv_path):
            # Criar arquivo com cabeçalho se não existir
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                f.write('professor,disciplina,turma,tipo,dias,horas,limite_duas_aulas,geminadas\n')
            return jsonify([]), 200
        
        # Ler o arquivo CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Remover coluna 'descricao' se existir
        if 'descricao' in df.columns:
            df = df.drop(columns=['descricao'])
        
        # Adicionar colunas se não existirem
        colunas_necessarias = ['limite_duas_aulas', 'geminadas', 'dias', 'horas']
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                df[coluna] = ''
        
        # Substituir NaN por string vazia
        colunas = ['professor', 'disciplina', 'turma', 'tipo', 'dias', 'horas', 'limite_duas_aulas', 'geminadas']
        for coluna in colunas:
            df[coluna] = df[coluna].fillna('').astype(str)
        
        # Corrigir caracteres especiais
        df['limite_duas_aulas'] = df['limite_duas_aulas'].replace({'NÃƒO': 'NÃO', 'SIM': 'SIM'})
        df['geminadas'] = df['geminadas'].replace({'NÃƒO': 'NÃO', 'SIM': 'SIM'})
        
        # Converter para lista de dicionários
        excecoes = df.to_dict('records')
        
        # Garantir que limite_duas_aulas e geminadas sejam SIM ou NÃO
        for excecao in excecoes:
            for coluna in ['limite_duas_aulas', 'geminadas']:
                valor = str(excecao.get(coluna, 'NÃO')).upper()
                excecao[coluna] = 'SIM' if valor == 'SIM' else 'NÃO'
            
            # Garantir que dias e horas sejam strings
            excecao['dias'] = str(excecao.get('dias', '')).lower()
            excecao['horas'] = str(excecao.get('horas', ''))
        
        # Adicionar log para depuração
        print("Exceções carregadas:", excecoes)
        
        return jsonify(excecoes), 200
    
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados de exceções: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/progresso_alocacoes')
def progresso_alocacoes():
    """
    Endpoint de Server-Sent Events para progresso de alocações
    """
    return Response(
        gerar_evento_progresso(), 
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

def notificar_progresso(progresso):
    """
    Função para atualizar o progresso de alocação
    
    :param progresso: Percentual de progresso (0-100)
    """
    global _ultimo_progresso
    _ultimo_progresso = max(0, min(100, progresso))

@app.route('/api/gerar_horario', methods=['GET'])
def gerar_horario_genetico():
    """
    Endpoint para gerar horário
    """
    try:
        # Obter turno da requisição
        turno = request.args.get('turno')
        
        # Validar turno
        if not turno:
            return jsonify({"error": "Turno não especificado"}), 400
        
        # Resetar progresso
        global _ultimo_progresso
        _ultimo_progresso = 0
        
        # Inicializar ML
        ml_model = HorarioML(DATA_PATH)
        
        # Treinar modelo de ML
        ml_model.treinar_modelo()
        
        # Gerar horário
        schedule_generator = ScheduleGenerator(DATA_PATH, ml_model=ml_model)
        horario = schedule_generator.gerar_horario(turno)
        
        # Adicionar informações de alocações incompletas, se houver
        if schedule_generator.alocacoes_incompletas:
            horario['_alocacoes_incompletas'] = schedule_generator.alocacoes_incompletas
        
        return jsonify(horario)
    
    except Exception as e:
        print(f"❌ Erro ao gerar horário: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/validar_conflito", methods=['POST'])
def validar_conflito():
    try:
        dados = request.json
        professor = dados.get('professor')
        dia = dados.get('dia')
        hora = dados.get('hora')

        # Definir caminho para pasta de dados
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'scheduler', 'data'
        )
        
        # Verificar conflitos nas disponibilidades
        csv_path = os.path.join(data_path, 'professores.csv')
        df_professores = pd.read_csv(csv_path)
        
        # Verificar se o professor já tem aula marcada neste horário
        professor_row = df_professores[df_professores['nome'] == professor]
        if not professor_row.empty:
            disponibilidade = str(professor_row[dia].iloc[0])
            if hora not in disponibilidade.split(','):
                return jsonify({"temConflito": True, "motivo": "Professor não disponível neste horário"})
        
        return jsonify({"temConflito": False})

    except Exception as e:
        print(f"❌ Erro ao validar conflito: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/metricas')
def obter_metricas_ml():
    """Retorna métricas do modelo de ML"""
    try:
        ml_model = HorarioML(DATA_PATH)
        
        # Caminho para o arquivo de histórico
        historico_path = os.path.join(DATA_PATH, 'historico_horarios.csv')
        
        # Verificar se o arquivo de histórico existe
        if not os.path.exists(historico_path):
            return jsonify({"error": "Arquivo de histórico não encontrado"}), 404
        
        # Carregar histórico
        historico_df = pd.read_csv(historico_path)
        
        # Verificar se o arquivo do modelo existe
        modelo_path = os.path.join(DATA_PATH, 'modelo_horario.joblib')
        if not os.path.exists(modelo_path):
            return jsonify({"error": "Arquivo do modelo não encontrado"}), 404
        
        metricas = {
            'total_horarios_gerados': len(historico_df),
            'score_medio': float(historico_df['score'].mean()),
            'score_maximo': float(historico_df['score'].max()),
            'evolucao_scores': historico_df['score'].tolist()[-10:],  # últimos 10 scores
            'data_ultimo_treino': os.path.getmtime(modelo_path)
        }
        
        return jsonify(metricas), 200
        
    except Exception as e:
        print(f"❌ Erro ao obter métricas ML: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/treinar', methods=['POST'])
def treinar_modelo():
    """Força um novo treinamento do modelo"""
    try:
        ml_model = HorarioML(DATA_PATH)
        ml_model.treinar_modelo()
        
        return jsonify({"message": "Modelo treinado com sucesso"}), 200
        
    except Exception as e:
        print(f"❌ Erro ao treinar modelo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/analise')
def obter_analise_ml():
    """Retorna análise completa do sistema de ML"""
    try:
        ml_model = HorarioML(DATA_PATH)
        
        relatorio = ml_model.obter_relatorio_aprendizado()
        tendencias = ml_model.analisar_tendencias()
        
        return jsonify({
            'relatorio': relatorio,
            'tendencias': tendencias,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Erro ao obter análise ML: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/tendencias')
def obter_tendencias_ml():
    """Retorna análise de tendências do sistema"""
    try:
        ml_model = HorarioML(DATA_PATH)
        tendencias = ml_model.analisar_tendencias()
        
        return jsonify({
            'tendencias': tendencias,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Erro ao obter tendências ML: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ml/historico')
def obter_historico_ml():
    """Retorna histórico de treinamento do modelo"""
    try:
        ml_model = HorarioML(DATA_PATH)
        historico_path = os.path.join(DATA_PATH, 'historico_treinamento.json')
        
        if not os.path.exists(historico_path):
            return jsonify({"message": "Nenhum histórico disponível"}), 404
            
        with open(historico_path, 'r') as f:
            historico = json.load(f)
            
        return jsonify(historico), 200
        
    except Exception as e:
        print(f"❌ Erro ao obter histórico ML: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
