# st5-robot

## Simulation

Pour simuler le comportement du robot, nous avons choisi d'utiliser [*Webots*](https://cyberbotics.com/) plutôt que *Simulink*.
En effet, *Webots* permet de développer les algorithmes de perception et de comportement du robot directement en Python. Nous évitons ainsi l'étape de retranscription de MATLAB vers Python.

### Fonctionnement de Webots

Une simulation sur *Webots* est principalement constitué d'un monde (world, fichier ```.wbt```). Il faut ouvrir ce fichier dans *Webots*.

Le monde des composé de noeuds (solides tels que le sol, robots et autres).

Nous avons placé les noeuds correspondants à la grille et au robot.

Le noeud robot est constitués d'enfants (children) tels que :

- le chassis
- les roues et liaisons pivots
- la caméra
- les capteurs (distance, encodeurs)

Le robot est associé à un fichier python : ```controller.py```. Ce dernier s'exécute au lancement de la simulation.

Les données du robot peuvent ainsi être traitées dans ce fichier. Nous pouvons aussi lui envoyer des ordres.

### Mise en place de la simulation

Les fichiers spécifiques à la simulation sont dans le dossier ```sim```.

Démarrez la simulation en ouvrant le monde *Webots* ```sim/worlds/grille.wbt```. Il faut s'assurer que le temps s'écoule bien. Le robot attend les ordres.

Puis exécutez les commandes suivantes à partir de la racine de ```st5-robot``` dans deux terminaux séparés.

```shell
python .\host\monitoring.py
python .\nodes\planner.py
```