#!/bin/bash

cd /home/ubuntu

sudo apt update

git clone https://github.com/raulikeda/tasks.git

sudo sed -i "s/node1/postgresIp/g" ./tasks/portfolio/settings.py

cd tasks

./install.sh

sudo reboot


