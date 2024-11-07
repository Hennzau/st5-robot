# Pour aller plus loin

La prochaine étape serait de rendre vraiment le projet end-to-end : nous devrions remplacer le code arduino `arduino/arduino.ino`
par un code `C` avec le manager de projet `platformio` et le projet `eclipse-zenoh-pico` en mode Serial.

Cela permettra d'avoir une seule vrai logique et de ne pas programmer nous même la communication Serial qui peut s'avérer plutôt complexe
et totalement inélégante.

Il faudra donc :
- Créer un projet `platformio` pour le code arduino avec le bon board
- Ajouter la dépendance `eclipse-zenoh-pico` pour la communication Serial

Liens utils : [zenoh-pico](https://github.com/eclipse-zenoh/zenoh-pico)
