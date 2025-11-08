## IN PROGRESS

import os
import asyncio
import datetime
from fetch_calendar import auth_fetch
from gemini import analyze_calendar_data, call_gemini_api
from dotenv import load_dotenv

load_dotenv()

LOCATION = "Amherst, Massachusetts"
TIMEZONE = datetime.timezone(-datetime.timedelta(hours=5))

def get_gemini_recommendations():
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
        text, sources = asyncio.run(call_gemini_api(analysis, LOCATION, api_key))
    except Exception as e:
        print(f"Error running asyncio task: {e}")
        return
        
    if not text:
        print("Failed to generate a plan.")
        return

    # 3. Render the output
    print("\n" + "="*50)
    print("   Your Personalized Plan")
    print("="*50 + "\n")
    print(text)

    if sources:
        print("\n" + "-"*50)
        print("Sources:")
        
        # Deduplicate sources
        unique_sources = {s['uri']: s for s in sources}.values()
        
        for i, source in enumerate(unique_sources, 1):
            print(f"  [{i}] {source['title']}\n      <{source['uri']}>")
    
    print("\n" + "="*50)



if __name__ == "__main__":
    get_gemini_recommendations()