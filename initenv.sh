#!/bin/bash
# virtualenv, pip and python needed
# New virtual env
virtualenv watsonbot
source watsonbot/bin/activate
# Dependencies
pip install -r requirements.txt
