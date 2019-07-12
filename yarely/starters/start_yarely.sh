#!/bin/sh
killall python3
killall python3
killall python3

./proj/yarely/starters/facade.py &
sleep 5 
./proj/yarely/starters/sensor_manager.py &
./proj/yarely/starters/subscription_manager.py &
./proj/yarely/starters/scheduler.py
