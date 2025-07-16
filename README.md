# GNSS NMEA Reader

A Python script to configure and read NMEA GPS data from a serial GNSS receiver.

## Features
- Configures GPS, GLONASS, Galileo, BeiDou
- Supports update rate setting
- Parses GGA and RMC messages with fix validation

## Requirements
- `pynmea2`
- `pyserial`

## Usage
Edit the `SERIAL_PORT` in the script and run:
```bash
python gnss_reader.py
