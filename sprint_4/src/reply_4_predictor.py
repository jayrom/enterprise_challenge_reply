import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sqlalchemy import create_engine, text
import oracledb

# -----------------------------------------------------------------------------
# 1. Configuração
# -----------------------------------------------------------------------------

# Banco de dados
DB_USER = 'RM...'
DB_PASS = 'pass...'
DB_CONNECTION_STRING = oracledb.connect(user=DB_USER, password=DB_PASS, dsn='oracle.fiap.com.br:1521/ORCL')

# Tabelas
TABELA_LEITURAS = 'T_REPLY_SENSOR_READINGS'
TABELA_PREDICOES = 'T_REPLY_MODEL_PREDICTIONS'

# Modelo e artefatos de ML
PATH_MODELO_REGRESSAO = 'random_forest_regressor_model.joblib'
PATH_MODELO_CLASSIFICACAO = 'svm_model.joblib'
PATH_SCALER = 'scaler.joblib'
PATH_LABEL_ENCODER = 'label_encoder.joblib'

# Features
FEATURES_TREINAMENTO = [
    'temperature_c', 'current_amps', 'vibration_magnitude_mss', 'device_motor_B',
    'hora_sin', 'hora_cos', 'dia_semana_sin', 'dia_semana_cos'
]

# -----------------------------------------------------------------------------
# 2. Funções de acesso ao banco e pré-processamento
# -----------------------------------------------------------------------------

engine = create_engine(DB_CONNECTION_STRING)

def buscar_leituras_nao_processadas():
    print("Buscando novas leituras não processadas...")
    sql_query = text(f"""
        SELECT *
        FROM {TABELA_LEITURAS}
        WHERE READING_ID NOT IN (SELECT SENSOR_READING_ID FROM {TABELA_PREDICOES} WHERE SENSOR_READING_ID IS NOT NULL)
    """)
    with engine.connect() as connection:
        df_novas_leituras = pd.read_sql(sql_query, connection)
    if not df_novas_leituras.empty:
        df_novas_leituras.columns = [col.lower() for col in df_novas_leituras.columns]
    print(f"Encontrado(s) {len(df_novas_leituras)} novo(s) registro(s) para processar.")
    return df_novas_leituras

def preprocessar_dados(df):
    print("Aplicando pré-processamento e engenharia de features...")
    df.rename(columns={
        'timestamp_tms': 'timestamp', 'temperature_vl': 'temperature_c',
        'current_vl': 'current_amps', 'vibration_vl': 'vibration_magnitude_mss'
    }, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hora_do_dia'] = df['timestamp'].dt.hour
    df['dia_da_semana'] = df['timestamp'].dt.dayofweek
    df['hora_sin'] = np.sin(2 * np.pi * df['hora_do_dia'] / 24.0)
    df['hora_cos'] = np.cos(2 * np.pi * df['hora_do_dia'] / 24.0)
    df['dia_semana_sin'] = np.sin(2 * np.pi * df['dia_da_semana'] / 7.0)
    df['dia_semana_cos'] = np.cos(2 * np.pi * df['dia_da_semana'] / 7.0)
    df_encoded = pd.get_dummies(df, columns=['device_id'], prefix='device')
    for col in FEATURES_TREINAMENTO:
        if col not in df_encoded.columns:
            df_encoded[col] = 0
    return df_encoded[FEATURES_TREINAMENTO]

def salvar_predicoes(predicoes_a_salvar):
    if predicoes_a_salvar.empty:
        return
    print(f"Salvando {len(predicoes_a_salvar)} novas predições no banco...")
    try:
        predicoes_a_salvar.to_sql(TABELA_PREDICOES, engine, if_exists='append', index=False)
        print("Predições salvas com sucesso.")
    except Exception as e:
        print(f"ERRO ao salvar predições: {e}")

# -----------------------------------------------------------------------------
# 3. Motor de ponderação de regras de negócio
# -----------------------------------------------------------------------------

def aplicar_regras_de_negocio(df_pred):
    print("Aplicando motor ponderação para validar predições...")
    
    LIMITE_DIAS_CRITICO = 2.0
    LIMITE_DIAS_ATENCAO = 7.0
    
    # Condições, em ordem de prioridade
    conditions = [

        # REGRA 1: incongruência de urgência (Classificado como normal, mas falha iminente)
        (df_pred['PREDICTED_FAILURE_MODE'] == 'normal') & (df_pred['PREDICTED_DAYS_TO_FAILURE'] < LIMITE_DIAS_ATENCAO),

        # REGRA 2: falha consistente e crítica
        (df_pred['PREDICTED_FAILURE_MODE'] != 'normal') & (df_pred['PREDICTED_DAYS_TO_FAILURE'] < LIMITE_DIAS_CRITICO),

        # REGRA 3: Falha consistente, mas não urgente
        (df_pred['PREDICTED_FAILURE_MODE'] != 'normal')
    ]
    
    # Níveis de alerta correspondentes
    choices_alert = ['Critico', 'Critico', 'Atencao']
    
    # Aplica as regras para definir o nível de alerta final
    df_pred['EVALUATION_STATUS'] = np.select(conditions, choices_alert, default='Normal')
    
    return df_pred

# -----------------------------------------------------------------------------
# 4. Lógica central
# -----------------------------------------------------------------------------

def executar_ciclo_de_predicao():
    # 1. Buscar dados novos
    df_novas_leituras = buscar_leituras_nao_processadas()
    if df_novas_leituras.empty:
        print("Nenhuma leitura nova para processar. Encerrando.")
        return

    # 2. Carregar modelos
    model_reg = joblib.load(PATH_MODELO_REGRESSAO)
    model_class = joblib.load(PATH_MODELO_CLASSIFICACAO)
    scaler = joblib.load(PATH_SCALER)
    le = joblib.load(PATH_LABEL_ENCODER)

    # 3. Pré-processar
    X_processed = preprocessar_dados(df_novas_leituras.copy())
    X_scaled = scaler.transform(X_processed)

    # 4. Fazer predições brutas
    pred_days = model_reg.predict(X_scaled)
    pred_class_labels = le.inverse_transform(model_class.predict(X_scaled))
    
    # 5. Montar um DataFrame com as predições brutas
    df_resultados_brutos = pd.DataFrame({
        'SENSOR_READING_ID': df_novas_leituras['reading_id'],
        'TIMESTAMP': datetime.now(),
        'DEVICE_ID': df_novas_leituras['device_id'],
        'PREDICTED_DAYS_TO_FAILURE': np.round(pred_days, 2),
        'PREDICTED_FAILURE_MODE': pred_class_labels
    })

    # 6. Aplicar o motor de ponderação para validar e definir o status final
    df_validados = aplicar_regras_de_negocio(df_resultados_brutos)

    # 7. Imprimir os alertas
    alertas = df_validados[df_validados['EVALUATION_STATUS'] != 'Normal']
    if not alertas.empty:
        print("\n!!!!!!!! ALERTA DE MONITORAMENTO DETECTADO !!!!!!!!")
        for _, row in alertas.iterrows(): # Usamos _ para ignorar o index
            status_final = row['PREDICTED_FAILURE_MODE']
            # Se a predição for incongruente, o status final reflete isso
            if (row['EVALUATION_STATUS'] == 'Critico') and (row['PREDICTED_FAILURE_MODE'] == 'normal'):
                status_final = "Incongruente: Risco Iminente"

            print(f"  - [NÍVEL: {row['EVALUATION_STATUS'].upper()}] Device: {row['DEVICE_ID']}")
            print(f"    Status Final: '{status_final}' (Dias restantes: {row['PREDICTED_DAYS_TO_FAILURE']})")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    
    # 8. Salvar o DataFrame validado no banco
    salvar_predicoes(df_validados)

if __name__ == "__main__":
    executar_ciclo_de_predicao()