import os
import json
#import google.generativeai as genai
import google.genai as genai
from datetime import datetime, time, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# --- MOCK DATA ---
# Pre-filled data to simulate a high-stress user (same as the HTML app)
MOCK_DATA = {
    "pastWeek": [
        {"summary": "Project A Deadline Push", "start": "2025-11-03T09:00:00Z", "end": "2025-11-03T17:00:00Z"},
        {"summary": "Client Call - Project B", "start": "2025-11-04T10:00:00Z", "end": "2025-11-04T11:30:00Z"},
        {"summary": "Team Sync", "start": "2025-11-04T14:00:00Z", "end": "2025-11-04T15:00:00Z"},
        {"summary": "Budget Review", "start": "2025-11-04T15:00:00Z", "end": "2025-11-04T17:00:00Z"},
        {"summary": "All-Hands Meeting", "start": "2025-11-05T09:00:00Z", "end": "2025-11-05T11:00:00Z"},
        {"summary": "Focus Block - Coding", "start": "2025-11-05T11:00:00Z", "end": "2025-11-05T16:00:00Z"},
        {"summary": "Late Review", "start": "2025-11-05T17:00:00Z", "end": "2025-11-05T18:30:00Z"},
        {"summary": "Project C Kick-off", "start": "2025-11-06T09:30:00Z", "end": "2025-11-06T11:00:00Z"},
        {"summary": "1-on-1 with Manager", "start": "2025-11-06T11:30:00Z", "end": "2025-11-06T12:00:00Z"},
        {"summary": "Strategy Session", "start": "2025-11-06T14:00:00Z", "end": "2025-11-06T17:00:00Z"},
        {"summary": "Final Sprint Planning", "start": "2025-11-07T10:00:00Z", "end": "2025-11-07T12:30:00Z"},
        {"summary": "Code Freeze", "start": "2025-11-07T13:30:00Z", "end": "2025-11-07T18:00:00Z"}
    ],
    "today": [
        {"summary": "Morning Stand-up", "start": "2025-11-08T09:00:00-05:00", "end": "2025-11-08T09:30:00-05:00"},
        {"summary": "Dentist Appointment", "start": "2025-11-08T11:00:00-05:00", "end": "2025-11-08T12:00:00-05:00"},
        {"summary": "Project Phoenix - Final Review", "start": "2025-11-08T15:00:00-05:00", "end": "2025-11-08T16:30:00-05:00"}
    ],
    "upcomingWeek": [
        {"summary": "Project D Launch", "start": "2025-11-10T09:00:00Z", "end": "2025-11-10T11:00:00Z"},
        {"summary": "Client Onboarding", "start": "2025-11-10T13:00:00Z", "end": "2025-11-10T15:00:00Z"},
        {"summary": "Hiring Interviews", "start": "2025-11-11T10:00:00Z", "end": "2025-11-11T12:00:00Z"},
        {"summary": "Product Roadmap Planning", "start": "2025-11-11T14:00:00Z", "end": "2025-11-11T17:00:00Z"},
        {"summary": "Investor Update Prep", "start": "2025-11-12T09:00:00Z", "end": "2025-11-12T17:00:00Z"},
        {"summary": "Board Meeting", "start": "2025-11-13T10:00:00Z", "end": "2025-11-13T15:00:00Z"},
        {"summary": "Team Outing (Company)", "start": "2025-11-13T17:00:00Z", "end": "2025-11-13T20:00:00Z"},
        {"summary": "Marketing Sync", "start": "2025-11-14T11:00:00Z", "end": "2025-11-14T12:00:00Z"},
        {"summary": "Sprint Retro/Demo", "start": "2025-11-14T14:00:00Z", "end": "2025-11-14T16:00:00Z"}
    ]
}

def format_minutes_to_time(minutes):
    """Converts minutes from midnight to a 12-hour AM/PM string."""
    h = minutes // 60
    m = minutes % 60
    dt = time(hour=h, minute=m)
    return dt.strftime("%I:%M %p").lstrip('0')

def analyze_calendar_data(past_events, today_events, upcoming_events):
    """
    Analyzes raw calendar data to produce busyness scores and free slots.
    """
    
    # --- Helper to calculate hours for a list of events ---
    def calculate_total_hours(events):
        total_hours = 0
        for event in events:
            try:
                # Use fromisoformat to parse timezone-aware strings
                start = datetime.fromisoformat(event['start'])
                end = datetime.fromisoformat(event['end'])
                duration = end - start
                total_hours += duration.total_seconds() / 3600
            except (ValueError, TypeError):
                print(f"Skipping invalid event: {event.get('summary')}")
                continue
        return total_hours

    # --- Busyness Score (0.0 to 1.0) ---
    WORKING_HOURS_PER_WEEK = 40.0
    past_busyness = min(1.0, calculate_total_hours(past_events) / WORKING_HOURS_PER_WEEK)
    upcoming_busyness = min(1.0, calculate_total_hours(upcoming_events) / WORKING_HOURS_PER_WEEK)

    # --- Today's Simple Event List (for the prompt) ---
    today_appointments = []
    for event in today_events:
        try:
            start = datetime.fromisoformat(event['start'])
            end = datetime.fromisoformat(event['end'])
            start_str = start.strftime("%I:%M %p").lstrip('0')
            end_str = end.strftime("%I:%M %p").lstrip('0')
            today_appointments.append({"summary": event['summary'], "time": f"{start_str} - {end_str}"})
        except (ValueError, TypeError):
            today_appointments.append({"summary": event.get('summary'), "time": "Time TBD"})

    # --- Today's Free Slots (9am-5pm) ---
    work_day_start_minutes = 9 * 60
    work_day_end_minutes = 17 * 60
    current_time_minutes = work_day_start_minutes
    free_slots = []

    # Map and sort events
    sorted_events = []
    for e in today_events:
        try:
            start_dt = datetime.fromisoformat(e['start'])
            end_dt = datetime.fromisoformat(e['end'])
            sorted_events.append({
                "summary": e['summary'],
                "start": start_dt,
                "end": end_dt
            })
        except (ValueError, TypeError):
            continue
            
    sorted_events.sort(key=lambda x: x['start'])

    for event in sorted_events:
        event_start_minutes = event['start'].hour * 60 + event['start'].minute
        event_end_minutes = event['end'].hour * 60 + event['end'].minute

        if event_start_minutes > current_time_minutes:
            free_slots.append({
                "start": format_minutes_to_time(current_time_minutes),
                "end": format_minutes_to_time(event_start_minutes),
                "duration": event_start_minutes - current_time_minutes
            })
        current_time_minutes = max(current_time_minutes, event_end_minutes)

    if current_time_minutes < work_day_end_minutes:
        free_slots.append({
            "start": format_minutes_to_time(current_time_minutes),
            "end": format_minutes_to_time(work_day_end_minutes),
            "duration": work_day_end_minutes - current_time_minutes
        })

    return {
        "pastBusyness": round(past_busyness, 2),
        "upcomingBusyness": round(upcoming_busyness, 2),
        "todayAppointments": today_appointments,
        "todayFreeSlots": [slot for slot in free_slots if slot["duration"] > 30]
    }

async def call_gemini_api(analysis, location, api_key):
    """
    Calls the Gemini API with the calendar analysis and location.
    """
    client = genai.Client(api_key=api_key)
    #old code
    #genai.configure(api_key=api_key)
    
    ## Change system prompt to output speakable text
    system_prompt = """You are an expert life-balance and wellness coach. Your goal is to help a user manage stress and find a healthy work-life balance.
You will receive a JSON analysis of their calendar (past, present, and future) and their location.
Your task is to generate a helpful, empathetic, and actionable plan for their day.

**Your response MUST strictly follow this Markdown structure:**

### 1. Greeting & Today's Brief
A warm, empathetic welcome (e.g., "Good morning. It looks like today...").
A 1-2 sentence summary of their day's appointments.

### 2. Your Weekly Vibe
An empathetic assessment of their recent and upcoming week based on the busyness scores. (e.g., "It looks like you've been in back-to-back meetings and the week ahead is also packed. That's a lot to handle. Let's make sure you get time to breathe today.").

### 3. Today's Rejuvenation Plan
Based on their free time *and location*, suggest 1-2 *specific* local activities.
**You MUST use your Google Search tool** to find real, low-stress activities (e.g., "a quiet walk at [Local Park]" or "a relaxing coffee at [Local Cafe]").
**You MUST include the name of the place and why it's a good low-stress choice.**
These suggestions *must* fit into their "Today's Free Slots".

### 4. Today's Ideal Schedule
An hourly or block-based breakdown for their day (e.g., 9:00 AM - 5:00 PM).
**You MUST integrate their existing appointments.**
**You MUST** proactively schedule short breaks (e.g., "Pomodoro break," "short walk," "mindful lunch") in their free slots.
This should be a bulleted or numbered list.

**Tone:** Empathetic, encouraging, and professional.
"""

    user_prompt = f"""Here is my calendar analysis. Please generate my plan.

**Location:** {location}

**Analysis:**
```json
{json.dumps(analysis, indent=2)}
```
"""

    # Set up the model

    ##old code 
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-09-2025',
        contents=system_prompt,
        config=genai.types.GenerateContentConfig(
            tools=[genai.types.Tool(google_search=genai.types.GoogleSearch())],
        ),
    )
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-09-2025",
        system_instruction=system_prompt,
        tools=[genai.types.Tool(google_search=genai.types.GoogleSearch())]
    )
    """
    print("Generating plan... (This may take a moment)")
    
    try:

        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash-preview-09-2025',
            contents=[user_prompt]
        )
        ## old code
        #response = await model.generate_content_async([user_prompt])
        
        text = response.text
        
        # Extract sources
        #blah = genai.types.GroundingMetadata().
        sources = []
        if (response.candidates[0].grounding_metadata and 
            response.candidates[0].grounding_metadata.grounding_supports):
            
            attributions = response.candidates[0].grounding_metadata.grounding_supports
            #attributions = response.candidates[0].grounding_metadata.grounding_attributions
            
            for attribution in attributions:
                if hasattr(attribution, 'web'):
                    sources.append({
                        "uri": attribution.web.uri,
                        "title": attribution.web.title,
                    })
        
        return text, sources

    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return None, None

def main():
    """
    Main function to run the analysis and print the plan.
    """
    api_key = os.getenv("GEMINI_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set your API key to run this script.")
        return

    location = "Amherst, Massachusetts" # You can change this
    
    # 1. Pre-process the data
    print("Analyzing calendar data...")
    analysis = analyze_calendar_data(
        MOCK_DATA["pastWeek"],
        MOCK_DATA["today"],
        MOCK_DATA["upcomingWeek"]
    )
    
    # 2. Call Gemini API
    print("Calling Gemini API...")
    
    # Run the async function
    import asyncio
    try:
        text, sources = asyncio.run(call_gemini_api(analysis, location, api_key))
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
    main()