int distanceInCm = 80;

#define infraredPin A0   // pin number of the sensor
float volts = 0;         // sensor analog value


void setup(){
  Serial.begin(9600);       // Sets the baud rate to 9600
}


void loop(){
  volts = analogRead(infraredPin)*5.0/1024.0;  // 10 bits over 5 volts
  Serial.print(volts);
  Serial.print(" V : ");
  distanceInCm = convertMeasure();   // sensor characteristics
  if (distanceInCm<8 && distanceInCm!= 0) {
	Serial.println("Too close!");
  } else if (distanceInCm>80 || distanceInCm== 0) {
	Serial.println("Out of range");
  } else {
    Serial.print(distanceInCm);
    Serial.println(" cm");
  }
  delay(500);
}


int convertMeasure(){               // approximate sensor characteristics
  if (volts<1) {
	distanceInCm = 28.0/volts;
  } else {
	volts -= 0.28;
	distanceInCm = 20.2/volts;
  }
  return distanceInCm;
}
