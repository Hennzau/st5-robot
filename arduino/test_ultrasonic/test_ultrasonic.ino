#include <Servo.h>
#include <Chrono.h>
Chrono measureDistance_chrono; // measure distance every 200ms
Chrono sweepServo_chrono; // change servo angle every 50 ms

unsigned long distanceInCm = 0;

Servo myservo;    // create servo object to control a servo
#define  servoPin 9    // pin number of the servo
int pos = 90;    // initial position of the servo
bool doSweep = true;    // optional rotation of the servo
int minPos = 60;    // lower bound on the position angle
int maxPos = 120;    // upper bound
bool clockwise = false;    // initial direction of the servo rotation

#define  URPWM 11    // URM PWM Output 0－25000US，Every 50US represent 1cm
#define  URTRIG 10    // URM trigger pin
uint8_t EnPwmCmd[4]={0x44,0x02,0xbb,0x01};    // distance measure command


void setup(){
  myservo.attach(servoPin);
  myservo.write(pos);
  Serial.begin(9600);       // Sets the baud rate to 9600
  SensorSetup();
}


void loop(){
  if( measureDistance_chrono.hasPassed(200) ){
    distanceInCm = MeasureDistance();
    Serial.println();
    if(distanceInCm>900){             // the reading is invalid.
      Serial.println("Invalid");
    }else{
      Serial.println(distanceInCm);
    }
  }
  
  if(doSweep){
    if( sweepServo_chrono.hasPassed(50) ){
      servoSweep();
      Serial.print('S');
    }
  }
}


void SensorSetup(){
  pinMode(URTRIG,OUTPUT);          // A low pull on pin COMP/TRIG
  digitalWrite(URTRIG,HIGH);       // Set to HIGH
  pinMode(URPWM, INPUT);           // Sending Enable PWM mode command
  for(int i=0; i<4; i++){
    Serial.write(EnPwmCmd[i]);
  }
}


int MeasureDistance(){               // a low pull on pin COMP/TRIG  triggering a sensor reading
  digitalWrite(URTRIG, LOW);
  digitalWrite(URTRIG, HIGH);      // reading Pin PWM will output pulses
  unsigned long distance = pulseIn(URPWM,LOW);
  distance = distance/50;          // every 50us low level stands for 1cm
  return distance;
}


void servoSweep(){
  if(not clockwise){
    if(pos>=minPos && pos<=maxPos){
      pos++;                            // in steps of 1 degree
      myservo.write(pos);               // tell servo to go to position in variable 'pos'
    }
    if(pos>=maxPos)  clockwise = true; // change direction
  }else{
    if(pos>=minPos && pos<=maxPos){
      pos--;
      myservo.write(pos);
    }
    if(pos<=minPos)  clockwise = false;
  }
}
