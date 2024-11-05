import serial
import time
import numpy as np

# import matplotlib
# import matplotlib.pyplot as plt
# import keyboard
import struct
# from pylab import *


def read_i16(f):
    return struct.unpack("<h", bytearray(f.read(2)))[0]


def read_i32(f):
    return struct.unpack("<l", bytearray(f.read(4)))[0]


def write_i16(f, value):
    f.write(struct.pack("<h", value))


def write_i32(f, value):
    f.write(struct.pack("<l", value))


############################################
# Fonction de dialogue direct avec l'arduino
#############################################


def DialArduino():
    while True:
        print("")
        print("Dialogue direct avec l'arduino")
        cma = input("Tapez votre commande arduino (Q pour finir) ")
        if cma == "Q":
            break
        if cma != "":
            arduino.write(cma.encode("utf-8"))
            time.sleep(0.01)
            rep = arduino.readline()  # on lit le message de réponse
            while rep == b"":  # On attend d'avoir une vraie réponse
                rep = arduino.readline()  # on lit le message de réponse
            # print(rep)
            print(rep.decode())
            while (
                arduino.inWaiting() > 0
            ):  # tant qu'on a des messages dans le buffer de retour
                rep = arduino.readline()  # on lit le message de réponse
                print(rep.decode())


def AttAcquit():
    rep = b""
    while rep == b"":  # attend l'acquitement du B2
        rep = arduino.readline()
    # print(rep.decode())


############################################
# Programme principal
############################################

############################################################
# initialisation de la liaison série connection à l'arduino

arduino = serial.Serial(port="/dev/ttyACM0", baudrate=115200, timeout=0.1)
print("Connection à l'arduino")
time.sleep(2)  # on attend 2s pour que la carte soit initialisée

arduino.write(b"A20")  # demande de connection avec acquitement complet en ascii
rep = arduino.readline()
if len(rep.split()) > 0:
    if rep.split()[0] == b"OK":
        print(rep.decode())
        DialArduino()


#######################################
#   deconnection de l'arduino

arduino.write(b"a")  # deconnection de la carte
arduino.close()  # fermeture de la liaison série
print("Fin de programme")
