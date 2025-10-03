import paho.mqtt.client as mqtt
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import time
import oracledb

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "planta_2/usinagem_4/equip-001/dados"

DB_USER = 'RM...'
DB_PASS = 'pass...'
DB_CONNECTION_STRING = oracledb.connect(user=DB_USER, password=DB_PASS, dsn='oracle.fiap.com.br:1521/ORCL')

CSV_DATA_SOURCE = 'dados_teste_para_predicao.csv'
BATCH_SIZE = 10
record_buffer = []

TABELA_LEITURAS = 'T_REPLY_SENSOR_READINGS'

# -----------------------------------------------------------------------------
# Lógica de banco de dados
# -----------------------------------------------------------------------------

engine = create_engine(DB_CONNECTION_STRING)

def flush_buffer_to_db():
    global record_buffer
    if not record_buffer:
        return
    print(f"\n[DB WRITER] Atingido o tamanho do lote. Inserindo {len(record_buffer)} registros no DB...")
    
    sql_insert_query = text(f"""
        INSERT INTO {TABELA_LEITURAS} (
            TIMESTAMP_TMS, DEVICE_ID, TEMPERATURE_VL,
            VIBRATION_VL, CURRENT_VL
        ) VALUES (
            :timestamp, :device_id, :temperature,
            :vibration, :current
        )
    """)
    
    try:
        with engine.connect() as connection:
            connection.execute(sql_insert_query, record_buffer)
            connection.commit()
            print("[DB WRITER] Lote inserido com sucesso.")
    except Exception as e:
        print(f"[DB WRITER] ERRO ao inserir lote no banco: {e}")
    finally:
        record_buffer = []

# -----------------------------------------------------------------------------
# Lógica cliente MQTT
# -----------------------------------------------------------------------------

try:
    df_realista = pd.read_csv(CSV_DATA_SOURCE)
    csv_row_index = 0
    print(f"Dados realistas do arquivo '{CSV_DATA_SOURCE}' carregados...")
except FileNotFoundError:
    print(f"ERRO: Arquivo de dados '{CSV_DATA_SOURCE}' não encontrado. Encerrando.")
    exit()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT LISTENER] Conectado! Ouvindo o tópico '{MQTT_TOPIC}'...")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[MQTT LISTENER] Falha ao conectar, código: {rc}")

def on_message(client, userdata, msg):
    global csv_row_index, record_buffer
    print(f"\n[MQTT LISTENER] Mensagem recebida do Wokwi! (Usando como gatilho)")

    if csv_row_index >= len(df_realista):
        print("[SIMULATOR] Fim dos dados da simulação.")
        return

    linha_realista = df_realista.iloc[csv_row_index]
    
    record_data = {
        'timestamp': pd.to_datetime(linha_realista['timestamp']),
        'device_id': linha_realista['device_id'],
        'temperature': linha_realista['temperature_c'],
        'vibration': linha_realista['vibration_magnitude_mss'],
        'current': linha_realista['current_amps']
    }
    
    record_buffer.append(record_data)
    print(f"[BUFFER] Registro de {record_data['device_id']} adicionado. Buffer: {len(record_buffer)}/{BATCH_SIZE}")
    
    csv_row_index += 1

    if len(record_buffer) >= BATCH_SIZE:
        flush_buffer_to_db()

if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"ERRO CRÍTICO ao conectar ao MQTT: {e}")
    finally:
        flush_buffer_to_db()
        print("Script encerrado.")