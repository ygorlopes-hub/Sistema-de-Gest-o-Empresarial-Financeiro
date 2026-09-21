from flask import Flask, render_template, request, redirect, url_for, send_file, session
from functools import wraps
from flask_socketio import SocketIO, emit
import io
import pymysql
import pandas as pd
from datetime import date, timedelta
import os
from dotenv import load_dotenv

# CARREGA O ARQUIVO .env AQUI
load_dotenv()

# ==========================================
# CONFIGURAÇÃO DO APLICATIVO
# ==========================================
app = Flask(__name__)
# Lê a secret key do .env também
app.secret_key = os.getenv('SECRET_KEY', 'chave_secreta_empresa_123')
socketio = SocketIO(app)

def get_conexao():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'blembalagens'), # Se o .env falhar, ele usa essa de garantia (opcional, se for uso local)
        database=os.getenv('DB_NAME', 'teste_empresa'),
        cursorclass=pymysql.cursors.DictCursor
    )

# ==========================================
# DECORATORS E AUDITORIA (LOGS)
# ==========================================
def registrar_log(acao, detalhes=""):
    usuario = session.get('usuario_nome', 'Desconhecido')
    ip_cliente = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    try:
        conexao = get_conexao()
        with conexao.cursor() as cursor:
            sql = "INSERT INTO tb_logs_auditoria (usuario_nome, ip_maquina, acao, detalhes) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (usuario, ip_cliente, acao, detalhes))
            conexao.commit()
        conexao.close()
    except Exception as e:
        print("Erro ao registrar log:", e)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('usuario_nivel') != 'admin':
            return "Acesso Negado: Apenas administradores podem excluir ou importar dados no sistema.", 403
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# MÓDULO: AUTENTICAÇÃO
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        
        conexao = get_conexao()
        with conexao.cursor() as cursor:
            cursor.execute("SELECT * FROM tb_usuarios WHERE usuario = %s AND senha = %s", (usuario, senha))
            user = cursor.fetchone()
        conexao.close()
        
        if user:
            session['usuario_id'] = user['id']
            session['usuario_nome'] = user['nome']
            session['usuario_nivel'] = user['nivel']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro='Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ==========================================
# MÓDULO: ESTOQUE
# ==========================================
@app.route('/')
@login_required
def dashboard():
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT produto, quantidade, estoque_minimo FROM tb_estoque")
        produtos = cursor.fetchall()
    conexao.close()

    total_itens = len(produtos)
    abaixo_minimo = 0
    estoque_adequado = 0

    for p in produtos:
        qtd = p['quantidade']
        minimo = p['estoque_minimo']

        if qtd <= minimo:
            p['alerta'] = 'Comprar Urgente!'
            p['cor'] = 'danger' 
            abaixo_minimo += 1
        elif qtd <= minimo + 5: 
            p['alerta'] = 'Atenção'
            p['cor'] = 'warning text-dark'
            estoque_adequado += 1
        else:
            p['alerta'] = 'Adequado'
            p['cor'] = 'primary'
            estoque_adequado += 1

    return render_template('index.html', produtos=produtos, total_itens=total_itens, abaixo_minimo=abaixo_minimo, estoque_adequado=estoque_adequado)

@app.route('/atualizar', methods=['POST'])
@login_required
def atualizar_estoque():
    produto_escolhido = request.form.get('produto')
    qtd_adicional = request.form.get('quantidade')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "UPDATE tb_estoque SET quantidade = quantidade + %s WHERE produto = %s"
        cursor.execute(sql, (qtd_adicional, produto_escolhido))
        
        sql_hist = "INSERT INTO tb_historico (produto, acao, quantidade) VALUES (%s, 'Entrada', %s)"
        cursor.execute(sql_hist, (produto_escolhido, qtd_adicional))
        
        conexao.commit() 
    conexao.close()
    return redirect(url_for('dashboard'))

@app.route('/retirar', methods=['POST'])
@login_required
def retirar_estoque():
    produto_escolhido = request.form.get('produto')
    qtd_retirada = request.form.get('quantidade')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "UPDATE tb_estoque SET quantidade = quantidade - %s WHERE produto = %s"
        cursor.execute(sql, (qtd_retirada, produto_escolhido))
        
        sql_hist = "INSERT INTO tb_historico (produto, acao, quantidade) VALUES (%s, 'Saída', %s)"
        cursor.execute(sql_hist, (produto_escolhido, qtd_retirada))
        
        conexao.commit() 
    conexao.close()
    return redirect(url_for('dashboard'))

@app.route('/adicionar_material', methods=['POST'])
@login_required
def adicionar_material():
    novo_produto = request.form.get('produto')
    nova_quantidade = request.form.get('quantidade')
    novo_minimo = request.form.get('estoque_minimo')
    novo_status = request.form.get('status') 

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "INSERT INTO tb_estoque (produto, quantidade, estoque_minimo, status) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (novo_produto, nova_quantidade, novo_minimo, novo_status))
        
        sql_hist = "INSERT INTO tb_historico (produto, acao, quantidade) VALUES (%s, 'Cadastro', %s)"
        cursor.execute(sql_hist, (novo_produto, nova_quantidade))
        
        conexao.commit() 
    conexao.close()
    return redirect(url_for('dashboard'))

@app.route('/deletar', methods=['POST'])
@login_required
@admin_required
def deletar_material():
    produto_excluir = request.form.get('produto')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "DELETE FROM tb_estoque WHERE produto = %s"
        cursor.execute(sql, (produto_excluir,))
        conexao.commit() 
    conexao.close()
    return redirect(url_for('dashboard'))

@app.route('/relatorios')
@login_required
def relatorios():
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT * FROM tb_historico ORDER BY data_registro DESC")
        historico = cursor.fetchall()
    conexao.close()
    return render_template('relatorios.html', historico=historico)

@app.route('/importar_excel', methods=['POST'])
@login_required
@admin_required
def importar_excel():
    arquivo = request.files.get('documento_excel')
    if arquivo:
        planilha = pd.read_excel(arquivo)
        conexao = get_conexao()
        with conexao.cursor() as cursor:
            for index, linha in planilha.iterrows():
                produto = str(linha['Produto'])
                quantidade = int(linha['Quantidade'])
                minimo = int(linha['Estoque Minimo'])
                
                sql = "INSERT INTO tb_estoque (produto, quantidade, estoque_minimo, status) VALUES (%s, %s, %s, 'Ativo')"
                cursor.execute(sql, (produto, quantidade, minimo))
                
                sql_hist = "INSERT INTO tb_historico (produto, acao, quantidade) VALUES (%s, 'Importação Excel', %s)"
                cursor.execute(sql_hist, (produto, quantidade))
                
            conexao.commit()
        conexao.close()
    return redirect(url_for('dashboard'))


# ==========================================
# MÓDULO: FINANCEIRO
# ==========================================
@app.route('/financeiro', methods=['GET', 'POST'])
@login_required
def financeiro():
    hoje = date.today()
    mes_atual = str(hoje.month).zfill(2)
    ano_atual = str(hoje.year)

    if request.method == 'POST':
        mes_ano = request.form.get('mes_filtro') 
        if mes_ano:
            ano_atual, mes_atual = mes_ano.split('-')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT * FROM tb_financeiro WHERE MONTH(data_vencimento) = %s AND YEAR(data_vencimento) = %s ORDER BY data_vencimento ASC", (mes_atual, ano_atual))
        contas = cursor.fetchall()
        
        cursor.execute("""
            SELECT data_vencimento, SUM(valor) as total 
            FROM tb_financeiro 
            WHERE MONTH(data_vencimento) = %s AND YEAR(data_vencimento) = %s 
            GROUP BY data_vencimento 
            ORDER BY data_vencimento ASC
        """, (mes_atual, ano_atual))
        dados_grafico_raw = cursor.fetchall()
    conexao.close()

    dados_grafico = []
    for d in dados_grafico_raw:
        venc = d['data_vencimento']
        dia_formatado = venc.strftime('%d/%m') if hasattr(venc, 'strftime') else str(venc)
        dados_grafico.append({'dia': dia_formatado, 'total': float(d['total'] or 0)})

    for c in contas:
        vencimento = c['data_vencimento']
        if c['status_pagamento'] == 'Pago':
            c['alerta'] = 'Pago'
            c['cor'] = 'success'
        else:
            if vencimento < hoje:
                c['alerta'] = 'Vencido'
                c['cor'] = 'danger'
            elif vencimento <= hoje + timedelta(days=3):
                c['alerta'] = 'Perto de Vencer'
                c['cor'] = 'warning text-dark'
            else:
                c['alerta'] = 'No Prazo'
                c['cor'] = 'primary'

    mes_filtro = f"{ano_atual}-{mes_atual}"
    return render_template('financeiro.html', contas=contas, dados_grafico=dados_grafico, mes_filtro=mes_filtro)

@app.route('/adicionar_conta', methods=['POST'])
@login_required
def adicionar_conta():
    descricao = request.form.get('descricao')
    valor = request.form.get('valor')
    data_vencimento = request.form.get('data_vencimento')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "INSERT INTO tb_financeiro (descricao, valor, data_vencimento) VALUES (%s, %s, %s)"
        cursor.execute(sql, (descricao, valor, data_vencimento))
        conexao.commit()
    conexao.close()
    return redirect(url_for('financeiro'))

@app.route('/pagar_conta', methods=['POST'])
@login_required
def pagar_conta():
    id_conta = request.form.get('id_conta')
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "UPDATE tb_financeiro SET status_pagamento = 'Pago' WHERE id = %s"
        cursor.execute(sql, (id_conta,))
        conexao.commit()
    conexao.close()
    return redirect(url_for('financeiro'))

@app.route('/deletar_conta', methods=['POST'])
@login_required
@admin_required
def deletar_conta():
    id_conta = request.form.get('id_conta')
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "DELETE FROM tb_financeiro WHERE id = %s"
        cursor.execute(sql, (id_conta,))
        conexao.commit()
    conexao.close()
    return redirect(url_for('financeiro'))

@app.route('/exportar_excel_financeiro')
@login_required
def exportar_excel_financeiro():
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT descricao, valor, data_vencimento, status_pagamento FROM tb_financeiro")
        contas = cursor.fetchall()
    conexao.close()

    df = pd.DataFrame(contas)
    if not df.empty:
        df.columns = ['Descricao', 'Valor', 'Data Vencimento', 'Status']

    saida = io.BytesIO()
    with pd.ExcelWriter(saida, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contas')
    saida.seek(0)
    return send_file(saida, download_name='relatorio_financeiro.xlsx', as_attachment=True)

@app.route('/importar_excel_financeiro', methods=['POST'])
@login_required
@admin_required
def importar_excel_financeiro():
    arquivo = request.files.get('documento_excel')
    if arquivo:
        planilha = pd.read_excel(arquivo)
        conexao = get_conexao()
        with conexao.cursor() as cursor:
            for index, linha in planilha.iterrows():
                descricao = str(linha['Descricao'])
                valor = float(linha['Valor'])
                data_vencimento = pd.to_datetime(linha['Data Vencimento']).strftime('%Y-%m-%d')
                
                sql_verifica = "SELECT id FROM tb_financeiro WHERE descricao = %s AND valor = %s AND data_vencimento = %s"
                cursor.execute(sql_verifica, (descricao, valor, data_vencimento))
                conta_existe = cursor.fetchone()
                
                if not conta_existe:
                    sql_insere = "INSERT INTO tb_financeiro (descricao, valor, data_vencimento) VALUES (%s, %s, %s)"
                    cursor.execute(sql_insere, (descricao, valor, data_vencimento))
                
            conexao.commit()
        conexao.close()
    return redirect(url_for('financeiro'))


# ==========================================
# MÓDULO: CHEQUES
# ==========================================
@app.route('/cheques')
@login_required
def cheques():
    page = request.args.get('page', 1, type=int)
    termo = request.args.get('pesquisa', '').strip()
    banco_filtro = request.args.get('banco', '').strip()
    status_filtro = request.args.get('status', '').strip()
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    filtro_emissor = request.args.get('filtro_emissor', '').strip()
    filtro_rec_inicio = request.args.get('filtro_rec_inicio', '').strip()
    filtro_rec_fim = request.args.get('filtro_rec_fim', '').strip()
    filtro_venc_inicio = request.args.get('filtro_venc_inicio', '').strip()
    filtro_venc_fim = request.args.get('filtro_venc_fim', '').strip()
    filtro_valor_min = request.args.get('filtro_valor_min', '').strip()
    filtro_valor_max = request.args.get('filtro_valor_max', '').strip()
    filtro_numero_cheque = request.args.get('filtro_numero_cheque', '').strip()
    filtro_destino = request.args.get('filtro_destino', '').strip()
    filtro_rep_inicio = request.args.get('filtro_rep_inicio', '').strip()
    filtro_rep_fim = request.args.get('filtro_rep_fim', '').strip()
    ordem = request.args.get('ordem', '').strip()  # <-- Captura a ordenação selecionada

    per_page = 50
    offset = (page - 1) * per_page

    query_base = "FROM tb_cheques WHERE 1=1"
    params = []

    if termo:
        query_base += " AND (cliente LIKE %s OR emissor LIKE %s OR numero_cheque LIKE %s OR banco LIKE %s OR status_cheque LIKE %s)"
        termo_like = f"%{termo}%"
        params.extend([termo_like, termo_like, termo_like, termo_like, termo_like])
        
    if banco_filtro:
        query_base += " AND banco = %s"
        params.append(banco_filtro)

    if status_filtro:
        if status_filtro == 'Pendente':
            query_base += " AND (status_cheque = 'Pendente' OR status_cheque IS NULL)"
        else:
            query_base += " AND status_cheque = %s"
            params.append(status_filtro)
            
    if data_inicio:
        query_base += " AND data_bom_para >= %s"
        params.append(data_inicio)
        
    if data_fim:
        query_base += " AND data_bom_para <= %s"
        params.append(data_fim)

    if filtro_emissor:
        query_base += " AND (cliente LIKE %s OR emissor LIKE %s)"
        params.extend([f"%{filtro_emissor}%", f"%{filtro_emissor}%"])
        
    if filtro_rec_inicio:
        query_base += " AND data_recebimento >= %s"
        params.append(filtro_rec_inicio)
    if filtro_rec_fim:
        query_base += " AND data_recebimento <= %s"
        params.append(filtro_rec_fim)
        
    if filtro_venc_inicio:
        query_base += " AND data_bom_para >= %s"
        params.append(filtro_venc_inicio)
    if filtro_venc_fim:
        query_base += " AND data_bom_para <= %s"
        params.append(filtro_venc_fim)
        
    if filtro_valor_min:
        query_base += " AND valor >= %s"
        params.append(filtro_valor_min)

    if filtro_valor_max:
        query_base += " AND valor <= %s"
        params.append(filtro_valor_max)

    if filtro_numero_cheque:
        query_base += " AND numero_cheque LIKE %s"
        params.append(f"%{filtro_numero_cheque}%")

    if filtro_destino:
        termo_pesquisa = filtro_destino.strip()
        partes_data = termo_pesquisa.split('/')
        termo_sql_data = ""
        if len(partes_data) == 3 and len(partes_data[2]) == 4:
            termo_sql_data = f"{partes_data[2]}-{partes_data[1]}-{partes_data[0]}"
        elif len(partes_data) == 2:
            termo_sql_data = f"-{partes_data[1]}-{partes_data[0]}"

        if termo_sql_data:
            query_base += " AND (destino LIKE %s OR info_repasse LIKE %s OR data_repasse LIKE %s)"
            termo_like = f"%{termo_pesquisa}%"
            termo_data_like = f"%{termo_sql_data}%"
            params.extend([termo_like, termo_like, termo_data_like])
        else:
            query_base += " AND (destino LIKE %s OR info_repasse LIKE %s OR CAST(data_repasse AS CHAR) LIKE %s)"
            termo_like = f"%{termo_pesquisa}%"
            params.extend([termo_like, termo_like, termo_like])

    if filtro_rep_inicio:
        query_base += " AND data_repasse >= %s"
        params.append(filtro_rep_inicio)

    if filtro_rep_fim:
        query_base += " AND data_repasse <= %s"
        params.append(filtro_rep_fim)

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("UPDATE tb_cheques SET status_cheque = 'Repassado' WHERE data_repasse IS NOT NULL")
        conexao.commit()

        cursor.execute(f"SELECT COUNT(*) as total {query_base}", tuple(params))
        total_registros = cursor.fetchone()['total']

        query_resumo = f"""
            SELECT 
                SUM(valor) as valor_total,
                SUM(CASE WHEN status_cheque = 'Compensado' THEN 1 ELSE 0 END) as compensados,
                SUM(CASE WHEN status_cheque = 'Repassado' THEN 1 ELSE 0 END) as repassados,
                SUM(CASE WHEN status_cheque = 'Devolvido' THEN 1 ELSE 0 END) as devolvidos,
                SUM(CASE WHEN status_cheque = 'Pendente' OR status_cheque IS NULL THEN 1 ELSE 0 END) as pendentes
            {query_base}
        """
        cursor.execute(query_resumo, tuple(params))
        resumo = cursor.fetchone()
        
        resumo['valor_total'] = resumo['valor_total'] or 0
        resumo['compensados'] = int(resumo['compensados'] or 0)
        resumo['repassados'] = int(resumo['repassados'] or 0)
        resumo['devolvidos'] = int(resumo['devolvidos'] or 0)
        resumo['pendentes'] = int(resumo['pendentes'] or 0)

        cursor.execute("SELECT DISTINCT banco FROM tb_cheques WHERE banco IS NOT NULL AND banco != '' AND banco != 'nan' ORDER BY banco")
        bancos_db = [str(row['banco']).strip() for row in cursor.fetchall() if row['banco']]
        
        cursor.execute("SELECT DISTINCT cliente FROM tb_cheques WHERE cliente IS NOT NULL AND cliente != '' AND cliente != 'nan' ORDER BY cliente")
        clientes_db = [str(row['cliente']).strip() for row in cursor.fetchall() if row['cliente']]
        
        cursor.execute("SELECT DISTINCT emissor FROM tb_cheques WHERE emissor IS NOT NULL AND emissor != '' AND emissor != 'nan' ORDER BY emissor")
        emissores_db = [str(row['emissor']).strip() for row in cursor.fetchall() if row['emissor']]

        cursor.execute("SELECT DISTINCT cnpj_cpf FROM tb_cheques WHERE cnpj_cpf IS NOT NULL AND cnpj_cpf != '' AND cnpj_cpf != 'nan' ORDER BY cnpj_cpf")
        cnpjs_db = [str(row['cnpj_cpf']).strip() for row in cursor.fetchall() if row['cnpj_cpf']]
        
        cursor.execute("SELECT DISTINCT destino FROM tb_cheques WHERE destino IS NOT NULL AND destino != '' AND destino != 'nan' ORDER BY destino")
        destinos_db = [str(row['destino']).strip() for row in cursor.fetchall() if row['destino']]

        # Alterna a ordenação se o usuário clicou para ordenar por vencimento mais próximo
        if ordem == 'venc_asc':
            query_dados = f"SELECT * {query_base} ORDER BY data_bom_para ASC, id ASC LIMIT %s OFFSET %s"
        elif ordem == 'venc_desc':
            query_dados = f"SELECT * {query_base} ORDER BY data_bom_para DESC, id ASC LIMIT %s OFFSET %s"
        else:
            query_dados = f"SELECT * {query_base} ORDER BY id DESC LIMIT %s OFFSET %s"

        params_dados = params + [per_page, offset]
        cursor.execute(query_dados, tuple(params_dados))
        lista_cheques = cursor.fetchall()

        cursor.execute("""
            SELECT DISTINCT emissor AS nome, cnpj_cpf 
            FROM tb_cheques 
            WHERE emissor IS NOT NULL AND emissor != '' 
            ORDER BY emissor ASC
        """)
        lista_emissores = cursor.fetchall()
        
    conexao.close()

    total_pages = (total_registros + per_page - 1) // per_page

    for ch in lista_cheques:
        if ch['status_cheque'] == 'Compensado':
            ch['cor'] = 'success'
        elif ch['status_cheque'] == 'Devolvido':
            ch['cor'] = 'danger'
        elif ch['status_cheque'] == 'Repassado':
            ch['cor'] = 'primary'
        else:
            ch['cor'] = 'warning text-dark'
            ch['status_cheque'] = 'Pendente'

    filtros = {
        'pesquisa': termo, 'banco': banco_filtro, 'status': status_filtro,
        'data_inicio': data_inicio, 'data_fim': data_fim,
        'filtro_emissor': filtro_emissor,
        'filtro_numero_cheque': filtro_numero_cheque,
        'filtro_destino': filtro_destino,
        'filtro_rep_inicio': filtro_rep_inicio,
        'filtro_rep_fim': filtro_rep_fim,
        'filtro_rec_inicio': filtro_rec_inicio, 'filtro_rec_fim': filtro_rec_fim,
        'filtro_venc_inicio': filtro_venc_inicio, 'filtro_venc_fim': filtro_venc_fim,
        'filtro_valor_min': filtro_valor_min, 'filtro_valor_max': filtro_valor_max,
        'ordem': ordem  # <-- Mantido no dicionário de filtros
    }

    return render_template(
        'cheques.html', 
        cheques=lista_cheques, 
        page=page, 
        total_pages=total_pages, 
        total_registros=total_registros, 
        bancos=bancos_db, 
        clientes=clientes_db, 
        emissores=emissores_db, 
        cnpjs=cnpjs_db, 
        destinos=destinos_db, 
        filtros=filtros, 
        resumo=resumo,
        lista_emissores=lista_emissores
    )

@app.route('/adicionar_cheque', methods=['POST'])
@login_required
def adicionar_cheque():
    datas_rec = request.form.getlist('data_recebimento[]')
    clientes = request.form.getlist('cliente[]')
    emissores = request.form.getlist('emissor[]')
    cnpjs_cpfs = request.form.getlist('cnpj_cpf[]')
    bancos = request.form.getlist('banco[]')
    numeros = request.form.getlist('numero_cheque[]')
    datas_bom_para = request.form.getlist('data_bom_para[]')
    valores = request.form.getlist('valor[]')
    destinos = request.form.getlist('destino[]')
    datas_repasse = request.form.getlist('data_repasse[]')
    infos_repasse = request.form.getlist('info_repasse[]')
    observacoes = request.form.getlist('observacoes[]')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = """
            INSERT INTO tb_cheques 
            (data_recebimento, cliente, emissor, cnpj_cpf, banco, numero_cheque, data_bom_para, valor, destino, data_repasse, observacoes, info_repasse) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cheques_cadastrados = 0
        for i in range(len(numeros)):
            if not numeros[i].strip():
                continue 
                
            cursor.execute(sql, (
                datas_rec[i] if datas_rec[i] else None,
                clientes[i],
                emissores[i],
                cnpjs_cpfs[i],
                bancos[i],
                numeros[i],
                datas_bom_para[i] if datas_bom_para[i] else None,
                valores[i] if valores[i] else 0,
                destinos[i],
                datas_repasse[i] if datas_repasse[i] else None,
                observacoes[i],
                infos_repasse[i]
            ))
            cheques_cadastrados += 1
            
        conexao.commit()
        registrar_log("CADASTROU CHEQUES", f"Cadastrou {cheques_cadastrados} cheque(s) em lote.")
    conexao.close()
    
    socketio.emit('atualizar_tela')
    return redirect(url_for('cheques'))

@app.route('/importar_excel_cheques', methods=['POST'])
@login_required
@admin_required
def importar_excel_cheques():
    arquivo = request.files.get('documento_excel')
    if arquivo:
        planilha = pd.read_excel(arquivo)
        planilha.columns = [str(c).strip().upper() for c in planilha.columns]
        
        conexao = get_conexao()
        with conexao.cursor() as cursor:
            for index, linha in planilha.iterrows():
                def get_valor_seguro(colunas_possiveis):
                    for col in colunas_possiveis:
                        if col in linha and pd.notna(linha[col]) and str(linha[col]).strip() != '':
                            return linha[col]
                    return None

                num_cheque = get_valor_seguro(['Nº CHEQUE', 'NUMERO CHEQUE', 'CHEQUE'])
                vencimento = get_valor_seguro(['VENC.', 'VENCIMENTO', 'BOM PARA'])
                
                if not num_cheque or not vencimento:
                    continue
                
                numero = str(num_cheque).split('.')[0].strip()
                banco = str(linha.get('BANCO', '')).strip()
                if banco == 'nan': banco = ''
                
                cliente = str(linha.get('CLIENTE', '')).strip()
                if cliente == 'nan': cliente = ''
                
                emissor = str(linha.get('EMISSOR', '')).strip()
                if not emissor or emissor == 'nan':
                    emissor = cliente
                
                cnpj_cpf = str(get_valor_seguro(['CNPJ/CPF', 'CNPJ', 'CPF']) or '').strip()
                if cnpj_cpf == 'nan': cnpj_cpf = ''
                
                valor = float(get_valor_seguro(['VALOR', 'R$ VALOR', 'R$']) or 0)
                destino = str(linha.get('DESTINO', '')).strip()
                if destino == 'nan': destino = ''
                
                obs = str(get_valor_seguro(['OBS', 'OBSERVAÇÕES', 'OBSERVACOES']) or '').strip()
                info_rep = str(get_valor_seguro(['INFO REPASSE', 'REPASSE']) or '').strip()
                
                if obs == 'nan': obs = ''
                if info_rep == 'nan': info_rep = ''
                
                def parse_data(val):
                    if pd.isna(val) or val == '' or str(val).strip().lower() == 'nan': 
                        return None
                    try:
                        dt = pd.to_datetime(val, dayfirst=True)
                        if pd.isna(dt): return None
                        return dt.strftime('%Y-%m-%d')
                    except:
                        return None

                data_rec_raw = get_valor_seguro(['DATA', 'DT', 'DATA RECEBIMENTO', 'DATA RECEB', 'RECEBIMENTO'])
                data_rec = parse_data(data_rec_raw)
                data_venc = parse_data(vencimento)
                data_rep = parse_data(get_valor_seguro(['DT REPAS', 'DT  REPAS', 'DATA REPASSE', 'REPASSE']))

                sql_verifica = """
                    SELECT id FROM tb_cheques 
                    WHERE banco = %s AND numero_cheque = %s AND emissor = %s AND data_bom_para = %s AND valor = %s
                """
                cursor.execute(sql_verifica, (banco, numero, emissor, data_venc, valor))
                cheque_existente = cursor.fetchone()
                
                if not cheque_existente:
                    sql_insere = """
                        INSERT INTO tb_cheques 
                        (data_recebimento, cliente, emissor, cnpj_cpf, banco, numero_cheque, data_bom_para, valor, destino, data_repasse, observacoes, info_repasse) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql_insere, (data_rec, cliente, emissor, cnpj_cpf, banco, numero, data_venc, valor, destino, data_rep, obs, info_rep))
                else:
                    id_cheque = cheque_existente['id']
                    sql_atualiza = """
                        UPDATE tb_cheques 
                        SET data_recebimento = %s, 
                            cliente = %s,
                            cnpj_cpf = %s,
                            destino = %s,
                            data_repasse = %s, 
                            observacoes = %s,
                            info_repasse = %s
                        WHERE id = %s
                    """
                    cursor.execute(sql_atualiza, (data_rec, cliente, cnpj_cpf, destino, data_rep, obs, info_rep, id_cheque))

            conexao.commit()
        conexao.close()
        
    socketio.emit('atualizar_tela')
    return redirect(url_for('cheques'))

@app.route('/exportar_excel_cheques', methods=['GET', 'POST'])
@login_required
def exportar_excel_cheques():
    termo = request.args.get('pesquisa', '').strip()
    banco_filtro = request.args.get('banco', '').strip()
    status_filtro = request.args.get('status', '').strip()
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    filtro_emissor = request.args.get('filtro_emissor', '').strip()
    filtro_rec_inicio = request.args.get('filtro_rec_inicio', '').strip()
    filtro_rec_fim = request.args.get('filtro_rec_fim', '').strip()
    filtro_venc_inicio = request.args.get('filtro_venc_inicio', '').strip()
    filtro_venc_fim = request.args.get('filtro_venc_fim', '').strip()
    filtro_valor_min = request.args.get('filtro_valor_min', '').strip()
    filtro_valor_max = request.args.get('filtro_valor_max', '').strip()
    filtro_numero_cheque = request.args.get('filtro_numero_cheque', '').strip()
    filtro_destino = request.args.get('filtro_destino', '').strip()
    filtro_rep_inicio = request.args.get('filtro_rep_inicio', '').strip()
    filtro_rep_fim = request.args.get('filtro_rep_fim', '').strip()

    query_base = "FROM tb_cheques WHERE 1=1"
    params = []

    if termo:
        query_base += " AND (cliente LIKE %s OR emissor LIKE %s OR numero_cheque LIKE %s OR banco LIKE %s OR status_cheque LIKE %s)"
        termo_like = f"%{termo}%"
        params.extend([termo_like, termo_like, termo_like, termo_like, termo_like])
        
    if banco_filtro:
        query_base += " AND banco = %s"
        params.append(banco_filtro)

    if status_filtro:
        if status_filtro == 'Pendente':
            query_base += " AND (status_cheque = 'Pendente' OR status_cheque IS NULL)"
        else:
            query_base += " AND status_cheque = %s"
            params.append(status_filtro)
            
    if data_inicio:
        query_base += " AND data_bom_para >= %s"
        params.append(data_inicio)
        
    if data_fim:
        query_base += " AND data_bom_para <= %s"
        params.append(data_fim)

    if filtro_emissor:
        query_base += " AND (cliente LIKE %s OR emissor LIKE %s)"
        params.extend([f"%{filtro_emissor}%", f"%{filtro_emissor}%"])
        
    if filtro_rec_inicio:
        query_base += " AND data_recebimento >= %s"
        params.append(filtro_rec_inicio)
    if filtro_rec_fim:
        query_base += " AND data_recebimento <= %s"
        params.append(filtro_rec_fim)
        
    if filtro_venc_inicio:
        query_base += " AND data_bom_para >= %s"
        params.append(filtro_venc_inicio)
    if filtro_venc_fim:
        query_base += " AND data_bom_para <= %s"
        params.append(filtro_venc_fim)
        
    if filtro_valor_min:
        query_base += " AND valor >= %s"
        params.append(filtro_valor_min)
    if filtro_valor_max:
        query_base += " AND valor <= %s"
        params.append(filtro_valor_max)

    if filtro_numero_cheque:
        query_base += " AND numero_cheque LIKE %s"
        params.append(f"%{filtro_numero_cheque}%")
    
    if filtro_destino:
        termo_pesquisa = filtro_destino.strip()
        partes_data = termo_pesquisa.split('/')
        termo_sql_data = ""
        if len(partes_data) == 3 and len(partes_data[2]) == 4:
            termo_sql_data = f"{partes_data[2]}-{partes_data[1]}-{partes_data[0]}"
        elif len(partes_data) == 2:
            termo_sql_data = f"-{partes_data[1]}-{partes_data[0]}"

        if termo_sql_data:
            query_base += " AND (destino LIKE %s OR info_repasse LIKE %s OR data_repasse LIKE %s)"
            termo_like = f"%{termo_pesquisa}%"
            termo_data_like = f"%{termo_sql_data}%"
            params.extend([termo_like, termo_like, termo_data_like])
        else:
            query_base += " AND (destino LIKE %s OR info_repasse LIKE %s OR CAST(data_repasse AS CHAR) LIKE %s)"
            termo_like = f"%{termo_pesquisa}%"
            params.extend([termo_like, termo_like, termo_like])

    if filtro_rep_inicio:
        query_base += " AND data_repasse >= %s"
        params.append(filtro_rep_inicio)

    if filtro_rep_fim:
        query_base += " AND data_repasse <= %s"
        params.append(filtro_rep_fim)
        
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        colunas_sql = "banco, numero_cheque, data_recebimento, cliente, emissor, cnpj_cpf, data_bom_para, valor, destino, data_repasse, observacoes, info_repasse, status_cheque"
        cursor.execute(f"SELECT {colunas_sql} {query_base} ORDER BY id ASC", tuple(params))
        dados = cursor.fetchall()
    conexao.close()
    
    df = pd.DataFrame(dados)
    if not df.empty:
        df.columns = ['Banco', 'Nº Cheque', 'Data Recebimento', 'Cliente', 'Emissor', 'CNPJ/CPF', 'Vencimento', 'Valor (R$)', 'Destino', 'Data Repasse', 'Observações Gerais', 'Info Repasse', 'Status']
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Cheques Filtrados')
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='cheques_filtrados.xlsx')

@app.route('/atualizar_status_cheque/<int:id_cheque>/<status>', methods=['POST'])
@login_required
def atualizar_status_cheque(id_cheque, status):
    if status in ['Compensado', 'Devolvido', 'Pendente', 'Repassado']:
        conexao = get_conexao()
        with conexao.cursor() as cursor:
            if status == 'Pendente':
                cursor.execute("UPDATE tb_cheques SET status_cheque = %s, data_repasse = NULL WHERE id = %s", (status, id_cheque))
            else:
                cursor.execute("UPDATE tb_cheques SET status_cheque = %s WHERE id = %s", (status, id_cheque))
            
            conexao.commit()
            registrar_log("ALTEROU STATUS", f"Mudou o status do cheque ID {id_cheque} para {status}")
        conexao.close()
        
        socketio.emit('atualizar_tela')
        
    return redirect(request.referrer or url_for('cheques'))

@app.route('/deletar_cheque/<int:id_cheque>', methods=['POST'])
@login_required
@admin_required
def deletar_cheque(id_cheque):
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("DELETE FROM tb_cheques WHERE id = %s", (id_cheque,))
        conexao.commit()
        registrar_log("EXCLUIU CHEQUE", f"Apagou o cheque ID: {id_cheque}")
    conexao.close()
    
    socketio.emit('atualizar_tela')
    return redirect(url_for('cheques'))

@app.route('/editar_cheque/<int:id_cheque>', methods=['POST'])
@login_required
def editar_cheque(id_cheque):
    data_rec = request.form.get('data_recebimento') or None
    cliente = request.form.get('cliente')
    emissor = request.form.get('emissor')
    cnpj_cpf = request.form.get('cnpj_cpf')
    banco = request.form.get('banco')
    numero_cheque = request.form.get('numero_cheque')
    data_bom_para = request.form.get('data_bom_para') or None
    valor = request.form.get('valor')
    destino = request.form.get('destino')
    data_repasse = request.form.get('data_repasse') or None
    observacoes = request.form.get('observacoes')
    info_repasse = request.form.get('info_repasse')

    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = """
            UPDATE tb_cheques 
            SET data_recebimento = %s, cliente = %s, emissor = %s, cnpj_cpf = %s, banco = %s, 
                numero_cheque = %s, data_bom_para = %s, valor = %s, destino = %s, data_repasse = %s, 
                observacoes = %s, info_repasse = %s 
            WHERE id = %s
        """
        cursor.execute(sql, (data_rec, cliente, emissor, cnpj_cpf, banco, numero_cheque, data_bom_para, valor, destino, data_repasse, observacoes, info_repasse, id_cheque))
        conexao.commit()
    conexao.close()
    
    socketio.emit('atualizar_tela')
    return redirect(request.referrer or url_for('cheques'))


# ==========================================
# MÓDULO: MONITORAMENTO E USUÁRIOS
# ==========================================
@app.route('/monitoramento')
@login_required
def monitoramento():
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT * FROM tb_logs_auditoria ORDER BY data_hora DESC LIMIT 100")
        logs = cursor.fetchall()
    conexao.close()
    return render_template('monitoramento.html', logs=logs)

@app.route('/usuarios')
@login_required
@admin_required
def usuarios():
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT id, nome, usuario, senha, nivel FROM tb_usuarios ORDER BY id DESC")
        lista_usuarios = cursor.fetchall()
    conexao.close()
    return render_template('usuarios.html', usuarios=lista_usuarios)

@app.route('/adicionar_usuario', methods=['POST'])
@login_required
@admin_required
def adicionar_usuario():
    nome = request.form.get('nome')
    usuario = request.form.get('usuario')
    senha = request.form.get('senha')
    nivel = request.form.get('nivel')
    
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        sql = "INSERT INTO tb_usuarios (nome, usuario, senha, nivel) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nome, usuario, senha, nivel))
        conexao.commit()
    conexao.close()
    
    registrar_log("CADASTROU USUÁRIO", f"Criou o usuário '{usuario}' com nível '{nivel}'")
    return redirect(url_for('usuarios'))

@app.route('/deletar_usuario/<int:id_usuario>', methods=['POST'])
@login_required
@admin_required
def deletar_usuario(id_usuario):
    if id_usuario == session.get('usuario_id'):
        return "Você não pode excluir seu próprio usuário.", 400
    
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("DELETE FROM tb_usuarios WHERE id = %s", (id_usuario,))
        conexao.commit()
    conexao.close()
    
    registrar_log("EXCLUIU USUÁRIO", f"Removeu o usuário ID: {id_usuario}")
    return redirect(url_for('usuarios'))

@app.route('/alterar_senha', methods=['POST'])
@login_required
def alterar_senha():
    senha_atual = request.form.get('senha_atual')
    nova_senha = request.form.get('nova_senha')
    usuario_id = session.get('usuario_id')
    
    conexao = get_conexao()
    with conexao.cursor() as cursor:
        cursor.execute("SELECT * FROM tb_usuarios WHERE id = %s AND senha = %s", (usuario_id, senha_atual))
        usuario = cursor.fetchone()
        
        if usuario:
            cursor.execute("UPDATE tb_usuarios SET senha = %s WHERE id = %s", (nova_senha, usuario_id))
            conexao.commit()
            sucesso = "Senha alterada com sucesso!"
        else:
            erro = "A senha atual está incorreta."
            
    conexao.close()
    return redirect(request.referrer or url_for('dashboard'))


# ==========================================
# INICIALIZAÇÃO DO SERVIDOR
# ==========================================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)