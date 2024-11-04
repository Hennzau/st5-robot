// #
// # Editor     : Lauren from DFRobot
// # Date       : 17.01.2012

// # Product name: Wheel Encoders for DFRobot 3PA and 4WD Rovers
// # Product SKU : SEN0038

// # Description:
// # The sketch for using the encoder on the DFRobot Mobile platform

// # Connection for Uno or other 328-based:
// #        left wheel encoder  -> Digital pin 2
// #        right wheel encoder -> Digital pin 3
// # Note: If your controller is not 328-based, please check https://www.arduino.cc/en/Reference/AttachInterrupt for proper digital pins.


#define LEFT 0
#define RIGHT 1
#define LEFT_B A2
#define RIGHT_B 13

long coder[2] = {
  0,0};
int lastSpeed[2] = {
  0,0};


void setup(){

  Serial.begin(9600);                            //init the Serial port to print the data
  attachInterrupt(LEFT, LwheelSpeed, RISING);    //init the interrupt mode for the digital pin 2
  attachInterrupt(RIGHT, RwheelSpeed, RISING);   //init the interrupt mode for the digital pin 3
  pinMode(LEFT_B, INPUT);
  pinMode(RIGHT_B, INPUT);

}

void loop(){

  static unsigned long timer = 0;                //print manager timer

  if(millis() - timer > 1000){
    Serial.print("Coder value: ");
    Serial.print(coder[LEFT]);
    Serial.print("[Left Wheel] ");
    Serial.print(coder[RIGHT]);
    Serial.println("[Right Wheel]");

    lastSpeed[LEFT] = coder[LEFT];   //record the latest speed value
    lastSpeed[RIGHT] = coder[RIGHT];
    coder[LEFT] = 0;                 //clear the data buffer
    coder[RIGHT] = 0;
    timer = millis();
  }

}


void LwheelSpeed()
{
  if(!digitalRead(LEFT_B)) //counter-clockwise motor rotation
  {
    coder[LEFT] ++;  //count the left wheel encoder interrupts
  }
  else
  {
    coder[LEFT] --;
  }
}


void RwheelSpeed()
{
  if(digitalRead(RIGHT_B)) //clockwise motor rotation
  {
    coder[RIGHT] ++;  //count the right wheel encoder interrupts
  }
  else
  {
    coder[RIGHT] --;
  }
}
