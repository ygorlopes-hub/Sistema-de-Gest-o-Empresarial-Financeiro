import pandas as pd
from sqlalchemy import create_engine

# 1. Criação do Excel de teste (Simulando a vida real)
dados_falsos = {
    'Produto': ['Caixa de Papelão P', 'Fita Adesiva Kraft', 'Plástico Bolha 50m', 'Caixa de Papelão G'],
    'Quantidade': [50, 5, 12, 100],
    'Estoque_Minimo': [20, 10, 15, 30]
}
df_teste = pd.DataFrame(dados_falsos)
df_teste.to_excel('estoque_teste.xlsx', index=False)
print("-> Arquivo 'estoque_teste.xlsx' criado!")

# 2. Leitura (Extract) e Limpeza (Transform)
df = pd.read_excel('estoque_teste.xlsx')
df.columns = [str(col).lower() for col in df.columns] # Padroniza colunas em minúsculo

# 3. Conexão e Carga (Load) no MySQL
# Substitua 'suasenha' pela senha que você criou para o usuário 'admin' no Ubuntu
str_conexao = "mysql+pymysql://admin:suasenha@localhost/teste_empresa"
engine = create_engine(str_conexao)

df.to_sql('tb_estoque', con=engine, if_exists='replace', index=False)
print("-> SUCESSO! Dados migrados do Excel para o MySQL.")