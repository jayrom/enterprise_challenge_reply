#include <WiFi.h>
#include <PubSubClient.h> // Biblioteca para MQTT
#include <Wire.h>         // Biblioteca para I2C (MPU6050)
#include <Adafruit_MPU6050.h> // Biblioteca para MPU6050
#include <Adafruit_Sensor.h>  // Dependência da biblioteca MPU6050


// DS18B20
#include <OneWire.h>
#include <DallasTemperature.h>

// Wi-Fi
const char* ssid = "Wokwi-GUEST"; // Nome da rede Wi-Fi no Wokwi
const char* password = "";        // Senha (não tem senha)

// MQTT
const char* mqtt_broker = "broker.hivemq.com"; // Broker MQTT
const int mqtt_port = 1883; // Porta padrão MQTT
const char* mqtt_client_id = "reply-equip-001"; // ID único para o cliente MQTT

// Tópico MQTT para envio de dados
const char* mqtt_topic = "planta_2/usinagem_4/equip-001/dados";

// Pinos dos sensores
#define MPU6050_SDA_PIN 21
#define MPU6050_SCL_PIN 22
#define DS18B20_DQ_PIN  4
#define POT_CURRENT_PIN 35

// Objetos de sensores ---
Adafruit_MPU6050 mpu; // MPU6050
OneWire oneWire(DS18B20_DQ_PIN); // OneWire
DallasTemperature sensors(&oneWire); // DallasTemperature / DS18B20

// Objetos de rede
WiFiClient espClient; // Cliente Wi-Fi
PubSubClient mqttClient(espClient); // Cliente MQTT

// Temporização
unsigned long lastSensorReadMillis = 0;
const long sensorReadInterval = 1000; // Frequência de leitura

// Conexão
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando-se a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Tentando conexão MQTT...");
	
    // Tenta conectar
    if (mqttClient.connect(mqtt_client_id)) {
      Serial.println("conectado!");
    } else {
      Serial.print("falhou, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000); // Espera 5s para tentar novamente
    }
  }
}

// Leitura dos sensores

// MPU6050
sensors_event_t a, g, temp;
void readMPU6050() {
  mpu.getEvent(&a, &g, &temp);
}

// DS18B20
float readDS18B20() {
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);
  return tempC;
}

// Potenciômetro (corrente)
float readPotCurrent() {
  int rawValue = analogRead(POT_CURRENT_PIN);
  // Mapeando leituras para valores reais de corrente: 0V = -5A, 3.3V = +5A
  float current = map(rawValue, 0, 4095, -500, 500) / 100.0;
  return current;
}

// Setup inicial
void setup() {
  Serial.begin(115200);

  // Wi-Fi
  setup_wifi();

  // MQTT
  mqttClient.setServer(mqtt_broker, mqtt_port);

  // Inicializa MPU6050
  Wire.begin(MPU6050_SDA_PIN, MPU6050_SCL_PIN);
  if (!mpu.begin()) {
    Serial.println("Falha ao encontrar MPU6050");
    while (1) delay(10);
  }
  Serial.println("MPU6050 encontrado!");
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G); // Ajustaremos se necessário
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);     // Ajustaremos se necessário
  mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);   // Ajustaremos se necessário

  // Inicializa DS18B20
  sensors.begin();
  Serial.println("DS18B20 encontrado!");
}

// Loop principal
void loop() {
  // Garante que o cliente MQTT está conectado
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop(); // Mantém a conexão MQTT e processa mensagens

  // Temporizador para leituras
  if (millis() - lastSensorReadMillis >= sensorReadInterval) {
    lastSensorReadMillis = millis();

    Serial.println("--- Coletando e enviando dados ---");

    // Leitura dos sensores ---
    readMPU6050(); // Dados estarão nas variáveis globais a, g, temp
    float tempC = readDS18B20();
    float currentData = readPotCurrent();

    // Formata o payload JSON
    String payload = "{";
      payload += "\"timestamp\": " + String(millis()) + ",";
      payload += "\"deviceId\": \"" + String(mqtt_client_id) + "\",";
      payload += "\"sensors\": {";
      payload += "\"vibration\": {";
      payload += "\"accel_x\": " + String(a.acceleration.x, 2) + ",";
      payload += "\"accel_y\": " + String(a.acceleration.y, 2) + ",";
      payload += "\"accel_z\": " + String(a.acceleration.z, 2);
      payload += "},";
      payload += "\"temperature\": {";
      payload += "\"value_celsius\": " + String(tempC, 2);
      payload += "},"; 
      payload += "\"current_voltage\": {";
      payload += "\"current_amps\": " + String(currentData, 2);
      payload += "}";
      payload += "}";
      payload += "}";

    Serial.println(payload); // Imprime o payload no Serial Monitor

        // --- Envio MQTT ---
    if (mqttClient.publish(mqtt_topic, payload.c_str())) {
      Serial.println("Mensagem MQTT publicada com sucesso!");
    } else {
      Serial.println("Falha ao publicar mensagem MQTT.");
    }
  }
}