#!/bin/bash
# virtualenv, pip and python needed
# New virtual env
virtualenv watsonbot
source watsonbot/bin/activate
# Dependencies
pip install watson-developer-cloud
pip install slackclient
pip install --upgrade google-api-python-client
