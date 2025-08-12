#!/bin/bash

# Variables
VENV_DIR="/home/pi/grid_freq_monitor/grid_freq_monitor_env"
SCRIPT_PATH="/home/pi/grid_freq_monitor/grid_freq_monitor.py"

# 1. Créer l'environnement virtuel s'il n'existe pas
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# 2. Activer l'environnement virtuel
source "$VENV_DIR/bin/activate"

# 3. Installer les dépendances
pip install --upgrade pip
pip install pigpio websockets

# 4. Démarrer pigpiod s'il n'est pas déjà lancé
if ! pgrep -x "pigpiod" > /dev/null; then
    sudo pigpiod
    sleep 1  # attendre que pigpiod démarre
fi

# 5. Lancer le script Python
python3 "$SCRIPT_PATH"
