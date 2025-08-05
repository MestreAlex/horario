import pandas as pd
import os

# Definir o caminho correto para o arquivo CSV
base_path = r'C:\Users\Alex Menezes\projetos\horario\data\professores.csv'

# Ler o CSV de professores
df = pd.read_csv(base_path)

# Contar ocorrências por professor
professor_counts = df['nome'].value_counts()

print('Número máximo de disciplinas por professor:', professor_counts.max())

print('\nProfessores com mais disciplinas:')
print(professor_counts[professor_counts == professor_counts.max()]) 