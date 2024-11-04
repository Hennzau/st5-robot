#include <Servo.h>
Servo frontServo, backServo;    // create servo objects
#define  frontPin 9
#define  backPin 8
int pos = 90;    // initial position of the servos
int minPosF = 20;    // lower bound on the front servo angle
int maxPosF = 160;    // upper bound
int minPosB = 0;    // lower bound on the back servo angle
int maxPosB = 180;    // upper bound
char rx_byte = 0;
String rx_str = "";
bool frontIsActive = true;

void setup() {
  frontServo.attach(frontPin);
  frontServo.write(pos);
  backServo.attach(backPin);
  backServo.write(pos);
  Serial.begin(9600);
}


void loop() {
  if (Serial.available() > 0) {    // is a character available?
    rx_byte = Serial.read();       // get the character
    
    if (rx_byte == 'f') {
      frontIsActive = true;
      rx_str = "";                // clear the string for reuse
    } else if (rx_byte == 'b') {
      frontIsActive = false;
      rx_str = "";                // clear the string for reuse
    } else if ((rx_byte >= '0') && (rx_byte <= '9')) {
      rx_str += rx_byte;
    }
    else if (rx_byte == '\n') {
      // end of string
      if (frontIsActive) {
        setFrontPos();
      } else {
        setBackPos();
      }
      Serial.println("Enter a new position.");
      rx_str = "";                // clear the string for reuse
    }
  } // end: if (Serial.available() > 0)
}

int setFrontPos(){
  int newPos = rx_str.toInt();
  Serial.print("Front position set to ");
  Serial.print(rx_str);
  if (newPos>maxPosF){
    newPos = maxPosF;
    Serial.print(" adjusted to ");
    Serial.print(newPos);
  } else if (newPos<minPosF){
    newPos = minPosF;
    Serial.print(" adjusted to ");
    Serial.print(newPos);
  }
  Serial.println();
  frontServo.write(newPos);
}

int setBackPos(){
  int newPos = rx_str.toInt();
  Serial.print("Back position set to ");
  Serial.print(rx_str);
  if (newPos>maxPosB){
    newPos = maxPosB;
    Serial.print(" adjusted to ");
    Serial.print(newPos);
  } else if (newPos<minPosB){
    newPos = minPosB;
    Serial.print(" adjusted to ");
    Serial.print(newPos);
  }
  Serial.println();
  backServo.write(newPos);
}
