# Instructions d'installation de l'assistant ALLO

## Liste du hardware
* Un raspberry Pi 2 ou 3
* Un micro Respeaker 2 mic HAT

## Préparation du raspberry et installation de Snips
* Snips a réalisé [un tutoriel très complet](https://github.com/snipsco/snips-platform-documentation/wiki/1.-Setup-the-Snips-Voice-Platform) pour cette étape.
* Ne pas oublier d'activer le spi :
	* `sudo raspi-config`
	* Aller dans le menu `Interfacing options` et `Enable SPI`
	* rebooter le raspberry

## Installation de l'assistant ALLO sur le raspberry
* Se connecter au raspberry `ssh pi@monipderaspberry`
* Installer les dépendances python : `sudo pip3 install -r requirements.txt`
* Cloner le projet `git clone https://github.com/pierrot-app/snips.git`

## Installation de l'environnement snips sur son ordinateur
* Avoir [node.js](https://nodejs.org/en/download/)
* Installer [le CLI sam](https://snips.gitbook.io/getting-started/installation)
* Se connecter au CLI sam avec l'adresse Gobelins `pierrot-app@edu.gobelins.fr` (demander à leo ou ben pour le mdp)
* Connecter sam au raspberry depuis son ordinateur : `sam connect monipderaspberry`
* Installer l'assistant ALLO : `sam install assistant`

## Lancer le projet en debug
* Se connecter au raspberry `ssh pi@monipderaspberry`
* Aller dans le dossier ou est enregistré le projet : `cd ~/snips`
* Lancer le projet `python main.py`
* Depuis son ordinateur, pour avoir les logs de la circulation mqtt : `sam watch`

## Outils
* [MQTT.fx](http://mqttfx.org/) qui permet de monitorer depuis une GUI les channels mqtt.

## TODO
* Faire de ALLO [un service](https://github.com/Psychokiller1888/MyChef/blob/master/mychef.service)
* Ajouter conf du speaker