## Necessary install to run calendar API
## pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

## NOTE: MAY NEED TO ADD TEAMMATES TO AUTHORIZED TESTERS IN GOOGLE CLOUD

## the following code has been modified from Google's quickstart.py sample code
## This sample code is licensed under the Apache 2.0 license, available at https://www.apache.org/licenses/LICENSE-2.0

import datetime
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

#TIMEZONE = datetime.timezone(-datetime.timedelta(hours=5))

def to_JSON(input):
    return json.dumps(input, indent=2)

def fetch_daily_events(creds, timezone):
  try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.now(tz=timezone).isoformat()
    #print(now)
    end_of_day = datetime.datetime.now(tz=timezone).replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    #print("Getting the events for today")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            singleEvents=True,
            orderBy="startTime",
            timeMax=end_of_day,
            timeZone = timezone
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
      print("No upcoming events found.")
      return []


    # Returns the start time, end time, and name of the events for today
    eventList = []
    eventInfo = {}
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))#[11:16]
      end = event["end"].get("dateTime", event["end"].get("date"))#[11:16]
      #print(start, end, event["summary"])
      eventInfo = {"summary":event["summary"], "start":start, "end":end}
      eventList.append(eventInfo)
    return eventList

  except HttpError as error:
    print(f"An error occurred: {error}")
    return None

def fetch_prev_week_events(creds, timezone):
  try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    dt_end_today = datetime.datetime.now(tz=timezone).replace(hour=23, minute=59, second=59, microsecond=999999)
    #print(now)
    prev_week = (dt_end_today-datetime.timedelta(days=7)).isoformat()
    end_of_yesterday = (dt_end_today-datetime.timedelta(days=1)).isoformat()
    #print("Getting the events for previous week")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=prev_week,
            singleEvents=True,
            orderBy="startTime",
            timeMax=end_of_yesterday,
            timeZone = timezone
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
      print("No upcoming events found.")
      return []


    # Returns the start time, end time, and name of the events for today
    eventList = []
    eventInfo = {}
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))#[11:16]
      end = event["end"].get("dateTime", event["end"].get("date"))#[11:16]
      #print(start, end, event["summary"])
      eventInfo = {"summary":event["summary"], "start":start, "end":end}
      eventList.append(eventInfo)
    return eventList

  except HttpError as error:
    print(f"An error occurred: {error}")
    return None

def fetch_next_week_events(creds, timezone):
  try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    dt_end_today = datetime.datetime.now(tz=timezone).replace(hour=23, minute=59, second=59, microsecond=999999)
    #print(now)
    end_of_today = dt_end_today.isoformat()
    next_week_end = (dt_end_today+datetime.timedelta(days=7)).isoformat()
    
    #print("Getting the events for previous week")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=end_of_today,
            singleEvents=True,
            orderBy="startTime",
            timeMax=next_week_end,
            timeZone = timezone
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
      print("No upcoming events found.")
      return []


    # Returns the start time, end time, and name of the events for today
    eventList = []
    eventInfo = {}
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))#[11:16]
      end = event["end"].get("dateTime", event["end"].get("date"))#[11:16]
      #print(start, end, event["summary"])
      eventInfo = {"summary":event["summary"], "start":start, "end":end}
      eventList.append(eventInfo)
    return eventList

  except HttpError as error:
    print(f"An error occurred: {error}")
    return None

def auth_fetch(whichTime="today", timezone=datetime.timezone(-datetime.timedelta(hours=5))):
  """
  Allows user to authorize with Google Calendar if necessary before fetching the daily events 
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
  match whichTime:
    case "today":
      return(fetch_daily_events(creds, timezone))
    case "prev_week":
      return(fetch_prev_week_events(creds, timezone))
    case "next_week":
      return(fetch_next_week_events(creds, timezone))
    case _:
      print("Invalid time area request")
      return None
  



if __name__ == "__main__":
  print(auth_fetch("today"))
  print(auth_fetch("prev_week"))
  print(auth_fetch("next_week"))
