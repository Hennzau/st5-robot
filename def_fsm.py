def fsm (dist): #dist positive s'il faut aller à droite, négative sinon
    dmin=2 #à changer
    if abs(dist)>dmin:
        if dist<0:
            return "right"
        if dist>0:
            return "left"
    else: 
        return "keep going"