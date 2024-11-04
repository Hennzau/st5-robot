import serial 
import time
import numpy as np
import struct


def read_i16(f):
    return struct.unpack('<h', bytearray(f.read(2)))[0]

def read_i32(f):
    return struct.unpack('<l', bytearray(f.read(4)))[0]

def write_i16(f, value):
    f.write(struct.pack('<h', value))

def write_i32(f, value):
    f.write(struct.pack('<l', value))

def envoiCmdi(cmd,arg1,arg2,arg3,arg4):
    arduino.write(cmd)
    write_i16(arduino, arg1)
    write_i16(arduino, arg2)
    write_i16(arduino, arg3)
    write_i16(arduino, arg4)
    AttAcquit()

def envoiCmdl(cmd,arg1,arg2):
    arduino.write(cmd)
    write_i32(arduino, arg1)
    write_i32(arduino, arg2)
    AttAcquit()

def recupCmdi(cmd):
    arduino.write(cmd)
    val1=read_i16(arduino)
    val2=read_i16(arduino)
    val3=read_i16(arduino)
    val4=read_i16(arduino)
    return val1,val2,val3,val4
    AttAcquit()

def recupCmdl(cmd):
    arduino.write(cmd)
    val1=read_i32(arduino)
    val2=read_i32(arduino)
    return val1,val2
    AttAcquit()


def AttAcquit():
    rep=b''
    while rep==b'':					# attend l'acquitement du B2
        rep=arduino.readline()
    print(rep.decode())

def    resetENC():
    envoiCmdi(b'B',0,0,0,0)

def    carStop():
    envoiCmdi(b'C',0,0,0,0)

def    carStopS():
    envoiCmdi(b'D',0,0,20,0)

def    carAdvance(v1,v2):
    envoiCmdi(b'C',v1,v2,0,0)

def  carAdvanceS(v1,v2,v3):
    envoiCmdi(b'D',v1,v2,v3,0)

def  carBack(v1,v2):
    envoiCmdi(b'C',-v1,-v2,0,0)

def  carBackS(v1,v2,v3):
    envoiCmdi(b'D',-v1,-v2,v3,0)

def  carTurnLeft(v1,v2):
    envoiCmdi(b'C',v1,-v2,0,0)

def  carTurnRight(v1,v2):
    envoiCmdi(b'C',-v1,v2,0,0)   
    
def TestMoteur():
    
    steptime = 2 			# durée de chaque étape
    
    if (1==1):
        print("le vehicule avance")
        carAdvance(150,150)
        time.sleep(1*steptime)
        carStop()
        time.sleep(1)
        
    if (1==1):
        print(" le vehicule recule")
        carBack(150,150)
        time.sleep(steptime)
        carStop()
        time.sleep(1)
    
    if (1==1):
        print(" le vehicule tourne à gauche")
        carTurnLeft(120,120)
        time.sleep(steptime)
        carStop()
        time.sleep(1)
        
        print(" le vehicule tourne à droite")
        carTurnRight(120,120)
        time.sleep(steptime)
        carStop()
        time.sleep(1)
        
    if (1==1):

        print("le vehicule avance progressivement")
        carAdvanceS(200,200,20)
        time.sleep(3*steptime)
        carStop()
        time.sleep(1)
        
    if (1==1):
        print(" le vehicule recule progressivement")
        carBackS(200,200,20)
        time.sleep(3*steptime)
        carStop()
        time.sleep(1)
        
    if (1==1):
        print("Remise à 0 des encodeurs de position")        
        resetENC()
        print("Test du capteur IR")
        arduino.write(b'I1')
        AttAcquit()
        print("Le vehicule démarre")
        carAdvance(180,180)
        
        vit1=1
        vit2=1
        while ((vit1!=0) or (vit2!=0)):
            time.sleep(0.5)
            tim,tim2,ir,dum1 = recupCmdi(b'R')
            enc1,enc2 = recupCmdl(b'N') 
            print(enc1,enc2,ir) ;
            vit1,vit2,dum1,dum2 = recupCmdi(b'T')
        print("Un obstacle a été détecté")


############################################
# Programme principal
############################################

############################################################
# initialisation de la liaison série connection à l'arduino

arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=0.1)

rep=' '   # on vide la liaison série
while rep!=b'':
  rep = arduino.readline()
print ("Connection à l'arduino")

time.sleep(2)			# on attend 2s pour que la carte soit initialisée

arduino.write(b'A22')		# demande de connection avec acquitement par OK
rep = arduino.readline()
if rep.split()[0]==b'OK':
    arduino.write(b'I0')
    AttAcquit()
    print(rep.decode()) 
    TestMoteur()
  
#######################################
#   deconnection de l'arduino

arduino.write(b'a')	# deconnection de la carte
arduino.close()         # fermeture de la liaison série
print ("Fin de programme")