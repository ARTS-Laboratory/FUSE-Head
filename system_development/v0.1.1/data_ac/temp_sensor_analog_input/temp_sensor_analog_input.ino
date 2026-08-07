int sensorPin = A0;   // select the input pin for the potentiometer
int sensorValue = 0;  // variable to store the value coming from the sensor
int intercept = -0.44013;
float slope = 0.48252;
int temperature = 0.97875;

void setup() {
  Serial.begin(9600);
}

void loop() {
  sensorValue = analogRead(sensorPin);
  temperature = sensorValue*slope+intercept;
  Serial.println(temperature);
  delay(100);
}