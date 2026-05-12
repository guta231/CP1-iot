import sqlite3

# 1. Conecta ao banco (arquivo local)
db = sqlite3.connect('smartgym.db')
cursor = db. cursor( )

# 2. Cria a tabela de Alunos
cursor.execute("CREATE TABLE IF NOT EXISTS alunos (id TEXT, nome TEXT, exercicio TEXT, repeticoes INTEGER)")

# 3. Insere um aluno (Cadastro Manual)
cursor.execute("INSERT OR IGNORE INTO alunos VALUES ( 'A95D9B99', 'Naka', 'Agachamentos', '10')")
db.commit( ) # Salva no disco

db.close()