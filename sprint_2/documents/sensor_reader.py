import paho.mqtt.client as mqtt
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import threading
import time

# --- Configurações do MQTT ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "planta_2/usinagem_4/equip-001/dados" #verificar se o topico está correto
MQTT_CLIENT_ID = "reply-equip-001-python" #verificar se o client_id está correto

# --- Configurações do arquivo CSV ---
CSV_FILENAME = "dado_sensor_esp32.csv" #Alterar nome do arquivo conforme salvo futuramente

# --- Dados em memória para o DataFrame ---
sensor_data_list = []
df = pd.DataFrame() #DF inicial vazio

# --- Lock para thread-safe access aos dados ---
data_lock = threading.Lock()

# --- Função de callback MQTT: Quando a conexão é estabelecida ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao broker MQTT!")
        client.subscribe(MQTT_TOPIC)
        print(f"Assinado ao tópico: {MQTT_TOPIC}")
    else:
        print(f"Falha na conexão, código de retorno: {rc}\n")

# --- Função de callback MQTT: Quando uma mensagem é recebida ---
def on_message(client, userdata, msg):
    print(f"Mensagem recebida no tópico {msg.topic}: {msg.payload.decode()}")
    try:
        # Decodificar a mensagem JSON
        data = json.loads(msg.payload.decode())

        # Adicionar Timestamp local se o sensor não fornecer um Timestamp real
        if 'timestamp' not in data:
            data['timestamp_local'] = datetime.now().isoformat()

        # Adicionar dados à lista com um lock para thread-safe
        with data_lock:
            sensor_data_list.append(data)
            print(f"Dados adicionados. Total de registros: {len(sensor_data_list)}")
    except json.JSONDecodeError:
        print("Erro: Mensagem MQTT não é um JSON válido.")
    except Exception as e:
        print(f"Erro ao processar a mensagem: {e}")

# --- Função para salvar dados no CSV ---
def save_to_csv():
    global df
    print("Iniciando rotina de salvamento de dados no CSV...")
    while True:
        time.sleep(5) # Salva a cada 5 segundos (configurável)
        with data_lock:
            if sensor_data_list:
                # Criar um DataFrame a partir de novos dados
                new_df = pd.DataFrame(sensor_data_list)
                sensor_data_list.clear() #Limpa a lista após processar

                # Conecatar com o DataFrame existente
                df = pd.concat([df, new_df], ignore_index=True)

                # Salvar no CSV
                # Se o arquivo não existir, escreve no cabeçalho. Caso contrário, anexa.
                mode = 'a' if os.path.exists(CSV_FILENAME) else 'w'
                header = not os.path.exists(CSV_FILENAME) # Escreve o cabeçalho apenas na primeira vez

                df.to_csv(CSV_FILENAME, mode=mode, header=header, index=False)
                print(f"Dados salvos em {CSV_FILENAME}. Total de registros: {len(df)}")
            else:
                print("Nenhum dado novo para salvar no CSV.")

# --- Função para plotar os dados ---
def plot_sensor_data():
    global df
    print("Iniciando rotina de plotagem de gráficos...")
    plt.ion() # Modo interativo para atualização de gráficos
    fig, ax = plt.subplots(figsize=(10, 6))

    while True:
        time.sleep(10) # Atualiza a cada 10 segundos (configurável)
        with data_lock:
            if not df.empty:
                # Certificar se a coluna timestamp é do tipo datetime
                # Use o timestamp_local se o ESP32 não enviar o 'timestamp'
                timestamp_col = 'timestamp' if 'timestamp' in df.columns else 'timestamp_local'

                # Converter o timestamp para datetime
                if pd.api.types.is_object_dtype(df([timestamp_col])):
                    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')

                    # Remover linhas com timestamp inválidos se houver erro de conversão
                    df.dropna(subset=[timestamp_col], inplace=True)

                    # Para facilitar a visualização de muitos pontos, podemos pegar os ultimos N registros
                    # Ou plotar tudo se a quantidade não for excessiva

                    # Exemplo de gráfico de linha para testar o DS18B20
                    if 'temp_ds18b20' in df.columns:
                        ax.clear()
                        sns.lineplot(x=timestamp_col, y='temp_ds18b20', data=df.tail(100), ax=ax, marker='o') # Últimos 100 pontos
                        ax.set_title('Temperatura DS18B20 ao longo do tempo')
                        ax.set_xlabel('Tempo')
                        ax.set_ylabel('Temperatura (ºC)')
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        plt.draw()
                        plt.pause(0.1) # Pequena pausa para a UI ser atualizada
                    else:
                        print("Coluna   temp_ds18b20 não encontrada no DataFrame para plotagem.")
                else:
                    print("DataFrame vazio, aguardadno dados para plotar.")

# --- Função Principal ---
def main():
    #1. Conctar/Contactar o MQTT
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Erro ao conectar ao broker MQTT: {e}")
        return
    
    # Iniciar o loop de rede do MQTT em um thread separada
    client_thread = threading.Thread(target=client.loop_forever)
    client_thread.daemon = True # Permite que o Thread termine quando o programa principal termina
    client_thread.start()

    # iniciar a thread para salvar dados no CSV
    csv_saver_thread = threading.Thread(target=save_to_csv)
    csv_saver_thread.daemon = True
    csv_saver_thread.start()

    # Iniciar a thread para plotar o gráfico
    plotter_thread = threading.Thread(target=plot_sensor_data)
    plotter_thread.daemon = True
    plotter_thread.start()

    print("Sistema Python iniciado. Aguardando mensagem MQTT...")
    print("Pressione Ctrl+C para sair.")

    try:
        # O programa principal pode ficar ativo aqui ou realizar outras tarefas
        # Por exemplo, manter um loop infinito
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nPrograma encerrado pelo usuário.")
    finally:
        client.disconnect()
        print("Desconectado do broker MQTT.")

if __name__ == "__main__":
    main()