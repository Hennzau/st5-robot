def conv_infrared (volts):
    if volts<1 : 
        distcm=28.0/volts
    else :
        volts=volts-0.28
        distcm=20.2/volts
    return distcm

