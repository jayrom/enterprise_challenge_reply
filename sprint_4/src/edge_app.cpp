
// ------------------------------------------------------------------------------------
// Esta é uma reprodução simples do arquivo sprint_4/sensors_wokwi/sketch.ino
// para fins de referência apenas. Para código atualizado, consulte o arquivo original.
// ------------------------------------------------------------------------------------

#include <WiFi.h>
#include <PubSubClient.h>      // Biblioteca MQTT
#include <Wire.h>              // Biblioteca I2C (MPU6050)
#include <Adafruit_MPU6050.h>  // Biblioteca MPU6050
#include <Adafruit_Sensor.h>   // Dependência MPU6050
#include <OneWire.h>           // Biblioteca DS18B20
#include <DallasTemperature.h> // Biblioteca DS18B20
#include <ArduinoJson.h>       // Biblioteca JSON

// CONFIGURAÇÕES DE REDE
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// CONFIGURAÇÕES MQTT
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_client_id = "reply-equip-001";
const char* mqtt_topic = "planta_2/usinagem_4/equip-001/dados";

// PINOS DOS SENSORES
#define MPU6050_SDA_PIN 21
#define MPU6050_SCL_PIN 22
#define DS18B20_DQ_PIN 4
#define POT_CURRENT_PIN 35

// OBJETOS DE SENSORES
Adafruit_MPU6050 mpu;
OneWire oneWire(DS18B20_DQ_PIN);
DallasTemperature sensors(&oneWire);

// OBJETOS DE REDE
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// CONTROLE DE TEMPO E AGREGAÇÃO
// Para simulação, usamos intervalos menores. Para a realidade, os valores devem ser ajustados.
// Ex: INTERVALO_ENVIO_MQTT = 600000; (10 minutos)
// Ex: INTERVALO_CRIACAO_REGISTRO = 60000; (1 minuto)
const unsigned long INTERVALO_LEITURA_SENSORES = 2000;   // Lê sensores a cada 2 segundos
const unsigned long INTERVALO_CRIACAO_REGISTRO = 30000;  // Cria registro a cada 30 segundos
const unsigned long INTERVALO_ENVIO_MQTT = 120000;       // Envia pacote a cada 2 minutos

unsigned long ultimo_envio_mqtt = 0;
unsigned long ultima_criacao_registro = 0;
unsigned long ultima_leitura_sensor = 0;

// Armazenar apenas a ÚLTIMA leitura de cada sensor no intervalo
float ultima_leitura_temperatura = 0.0;
float ultima_leitura_vibracao = 0.0;
float ultima_leitura_corrente = 0.0;
bool houve_leitura_no_intervalo = false;

// Documento JSON para payload
JsonDocument doc_pacote;
JsonArray records;
// =====================================================================================

// FUNÇÕES DE CONEXÃO
void setup_wifi() {
  delay(10);
  Serial.println("\nConectando-se a " + String(ssid));
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado! IP: " + WiFi.localIP().toString());
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Tentando conexão MQTT...");
    if (mqttClient.connect(mqtt_client_id)) {
      Serial.println("Conectado!");
    } else {
      Serial.print("Falhou, rc=" + String(mqttClient.state()) + ". Tentando novamente em 5s.");
      delay(5000);
    }
  }
}

// LÓGICA DE LEITURA, AGREGAÇÃO E ENVIO

// Lê os sensores e guarda apenas a última leitura
void ler_e_salvar_ultima_leitura() {
  sensors_event_t a, g, temp_mpu;
  
  // Leitura dos sensores
  mpu.getEvent(&a, &g, &temp_mpu);
  sensors.requestTemperatures();
  float temp_ds18b20 = sensors.getTempCByIndex(0);
  int rawValue = analogRead(POT_CURRENT_PIN);
  float current = map(rawValue, 0, 4095, -500, 500) / 100.0;

  // CÁLCULO DA MAGNITUDE VETORIAL DA VIBRAÇÃO
  // Combina os 3 eixos (X, Y, Z) em um único valor que representa a vibração total
  float vibracao_total = sqrt(pow(a.acceleration.x, 2) + pow(a.acceleration.y, 2) + pow(a.acceleration.z, 2));

  // Atualiza variáveis globais com os valores lidos
  ultima_leitura_temperatura = temp_ds18b20;
  ultima_leitura_vibracao = vibracao_total;
  ultima_leitura_corrente = current;
  
  houve_leitura_no_intervalo = true; // Marca que uma leitura foi feita
  Serial.printf("Leitura atualizada: Temp=%.2f C, Vibr=%.2f m/s^2, Corr=%.2f A\n", ultima_leitura_temperatura, ultima_leitura_vibracao, ultima_leitura_corrente);
  Serial.printf("%.2f,%.2f,%.2f\n", ultima_leitura_temperatura, ultima_leitura_vibracao, ultima_leitura_corrente);
}

// Cria registro no pacote JSON usando a última leitura salva
void criar_registro_do_intervalo() {
  Serial.println("-------------------------------------------------------------------");
  Serial.println("Criando registro com a última leitura do intervalo...");

  if (!houve_leitura_no_intervalo) {
    Serial.println("Nenhuma leitura feita neste intervalo. Pulando.");
    return;
  }
  
  JsonObject record = records.add<JsonObject>();
  record["timestamp"] = millis();
  
  record["temperatura_avg"] = ultima_leitura_temperatura;
  record["vibracao_avg"] = ultima_leitura_vibracao;
  record["corrente_avg"] = ultima_leitura_corrente;

  Serial.println("Registro criado e adicionado ao pacote.");
  houve_leitura_no_intervalo = false;
}

// Envia pacote completo via MQTT
void enviar_pacote_mqtt() {
  if (records.size() == 0) {
    return; // Não faz nada se não houver dados
  }

  Serial.println("-------------------------------------------------------------------");
  Serial.println("Preparando para enviar pacote de dados via MQTT...");

  doc_pacote["deviceId"] = mqtt_client_id;
  
  String payload;
  serializeJson(doc_pacote, payload); // Converte o objeto JSON para String de forma segura

  Serial.println("Payload a ser enviado:");
  Serial.println(payload);

  if (mqttClient.publish(mqtt_topic, payload.c_str())) {
    Serial.println("Pacote MQTT publicado com sucesso!");
  } else {
    Serial.println("Falha ao publicar pacote MQTT.");
  }

  records.clear(); // Limpa o pacote para o próximo ciclo
}

// SETUP E LOOP PRINCIPAL

void setup() {
  Serial.begin(115200);

  // Wi-Fi e MQTT
  setup_wifi();
  mqttClient.setServer(mqtt_broker, mqtt_port);

  // Inicializa MPU6050
  Wire.begin(MPU6050_SDA_PIN, MPU6050_SCL_PIN);
  if (!mpu.begin()) {
    Serial.println("Falha ao encontrar MPU6050");
    while (1) delay(10);
  }
  Serial.println("MPU6050 encontrado!");
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);

  // Inicializa DS18B20
  sensors.begin();
  Serial.println("DS18B20 encontrado!");

  // Inicializa array JSON para registros do pacote
  records = doc_pacote["records"].to<JsonArray>();
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  unsigned long agora = millis();

  // Lê os sensores a cada 2 segundos e guarda a última leitura
  if (agora - ultima_leitura_sensor >= INTERVALO_LEITURA_SENSORES) {
    ultima_leitura_sensor = agora;
    ler_e_salvar_ultima_leitura();
  }

  // A cada 30 segundos, cria um registro com a última leitura
  if (agora - ultima_criacao_registro >= INTERVALO_CRIACAO_REGISTRO) {
    ultima_criacao_registro = agora;
    criar_registro_do_intervalo();
  }

  // A cada 2 minutos, envia o pacote de registros
  if (agora - ultimo_envio_mqtt >= INTERVALO_ENVIO_MQTT) {
    ultimo_envio_mqtt = agora;
    enviar_pacote_mqtt();
  }
}