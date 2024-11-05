class Grille():

    def __init__(self, x=0, y=0):
        self.xmax = 5
        self.ymax = 5
        self.x = x
        self.y = y
        self.orientation = 0

    def position(self):
        return (self.x, self.y)

    def __str__(self):
        return f"Position : {self.position()}\nOrientation : {self.orientation}"

    def droite(self):
        self.orientation -= 90

        if self.orientation == -180:
            self.orientation = 180

    def gauche(self):
        self.orientation += 90

        if self.orientation == 270:
            self.orientation = -90

    def avance(self):
        if self.orientation == 0 and self.x < self.xmax-1:
            self.x += 1
        elif self.orientation == 90 and self.y < self.ymax-1:
            self.y += 1
        elif self.orientation == -90 and self.y > 0:
            self.y -= 1
        elif self.orientation == 180 and self.x > 0:
            self.x -= 1
        else:
            pass

    def arriere(self):
        if self.orientation == 0 and self.x > 0:
            self.x -= 1
        elif self.orientation == 90 and self.y > 0:
            self.y -= 1
        elif self.orientation == -90 and self.y < self.ymax-1:
            self.y += 1
        elif self.orientation == 180 and self.x < self.xmax-1:
            self.x += 1
        else:
            pass

    def avance_toutdroit(self, delta=1):
        # L = [self.position()]
        L = []
        for i in range(delta):
            self.avance()
            L.append("Avance")
            # L.append(self.position())
        return L

    def recule(self, delta=1):
        # L = [self.position()]
        L = []
        for i in range(delta):
            self.arriere()
            # L.append(self.position())
            L.append("Recule")
        return L

    def tourne_gauche(self, delta=1):
        # L = [self.position()]
        L = []
        self.gauche()
        L.append("Gauche")
        for i in range(delta):
            self.avance()
            L.append("Avance")
            # L.append(self.position())
        L.pop()
        return L

    def tourne_droite(self, delta=1):
        # L = [self.position()]
        L = []
        self.droite()
        L.append("Droite")
        for i in range(delta):
            self.avance()
            L.append("Avance")
            # L.append(self.position())
        L.pop()
        return L

    def itineraire(self, xfin=0, yfin=0):
        L = []
        xini, yini = self.position()
        if self.orientation == 90:
            deltax = xfin-xini
            deltay = yfin-yini
        elif self.orientation == -90:
            deltax = xini-xfin
            deltay = yini-yfin
        elif self.orientation == 0:
            deltax = yini-yfin
            deltay = xfin-xini
        else:
            deltax = yfin-yini
            deltay = xini-xfin

        if deltax > 0:
            L += self.tourne_droite(deltax)
            if deltay > 0:
                # L.pop()
                L += self.tourne_gauche(deltay)
            elif deltay < 0:
                # L.pop()
                L += self.tourne_droite(-deltay)
        elif deltax < 0:
            L += self.tourne_gauche(-deltax)
            if deltay > 0:
                # L.pop()
                L += self.tourne_droite(deltay)
            elif deltay < 0:
                # L.pop()
                L += self.tourne_gauche(-deltay)
        else:
            if deltay > 0:
                L += self.avance_toutdroit(deltay)
            elif deltay < 0:
                L += self.recule(-deltay)

        return L
