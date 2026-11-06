#!/bin/bash
clear
echo "========================================="
echo "   Wi-Fi Scanner Auto Installer Setup    "
echo "========================================="

pkg update -y && pkg upgrade -y
pkg install python git -y

pip install -r requirements.txt

clear
echo "========================================="
echo "   Setup ပြီးပါပြီ။ စတင် Run ပါမည်...   "
echo "========================================="
sleep 2

python updateurl.py
