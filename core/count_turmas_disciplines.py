import os
import pandas as pd
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('count_turmas_disciplines.log', mode='w')
    ]
)

def gerar_dataframe_professores_disciplinas():
    """
    Gera DataFrame com dados completos de professores, disciplinas e turmas
    """
    try:
        # Definir caminho base para a pasta data
        BASE_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scheduler', 'data')
        
        # Carregar dados de professores, disciplinas e turmas
        professores_df = pd.read_csv(os.path.join(BASE_DATA_PATH, 'professores.csv'))
        disciplinas_df = pd.read_csv(os.path.join(BASE_DATA_PATH, 'disciplinas.csv'))
        turmas_df = pd.read_csv(os.path.join(BASE_DATA_PATH, 'turmas.csv'))
        
        # Criar lista para armazenar dados detalhados
        dados_detalhados = []
        
        # Iterar sobre cada registro de professor
        for _, prof_row in professores_df.iterrows():
            nome = prof_row['nome']
            disciplina_prof = prof_row['disciplina']
            turma_prof = prof_row['turma']
            
            # Buscar informações da disciplina
            disciplina_info = disciplinas_df[
                (disciplinas_df['disciplina'] == disciplina_prof) & 
                (disciplinas_df['turma'] == turma_prof)
            ]
            
            # Buscar informações da turma
            turma_info = turmas_df[turmas_df['turma'] == turma_prof]
            
            # Se encontrar informações da disciplina
            if not disciplina_info.empty and not turma_info.empty:
                dados_detalhados.append({
                    'nome': nome,
                    'disciplina': disciplina_prof,
                    'turma': turma_prof,
                    'turno': turma_info.iloc[0]['turno'],
                    'carga_horaria': disciplina_info.iloc[0]['carga_horaria'],
                    'aulas_por_dia': turma_info.iloc[0]['aulas_por_dia'],
                    'd_seg': prof_row['d_seg'],
                    'd_ter': prof_row['d_ter'],
                    'd_qua': prof_row['d_qua'],
                    'd_qui': prof_row['d_qui'],
                    'd_sex': prof_row['d_sex'],
                    'r_seg': disciplina_info.iloc[0]['r_seg'],
                    'r_ter': disciplina_info.iloc[0]['r_ter'],
                    'r_qua': disciplina_info.iloc[0]['r_qua'],
                    'r_qui': disciplina_info.iloc[0]['r_qui'],
                    'r_sex': disciplina_info.iloc[0]['r_sex']
                })
        
        # Converter para DataFrame
        df_detalhado = pd.DataFrame(dados_detalhados)
        
        # Calcular total de aulas por professor
        df_detalhado['total_aulas'] = df_detalhado.groupby('nome')['carga_horaria'].transform('sum')
        
        # Ordenar por total de aulas em ordem decrescente
        df_detalhado = df_detalhado.sort_values('total_aulas', ascending=False)
        
        # Salvar DataFrame em CSV
        csv_path = os.path.join(BASE_DATA_PATH, 'professores_disciplinas_turmas.csv')
        
        # Salvar DataFrame em CSV
        df_detalhado.to_csv(csv_path, index=False)
        logging.info(f"DataFrame detalhado salvo em {csv_path}")
        
        return df_detalhado

    except Exception as e:
        logging.error(f"Erro ao gerar DataFrame: {e}")
        return None

def main():
    # Gerar DataFrame
    resultado = gerar_dataframe_professores_disciplinas()
    
    if resultado is not None:
        print("DataFrame gerado com sucesso!")
        print(resultado.head())

if __name__ == "__main__":
    main() 