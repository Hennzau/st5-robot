//////////////////////////////////////////////////////-
// Ce programme a été développé à CENTRALESUPELEC
// Merci de conserver ce cartouche
// Copyright  (c) 2024  CENTRALE-SUPELEC   
// Département Electronique et électromagnétisme
// //////////////////////////////////////////////////-
//
// fichier : serial_link.ino
// auteur  : P.BENABES   
// Copyright (c) 2024 CENTRALE-SUPELEC
// Revision: 1.0  Date: 20/08/2024
//
// //////////////////////////////////////////////////-
//
// DESCRIPTION DU SCRIPT :
// programme tournant sur les cartes arduino pour la
// commande des moteurs du robot
//
//////////////////////////////////////////////////////

#include "parameters.h"
#include <Servo.h>
//#include "SR04.h"

#define digitalPinToInterrupt(p)  ((p) == 2 ? 0 : ((p) == 3 ? 1 : -1))

char feedback ;   // si non nul indique que les commandes doivent renvoyer un acquittement

// gestion du multitache. définition de la période de chaque tache
int del1 = 100;  // délai tache 1 de test d'arrivée
int del2 = 500;  // délai regulation moteur
int del3 = 100;   // démarrage progressif des moteurs
int del4 = 100;  // tache de détection des obstacles
int del5 = 200;  // tache de détection des obstacles
int tim1,tim2,tim3,tim4,tim5 ;   // temps du prochain evenement
bool task1on=false ;        // lancement de la tache 1 de test d'arrivée
bool task2on=true ;         // lancement de la tache 2 de calcul de vitesse
bool task3on=false ;        // lancement de la tache 3 d'accélération progressive
bool task4on=false ;        // lancement de la tache 4 de détection de collision par IR
bool task5on=false ;        // lancement de la tache 5 de rotation du servomoteur
bool obst=false ;           // obstacle détecté

char c,CharIn,m;
bool ConnOn ;          // indique si la carte est connectée
int commode=0 ;        // indique le mode de communication 0=tout en ASCII, 1 les commandes sont en binaire et les retours en ascii, 2 tout est en binaire  
char retstring[96] ;   // chaine de retour de commande

// variables de la gestion des moteurs 
long int volatile CountIncr1,CountIncr2 =0 ;  // valeur des compteurs incrémentaux en 32 bits
int nivM1,nivM2 ;         // tension appliquée au moteur
int nivE1,nivE2 ;         // tension de consigne à atteindre pour le démarrage en douceur
int nivM ;                // pointeur sur ces variables
char motA,motB ;          // pointeur sur les moteurs
int vitdem=10 ;              // vitesse de démarrage des moteurs

// variables pour le calcul de la vitesse
long int v1,lv1 ;
long int v2,lv2 ;
long int v3,lv3 ;
int vitesse1,vitesse2 ;

//SR04 sr04 = SR04(ECHO_PIN,TRIG_PIN);  // gestion du capteur ultrasonore
long a;
int v;

// gestion du servomoteur
Servo frontServo ;    // create servo objects
int servopos= 0 ;    // commande de position du servomoteur
int servomin=30 ;     // position min du servomoteur
int servomax=150 ;
int servospeed=10 ;   // vitesse de rotation du servomoteur
int servosens=1 ;      // sens de rotation du servomoteur


///////////////////////////////////////////////////////////////////////////
//   mise en route des taches périodiques
/////////////////////////////////////////////////////////////////////////
inline void Task1On()
{ task1on=true;  tim1 = (int)millis()+del1; }
inline void Task2On()
{ task2on=true;  tim2 = (int)millis()+del2; }
inline void Task3On()
{ task3on=true;  tim3 = (int)millis()+del3; }
inline void Task4On()
{ task4on=true;  tim4 = (int)millis()+del4; }
inline void Task5On()
{ task5on=true;  tim5 = (int)millis()+del5; }

///////////////////////////////////////////////////////////////////////////
//
//   INITIALISATION DE L'ARDUINO
//
/////////////////////////////////////////////////////////////////////////

void dummy() {  Serial.println("ER"); }

void init_arduino() {

// on eteint les moteurs
  nivM1=0 ; nivM2=0 ;     
  set_motor1(nivM1) ;
  set_motor2(nivM2) ;
  
  servomin=30 ;     // position min du servomoteur
  servomax=150 ;
  servopos=(servomin+servomax)/2 ;
  frontServo.write(servopos);
  task5on=false ;
  obst=false ;

  task1on=false ;       
  Task2On() ;    
  task3on=false ;       
  task4on=false ;     
  task5on=false ;     
}

void setup() {
  Serial.begin(SERIAL_BAUD); // vitesse de la liaison série
  Serial.setTimeout(SERIAL_TIMEOUT); // timeout pour attendre une fin de message
  pinMode(motor1PWM, OUTPUT);
  pinMode(motor1SNS, OUTPUT);
  pinMode(motor2PWM, OUTPUT);
  pinMode(motor2SNS, OUTPUT);
  tim1 = (int)millis()+del1;
  tim2 = (int)millis()+del2;
  tim3 = (int)millis()+del3;
  tim4 = (int)millis()+del4;
  tim5 = (int)millis()+del5;
  frontServo.attach(ServofrontPin);

  init_arduino() ;

  attachInterrupt(digitalPinToInterrupt(ENCODER1B), IntIncrem1, FALLING); // attache l'interruption à l'encodeur 1
  attachInterrupt(digitalPinToInterrupt(ENCODER2B), IntIncrem2, FALLING); // attache l'interruption à l'encodeur 2
}

////////////////////////////////////////////////////////////
//
// la boucle principale
//
/////////////////////////////////////////////////////////////


void loop() {
 
  if (Serial.available() > 0) {
    // on lit le premier caractère qui arrive
    CharIn = Serial.read();
    if (CharIn=='A') CONNECT_code();        // demande de connection
    else if (ConnOn)     decod_serial(CharIn);  // on ne fait un decodage de commande que si on est connecté
  }

  // lancement des differentes taches périodiques
  if (task1on) task1() ;   // tache periodique non définie
  if (task2on) task2() ;      // tache de calcul de la vitesse moteur toujours en route
  if (task3on) task3() ;      // tache d'accélération progressive des moteurs
  if (task4on) task4() ;      // tache de détection de collision
  if (task5on) task5() ;      // tache de détection de collision
}



//////////////////////////////////////////////////////////////////////////
//
// LES FONCTIONS DE COMMUNICATION
//
//////////////////////////////////////////////////////////////////////////

// Routine de recuperation d'un caractere
char GetChar(char def)
{   
    if (Serial.available()>0)  // liaison série vide 
      return(Serial.read());
    else
      return(def) ;
}

// routine de récupération d'un nombre entier sur la liaison série
// le codage sera ascii ou binaire selon la variable 'commode'
int GetInt(int def)
{   
    int tmp ;
    if (commode==0) {
      c=Serial.peek() ;
      if (c==' ') {Serial.read(); c=Serial.peek() ;}
      if ((c=='-') || ((c>='0') && (c<='9'))) 
        return(Serial.parseInt()); // on recupere la commande du moteur
      else
        return(def) ; }  // renvoie la valeur par défaut 
    else {
      Serial.readBytes((char*)&tmp,2);
      return(tmp) ;
    }
    
}

// routine de récupération d'un nombre entier long (32 bits) sur la liaison série
// le codage sera ascii ou binaire selon la variable 'commode'
long int GetLong(long def)
{
    long int tmp ;
    if (commode==0) {
      c=Serial.peek() ;
      if (c==' ') {Serial.read(); c=Serial.peek() ;}
      if ((c=='-') || ((c>='0') && (c<='9'))) 
      {
        tmp=Serial.parseInt() ;
        return(tmp); // on recupere la commande du moteur
      }
      else
        return(def) ; }  // renvoie la valeur par défaut
    else {
      Serial.readBytes((char*)&tmp,4);
      return(tmp) ;
    }
}

// bibliothèque de renvoi de valeurs binaires sur la liaison série
inline void write_i8(char num)
{ Serial.write(num); }

void write_i16(int num)
{ Serial.write((uint8_t*)&num, 2); }

void write_i32(long num)
{ Serial.write((uint8_t*)&num, 4); }

/////////////////////////////////////////////////
//  LES FONCTIONS MOTEUR 
////////////////////////////////////////////////

// code de mise en route de moteur
inline void set_motor(char MPWM, char MSNS, char sns, int nivm)
{ if (obst==true) nivm=0 ; // si on n'a pas d'obstcle
    analogWrite(MPWM,abs(nivm));
    digitalWrite(MSNS,sns?(nivm>=0?0:1):(nivm>=0?1:0)) ;
}

inline void set_motor1(int nivm)
{  set_motor(motor1PWM,motor1SNS,0,nivm) ; }
  
inline void set_motor2(int nivm)  
{  set_motor(motor2PWM,motor2SNS,1,nivm) ; }


//////////////////////////////////////////////////////////////////////////////
//
// LES CODES DE TRAITEMENT DES COMMANDES
//
///////////////////////////////////////////////////////////////////////////////


// routine renvoyant le message d'acquitement simple (OK ou OBstacle)
inline void RetAcquitSimpl()
{
    if (feedback==1) 
      if (obst==false) Serial.println("OK"); 
      else Serial.println("OB");
}


// code de connection de la carte
void CONNECT_code() {
  delay(1); // indispensable et pas trop long sinon le caractère suivant n'est pas arrivé
  c=GetChar(0);
  feedback=c-'0' ;
  ConnOn = true ;
  commode= GetChar(0);
  if (commode>0) commode-='0'; else commode=0 ;
  init_arduino() ;

  RetAcquitSimpl();
  if (feedback==2)
  {
    sprintf(retstring,"OK Arduino connecte version 1.0 en mode %d",commode);
    Serial.println(retstring); 
  }  

}

// code de deconnection de la carte
void DISCONNECT_code() {
  init_arduino();
  Serial.println("OK Arduino deconnecte");
  ConnOn = false ;
}


// code de remise à 0 des encodeurs
void RESETENC_code() {
    GetLong(0);
    GetLong(0);
    CountIncr1=0 ;
    CountIncr2=0;
    RetAcquitSimpl();     // acquitement de la commande en mode feedback=1
    if (feedback==2)
        Serial.println("Ok encodeurs de position remis à 0"); 
}

// code pour commander 1 moteur
void SINGLEMOTOR_code() {
  char s ;
  delay(1); // indispensable et pas trop long
  m=GetChar(0);
  if (m=='1') { nivM=nivM1 ; motA=motor1PWM; s=0; motB=motor1SNS; }
  else if (m=='2') { nivM=nivM2 ; motA=motor2PWM; s=1; motB=motor2SNS; }
  if ((m=='1') || (m=='2'))
  { nivM=GetInt(0) ;              // recupere la valeur de la commande
    GetInt(0) ;
    GetLong(0);
    set_motor(motA,motB,s,nivM) ;  // envoie la commande au moteur
    RetAcquitSimpl();     // acquitement de la commande en mode feedback=1
    if (feedback==2)
      if (obst==false)
      {
        sprintf(retstring,"OK Moteur %c mis à la tension : %d",m,nivM);
        Serial.println(retstring); }
      else 
        Serial.println("OB stacle détecté moteur non allumé"); 
  }
  else
  { Serial.readString() ;
    Serial.println("Erreur commande incomplète"); 
  
  }
}

 
// code pour commander les 2 moteurs en même temps
void DUALMOTOR_code() {
  delay(1); // indispensable et pas trop long

  // on recupere les parametres
  nivM1=GetInt(0) ;   // on lit la valeur du premier moteur
  nivM2=GetInt(nivM1) ; // on lit la valeur du deuxième moteur
  GetLong(0);

  // on envoie la commande aux 2 moteurs
  set_motor1(nivM1) ;
  set_motor2(nivM2) ;
  if ((nivM1==1) && (nivM2==0)) task3on=false ;

  //reponse de la commande
  RetAcquitSimpl();
  if (feedback==2)
    if (obst==false)
    { 
      sprintf(retstring,"OK Moteurs mis aux tensions : %d %d",nivM1,nivM2);
      Serial.println(retstring); }
    else 
      Serial.println("OB stacle détecté moteur non allumé"); 
}


// code pour la mise en route progressive des 2 moteurs en même temps
void DUALMOTORSLOW_code() {
  delay(1); // indispensable et pas trop long

  // on recupere les parametres
  nivE1=GetInt(0) ;   // on lit la valeur du premier moteur ;
  nivE2=GetInt(nivE1) ;   // on lit la valeur du deuxième moteur ;
  vitdem=GetInt(25) ;     // on lit la vitesse 
  GetInt(0);
  
  // on lance la tache d'accélération
  if (obst==false) 
    Task3On();

  // réponse de la commande
  RetAcquitSimpl();
  if (feedback==2)
    if (obst==false)
    { 
      sprintf(retstring,"OK Moteurs démarrage progressif : %d %d %d",nivE1,nivE2,vitdem);
      Serial.println(retstring); }
    else 
      Serial.println("OB stacle détecté moteur non allumé"); 
}


// code pour régler la consigne de vitesse pour envoyer les 2 moteurs à une certaine position
void SERVO_code() {
  delay(1); // indispensable et pas trop long
  
  // onn recupere les paramètres 
  servopos=GetInt(0) ;  // on recupere la vitesse pour positionner le moteur
  GetInt(0);
  GetLong(0);
  if (servopos<servomin) servopos=servomin ;
  if (servopos>servomax) servopos=servomax ;
  
  frontServo.write(servopos);
   
  // on renvoie la réponse
  RetAcquitSimpl();
  if (feedback==2)
    {  
       sprintf(retstring,"OK servomoteur en %d",servopos);
       Serial.println(retstring); }
}

// code pour régler la consigne min et max des servomoteurs
void SERVO_minmax() {
  delay(1); // indispensable et pas trop long
  
  // onn recupere les paramètres 
  servomin=GetInt(0) ;  // on recupere la vitesse pour positionner le moteur
  servomax=GetInt(0);
  GetLong(0);
  if (servomin<0) servomin=0 ;
  if (servomax>270) servomax=270 ;
  
  // on renvoie la réponse
  RetAcquitSimpl();
  if (feedback==2)
    {  
       sprintf(retstring,"servomoteur min max = %d %d",servomin, servomax);
       Serial.println(retstring); }
}


// code de mise en route de la protection moteur
// chaque appel à cette commande réinitialise la détection et autorise le redémarrage des moteurs 
void PROTECT_IR_code() {
  delay(1); // indispensable et pas trop long
  m=GetChar(0);
  if (m=='0')   { task4on=false ; obst=false ;   }
  else if (m=='1')  { Task4On() ;  obst=false ; }    
  if (feedback==1) Serial.println("OK");
  if (feedback==2)
  {  Serial.print("OK protection moteur : ");
      Serial.println(task4on);
  }
}


//////////////////////////////////////////////////////////////////////////////
//
// LES CODES DE TRAITEMENT DES QUESTIONS
//
///////////////////////////////////////////////////////////////////////////////

// renvoie la position de 2 encodeurs
void  ENCODER_DUAL_code() {
  v1=CountIncr1; v2=CountIncr2 ;
  if (commode==2)
  {  write_i32(v1); write_i32(v2); }
  else
  {
    Serial.print(v1);
    Serial.print(" ");
    Serial.println(v2); }
}


// renvoie le temps courant et la position d'un encodeur
void  ENCODERS_TIME_code() {
  delay(1); // indispensable et pas trop long sinon le caractère suivant n'est pas arrivé
  c=GetChar(0);
  if (c=='1') 
    v2=CountIncr1; 
  else if (c=='2')
    v2=CountIncr2 ;

  v1=millis() ;
  if (commode==2)
  {  write_i32(v1); write_i32(v2); }
  else
  { Serial.print(v1);
    Serial.print(" ");
    Serial.print(v2);  }
}

// renvoie la vitesse des 2 moteurs
void SPEED_DUAL_code() {
  if (commode==2)
  {  write_i16(vitesse1); write_i16(vitesse2); write_i16(0);  write_i16(0); }
  else
  { Serial.print(vitesse1);
    Serial.print(" ");
    Serial.println(vitesse2); }
}

// renvoie le temps courant et la valeur du capteur infrarouge
void  INFRARED_TIME_code() {
  v1=millis() ;
  if (commode==2)
  {  write_i32(v1); write_i16(analogRead(IR_pin));  write_i16(0);   }
  else
  { 
    Serial.print(v1);
    Serial.print(" ");
    Serial.println(analogRead(IR_pin)); }
}

// renvoie la valeur du capteur ultrasons
void  ULTRASON_code() {
//  a=sr04.Distance();
//  if (commode==2)
//    write_i16(a); 
//  else
//    Serial.println(a);
}

// renvoie la tension sur le moteur
void  VALMOTOR_code() {
  if (commode==2)
  { write_i16(nivM1); 
    write_i16(nivM2);  write_i16(0);  write_i16(0);}
  else
  { Serial.print(nivM1);
    Serial.print(" ");
    Serial.println(nivM2); }
}

/////////////////////////////////////////////////////
// LE BIG TABLEAU D'AIGUILLAGE DES FONCTIONS
/////////////////////////////////////////////////////


void (*UpperFn[20])() = {           // tableau des fonctions pour un code en majuscule
  CONNECT_code,             // A
  RESETENC_code,            // B
  DUALMOTOR_code,           // C
  DUALMOTORSLOW_code,       // D
  dummy,                    // E
  dummy,                    // F
  SERVO_code,               // G
  dummy,                    // H
  PROTECT_IR_code,dummy,dummy,dummy,dummy, // I,J,K,L,M
  ENCODER_DUAL_code,        // N
  ENCODERS_TIME_code,       // O  
  SPEED_DUAL_code,dummy,    // P,Q
  INFRARED_TIME_code,       // R
  ULTRASON_code,            // S
  VALMOTOR_code             // T
  };

void (*LowerFn[20])() = {             // tableau des fonctions pour un code en minuscule
  DISCONNECT_code,          // a
  RESETENC_code,            // b
  SINGLEMOTOR_code,         // c
  DUALMOTORSLOW_code,       // d
  dummy,                    // e
  dummy,SERVO_minmax,dummy, // f,g,h
  PROTECT_IR_code,dummy,dummy,dummy,dummy, // i,J,K,L,M
  ENCODER_DUAL_code,        // n
  ENCODERS_TIME_code,       // o  
  SPEED_DUAL_code,dummy,    // p,q
  INFRARED_TIME_code,       // r
  ULTRASON_code,            // S
  VALMOTOR_code             // T
  };


// fonction de décodage des messages 
inline void decod_serial(char CharIn)
{
    if ((CharIn>='A') && (CharIn<='T'))       // pour les fonctions 'majuscule'
      UpperFn[CharIn-'A']() ;
    else if ((CharIn>='a') && (CharIn<='t'))  // pour les fonctions 'miniscule'
      LowerFn[CharIn-'a']() ;
    else
      dummy();
}


////////////////////////////////////////////////////////////////////
//
// LES TACHES PERIODIQUES
//
////////////////////////////////////////////////////////////////////


// tache libre
inline void task1() {
  if (((int)millis()-tim1)>0)  // si on a atteint le temps programmé
  { 

  // A COMPLETER

    
  tim1=tim1+del1 ;
  }
}

// tache de calcul de la vitesse du moteur
inline void task2() {
  if (((int)millis()-tim2)>0)  // si il s'est passé 1 seconde depuis la dernière lecture
  {

    // A COMPLETER


    tim2=tim2+del2 ;
  }
}

// tache gérant le démarrage (ou l'arret) progressif des moteurs
inline void task3() {
  if (((int)millis()-tim3)>0)  // si il s'est passé 1 seconde depuis la dernière lecture
  {
    if (nivM1 < nivE1)
    {  nivM1 += vitdem ;    // accélération du moteur 1
      if (nivM1> nivE1)        nivM1 = nivE1 ; }
    if (nivM1 > nivE1)
    {  nivM1 -= vitdem ;    // décélération du moteur 1
      if (nivM1 < nivE1)        nivM1 = nivE1 ; }

    if (nivM2 < nivE2)
    {  nivM2 += vitdem ;    // accélération du moteur 1
      if (nivM2> nivE2)        nivM2 = nivE1 ; }
    if (nivM2 > nivE2)
    {  nivM2 -= vitdem ;    // décélération du moteur 1
      if (nivM2 < nivE2)        nivM2 = nivE2 ; }

    set_motor1(nivM1) ;
    set_motor2(nivM2) ;

    if ((nivM1 == nivE1) && (nivM2 == nivE2))
      task3on =false;

    tim3=tim3+del3 ;
  }
}

// tache de détection des obstacles

inline void task4() {
  if (((int)millis()-tim4)>0)  // si on a atteint le temps programmé
  { 
    if (analogRead(IR_pin)>500)     // on a détecté un obstacle
    {
      obst=true ;                   // indique que l'on a détecté un obstacle
      nivM1=0 ; nivM2=0 ;
      set_motor1(0) ;
      set_motor2(0) ;
      task3on = false ;        // arret du démarrage progressif
    }
    tim4=tim4+del4 ;
  }
}

// tache de rotation du servomoteur

inline void task5() {
  if (((int)millis()-tim5)>0)  // si on a atteint le temps programmé
  { 

    // A COMPLETER EVENTUELLEMENT

    tim5=tim5+del5 ;
  }
}

////////////////////////////////////////////////////////////
//
// les routines d'interruption
//
////////////////////////////////////////////////////////////

// interruption du premier codeur incrémental
void IntIncrem1() {                // interruption du décodeur incrémental
  int sns = (digitalRead(ENCODER1A) == LOW) ? +1 : -1 ;     // on détermine le sens de rotation
  CountIncr1 += sns;              // on incrémente le compteur
}

// interruption du deuxième codeur incrémental
void IntIncrem2() {                // interruption du décodeur incrémental
  int sns = (digitalRead(ENCODER2A) == LOW) ? -1 : +1 ;     // on détermine le sens de rotation
  CountIncr2 += sns;              // on incrémente le compteur
}
