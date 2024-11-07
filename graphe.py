class Grille():
    def __init__(self, l=5, c=5):
        sommets = []
        for i in range(1, l+1):
            for j in range(1, c+1):
                sommets.append((i, j))

        aretes = {}
        for s in sommets:
            aretes[s] = [t for t in sommets if (s[0] == t[0] and abs(
                s[1]-t[1]) == 1) or (s[1] == t[1] and abs(s[0]-t[0]) == 1)]

        self.lignes = l
        self.colonnes = c
        self.sommets = sommets
        self.aretes = aretes
        self.graphe = (sommets, aretes)

    def __str__(self):
        return f"Sommets : {self.sommets}\nArêtes : {self.aretes}"

    def shape(self):
        return (self.lignes, self.colonnes)

    def arete(self, s):
        return self.aretes[s]

    def exist_arete(self, s, t):
        return t in self.arete(s)

    def obstacles(self):
        return [((1, 2), (1, 3))]

    def delete_arete(self, s, t):
        if self.exist_arete(s, t):
            if t in self.aretes[s]:
                self.aretes[s].remove(t)
        if self.exist_arete(t, s):
            if s in self.aretes[t]:
                self.aretes[t].remove(s)

    def add_arete(self, s, t):
        if not self.exist_arete(s, t):
            self.aretes[s].append(t)
        if not self.exist_arete(t, s):
            self.aretes[t].append(s)


class Robot():
    def __init__(self, i=1, j=1, orientation=0):
        G = Grille(5, 5)
        self.grille = G
        self.i = i
        self.j = j
        self.direction = orientation

    def position(self):
        return (self.i, self.j)

    def __str__(self):
        return f"Position : {self.position()}\nOrientation : {self.direction}"

    def droite(self):
        self.direction -= 90

        if self.direction == -180:
            self.direction = 180

    def gauche(self):
        self.direction += 90

        if self.direction == 270:
            self.direction = -90

    def avance(self):
        if self.direction == 0 and self.j < self.grille.shape()[1]:
            self.j += 1
        elif self.direction == 90 and self.i > 1:
            self.i -= 1
        elif self.direction == -90 and self.i < self.grille.shape()[0]:
            self.i += 1
        elif self.direction == 180 and self.j > 1:
            self.j -= 1
        else:
            pass

    def recule(self):
        if self.direction == 0 and self.j > 1:
            self.j -= 1
        elif self.direction == 90 and self.i < self.grille.shape()[0]:
            self.i += 1
        elif self.direction == -90 and self.i > 1:
            self.i -= 1
        elif self.direction == 180 and self.j < self.grille.shape()[1]:
            self.j += 1
        else:
            pass

    def itineraire(self, ifin=1, jfin=1, obstacles=[]):
        s = self.position()
        t = (ifin, jfin)

        itin = [t]
        file = [s]
        # Ensemble des nœuds déjà visités pour éviter les cycles
        parent = {s: None}
        # Liste pour stocker l'ordre de visite
        G = self.grille
        for x, y in obstacles:
            # if type(x) is tuple and type(y) is tuple:
            G.delete_arete(x, y)
            # if type(x) is int and type(y) is int:
            #    G.sommets.remove((x, y))
            #    G.aretes.pop((x, y))
            #    for a in G.aretes.keys():
            #        G.aretes[a].remove((x, y))

        # Tant qu'il y a des nœuds dans la file
        while file:
            # Récupérer le nœud en tête de file
            noeud = file.pop(0)

            # Parcourir les voisins non visités
            for voisin in G.arete(noeud):
                if voisin not in parent:
                    parent[voisin] = noeud
                    file.append(voisin)

        if itin[-1] in parent:
            while parent[itin[-1]] is not None:
                itin.append(parent[itin[-1]])

        return list(reversed(itin))

    def detect_obstacle(self):
        i, j = self.position()
        direction = self.direction
        G = self.grille

        if (direction == 0 and (self.position(), (i, j+1)) in G.obstacles()) or (direction == 90 and (self.position(), (i-1, j)) in G.obstacles()) or (direction == -90 and (self.position(), (i+1, j)) in G.obstacles()) or (direction == 180 and (self.position(), (i, j-1)) in G.obstacles()):
            return True
        else:
            return False

    def move_to(self, ifin=1, jfin=1, obstacles=[]):  # -> GAUCHE, RIGHT, AVANCE, RECULE
        s = self.position()
        # print(f"Je suis orienté à {self.direction}°")

        # On code les arêtes où le robot n'a pas le droit d'aller
        # i, j = s
        # forbidden = [] + obstacles
        # if self.direction == 0:
        #    forbidden.append((s, (i, j-1)))
        # elif self.direction == 90:
        #    forbidden.append((s, (i+1, j)))
        # elif self.direction == -90:
        #    forbidden.append((s, (i-1, j)))
        # elif self.direction == 180:
        #    forbidden.append((s, (i, j+1)))

        itineraire = self.itineraire(ifin, jfin, obstacles)

        if len(itineraire) == 0:
            return "STOP"

        # print(f"Voici mon itinéraire initial :\n{itineraire}")

        s = itineraire.pop(0)

        if len(itineraire) == 0:
            return "STOP"

        t = itineraire.pop(0)

        target = 0

        if t[0]-s[0] == 1:
            target = -90
        elif t[1]-s[1] == 1:
            target = 0
        elif t[0]-s[0] == -1:
            target = 90
        elif t[1]-s[1] == -1:
            target = 180

        if self.direction-target == 90 or self.direction-target == -270:
            return "90RIGHT"
        elif self.direction-target == -90 or self.direction-target == 270:
            return "90LEFT"
        elif abs(self.direction-target) == 180:
            return "180LEFT"
        else:
            return "FRONT"
            # if self.detect_obstacle():
            #     print("Oh mince, un obstacle !")
            #     if virage == "D":
            #         self.gauche()
            #     elif virage == "G":
            #         self.droite()
            #     self.grille.delete_arete(s, t)
            #     print("Je recalcule mon itinéraire ...")
            #     itineraire = self.itineraire(ifin, jfin)
            #     print("C'est bon, on est reparti")
            #     print(f"Voici mon nouvel itinéraire :\n{itineraire}")
            #     s = itineraire.pop(0)
            #     continue

            #     self.avance()
            #     print("Vroum ! J'avance !")
            #     s = t
            #     print(f"Je suis au point {s}, et orienté à 