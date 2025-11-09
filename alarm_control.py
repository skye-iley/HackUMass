## IN PROGRESS

import os
import asyncio
import datetime
import time
from fetch_calendar import auth_fetch
from gemini import analyze_calendar_data, call_gemini_api
from dotenv import load_dotenv
from speech import text_to_speech_save_file
from clock_GUI import view_clock

import pygame

load_dotenv()

LOCATION = "Amherst, Massachusetts"
TIMEZONE = datetime.timezone(-datetime.timedelta(hours=5))

def wait_till_time(target):
    while datetime.datetime.now(tz=TIMEZONE)<target:
        print(".")
        time.sleep(1)

async def get_gemini_recommendations():
    """
    Main function to run the analysis and print the plan.
    """
    api_key = os.getenv("GEMINI_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set your API key to run this script.")
        return

    
    # 1. Pre-process the data
    print("Analyzing calendar data...")
    analysis = analyze_calendar_data(
        auth_fetch("prev_week", TIMEZONE),
        auth_fetch("today", TIMEZONE),
        auth_fetch("next_week", TIMEZONE),
    )
    
    # 2. Call Gemini API
    print("Calling Gemini API...")
    
    # Run the async function
    try:
        text, sources = await call_gemini_api(analysis, LOCATION, api_key)
        #text, sources = asyncio.run(call_gemini_api(analysis, LOCATION, api_key))
    except Exception as e:
        print(f"Error running asyncio task: {e}")
        return
        
    if not text:
        print("Failed to generate a plan.")
        return

    # 3. Render the output
    #print("\n" + "="*50)
    print("   Your Personalized Plan")
    #print("="*50 + "\n")
    print(text)

    if sources:
        print("\n" + "-"*50)
        print("Sources:")
        
        # Deduplicate sources
        unique_sources = {s['uri']: s for s in sources}.values()
        
        for i, source in enumerate(unique_sources, 1):
            print(f"  [{i}] {source['title']}\n      <{source['uri']}>")
    
    print("\n" + "="*50)

    return text



def play_mp3(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    # Keep the program running until the music finishes
    while pygame.mixer.music.get_busy():
        time.sleep(1)

    # Replace 'your_song.mp3' with the actual path to your MP3 file

async def do_others():
    target_time = datetime.datetime.now(tz=TIMEZONE)+datetime.timedelta(seconds=30)
    text = await get_gemini_recommendations()
    text_to_speech_save_file(text)
    wait_till_time(target_time)
    ## takes about 5 seconds to run
    play_mp3('output.mp3')

async def main():
    await asyncio.gather(view_clock(),do_others())
    

if __name__ == "__main__":
    asyncio.run(main())
    
