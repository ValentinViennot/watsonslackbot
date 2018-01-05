#author niyatip
# coding: utf-8
from __future__ import print_function
from apiclient import discovery
from slackclient import SlackClient
from watson_developer_cloud import ConversationV1

import os
import time
import re

import httplib2
import json

import oauth2client
from oauth2client import client
from oauth2client import tools

import logging
logging.basicConfig()

import datetime


try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# starterbot's ID as an environment variable
#BOT_ID = os.environ.get("BOT_ID")

import keys

# instantiate Slack & Twilio clients
slack_client = SlackClient(keys.SLACK_BOT_TOKEN)

context = {}
FLOW_MAP = {}

def get_credentials(user):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart-' + user + '.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()

    return credentials

def get_auth_url(user):
    """ Creates a Flow Object from a clients_secrets.json which stores client parameters
        like client ID, client secret and other JSON parameters.

    Returns:
        Authorization server URI.
    """
    existing_flow = FLOW_MAP.get(user)
    if existing_flow is None:
        #urn:ietf:wg:oauth:2.0:oob to not redirect anywhere, but instead show the token on the auth_uri page
        flow = client.flow_from_clientsecrets(filename = keys.CLIENT_SECRET_FILE, scope = keys.SCOPES, redirect_uri = "urn:ietf:wg:oauth:2.0:oob")
        flow.user_agent = keys.APPLICATION_NAME
        auth_url = flow.step1_get_authorize_url()
        print(auth_url)
        FLOW_MAP[user] = flow
        return auth_url
    else:
        return existing_flow.step1_get_authorize_url()

def set_auth_token(user, token):
    """ Exchanges an authorization flow for a Credentials object.
    Passes the token provided by authorization server redirection to this function.
    Stores user credentials.
    """
    flow = FLOW_MAP.get(user)
    if flow is not None:
        try:
            credentials = flow.step2_exchange(token)
        except oauth2client.client.FlowExchangeError:
            return -1

        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'calendar-python-quickstart-' + user + '.json')

        store = oauth2client.file.Storage(credential_path)
        print("Storing credentials at " + credential_path)
        store.put(credentials)
        return 0
    else:
        return None


def calendarUsage(user, intent, d, t):
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """

    responseFromCalendar = ""
    credentials = get_credentials(user)

    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http, cache_discovery=False)

    now = d + 'T' + t + 'Z' # 'Z' indicates UTC time
    print('Getting the 10 upcoming events')
    eventsResult = service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    
    if intent == "schedule":
    
        dataList = []    
        if not events:
            dataList = 'No upcoming events found.'
        for event in events:
            try:
                print(event['summary'])
                start = datetime.datetime.strptime(event['start']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S").strftime("%I:%M %p, %a %b %d")
                attachmentObject = {}
                attachmentObject['color'] = "#2952A3"
                attachmentObject['title'] = event['summary']
                attachmentObject['text']= start
                dataList.append(attachmentObject)
            except KeyError:
                print("Not an event.")
                pass
        return dataList
                
    if intent == "free_time":
        if not events:
            response = "Vous n'avez rien de prévu prochainement."
        else:
            #grab the date of the calendar request
            date, time = events[0]['start']['dateTime'].split('T')
    
            #assume a starting time of 8 AM
            checkTime = datetime.datetime.strptime(date+"T08:00:00","%Y-%m-%dT%H:%M:%S")
            endTime = datetime.datetime.strptime(date+"T17:00:00","%Y-%m-%dT%H:%M:%S")
            response = "Vous êtes libre"
    
            #loop over events, if they start before 5 PM check to see if there is space between the start of the event and the end of the previous
            for event in events:
                try:
                    start = datetime.datetime.strptime(event['start']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S")
                    if start < endTime:  
                        if start > checkTime:
                            response += " de " + checkTime.strftime("%I:%M %p") + " à " + start.strftime("%I:%M %p") + ","
                        checkTime = datetime.datetime.strptime(event['end']['dateTime'][:-6],"%Y-%m-%dT%H:%M:%S")
                except KeyError:
                    print("Not an event.")
                    pass  
    
            #if last event ends before 5 PM, set hard limit at 5. Otherwise, change sentence formatting appropriately
            if checkTime < endTime:
                response += " et de " + checkTime.strftime("%I:%M %p") + " à 05:00 PM"
            else:
                response = response[:-1]
                r = response.rsplit(',',1)
                if len(r)>1:
                    response = r[0] + ", et" + r[1]
                if response == "Vous êtes libr":
                    response = "Pas de disponibilité"
            
        return response
    
    
def handle_command(command, channel, user):
    """
        Receives commands directed at the bot and determines if they
        are valid commands.
        If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    attachments = ""
    response = "Je ne comprends pas cette demande."
    print("Command : "+command)
    #Manage authentication process
    if command.startswith("token"):
        store_status = set_auth_token(user, command[6:].strip())
        if store_status is None:
            response = "Vous devez d'abord me donner l'autorisation de consulter votre calendrier, dites @watson hello."
        elif store_status == -1:
            response = "Le token que vous m'avez donné n'est pas valide."
        elif store_status == 0:
            response = "Authentification réussie ! J'ai maintenant accès à votre agenda."
    elif get_credentials(user) is None or command.startswith("reauth"):
        response = "Ouvrez cette url dans votre navigateur: " +  get_auth_url(user) \
                   + " \n Puis envoyez-moi le token obtenu en disant @watson token abc123."
    else :
        #Link to Watson Conversation as Auth is completed
        conversation = ConversationV1(
            username = keys.USERNAME,
            password = keys.PASSWORD,
            version = '2017-04-21', url = 'https://gateway-fra.watsonplatform.net/conversation/api'
        )

        #Get response from Watson Conversation
        responseFromWatson = conversation.message(
            workspace_id=keys.WORKSPACE_ID,
            input={'text': command},
            context=context
        )

        print("Response from Watson :")
        print(responseFromWatson)

        #Get intent of the query
        intent = ""
        try:
            intent = responseFromWatson['intents'][0]['intent']
        except IndexError:
            intent = "dont_understand"
            pass;

        #Render response on Bot
        #Format Calendar output on the basis of intent of query
        if intent == "schedule" or intent == "free_time":
            # get entities
            datetmp = datetime.date.today().isoformat()
            timetmp = datetime.datetime.utcnow().time().isoformat()
            try:
                for i in range(0,3):
                    try:
                        if responseFromWatson['entities'][i]['entity'] == "sys-date":
                            datetmp = responseFromWatson['entities'][i]['value']
                            pass
                        elif responseFromWatson['entities'][i]['entity'] == "sys-time":
                            timetmp = responseFromWatson['entities'][i]['value'] + ".000000"
                            pass
                    except KeyError:
                        pass
            except IndexError:
                pass
            calusage = calendarUsage(user, intent, datetmp, timetmp)
            if intent == "schedule":
                response = responseFromWatson['output']['text'][0]
                attachments = calusage
            else:
                response = calusage
        #Request not managed by Bot
        else:
            response = responseFromWatson['output']['text'][0]
        
    slack_client.api_call("chat.postMessage", as_user=True, channel=channel, text=response,
                      attachments=attachments)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        This parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and keys.AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split("<@"+keys.AT_BOT+">")[1].strip(), \
                       output['channel'], output['user']
    return None, None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel, user = parse_slack_output(slack_client.rtm_read())
            if command and channel and user:
                handle_command(command, channel, user)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
