import pandas as pd
import os

# Definir o caminho correto para o arquivo CSV
base_path = r'C:\Users\Alex Menezes\projetos\horario\scheduler\data\professores.csv'

# Verificar se o arquivo existe
if not os.path.exists(base_path):
    print(f"Erro: Arquivo não encontrado em {base_path}")
    exit(1)

# Ler o CSV de professores
try:
    df = pd.read_csv(base_path)
    
    # Filtrar linhas do professor com mais registros
    professor_max = df['nome'].value_counts().idxmax()
    fagner_df = df[df['nome'] == professor_max]
    
    print(f"\nDetalhes do professor com mais registros ({professor_max}):")
    print(f"Total de registros: {len(fagner_df)}")
    
    # Mostrar disciplinas únicas
    disciplinas_unicas = fagner_df['disciplina'].unique()
    print(f"\nDisciplinas únicas: {len(disciplinas_unicas)}")
    print("Disciplinas:")
    for disc in disciplinas_unicas:
        print(f"- {disc}")
    
    # Mostrar turmas únicas
    turmas_unicas = fagner_df['turma'].unique()
    print(f"\nTurmas únicas: {len(turmas_unicas)}")
    print("Turmas:")
    for turma in turmas_unicas:
        print(f"- {turma}")
    
    # Mostrar combinações únicas de disciplina e turma
    combinacoes_unicas = fagner_df.groupby(['disciplina', 'turma']).size().reset_index(name='count')
    print(f"\nCombinações únicas de disciplina e turma: {len(combinacoes_unicas)}")
    print(combinacoes_unicas)

except Exception as e:
    print(f"Erro ao processar o arquivo: {e}") 