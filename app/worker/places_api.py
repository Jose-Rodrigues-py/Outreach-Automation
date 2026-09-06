import httpx
import os
import asyncio
from dotenv import load_dotenv
from app.database.models import Client
from app.database.db import AsyncSessionLocal
from sqlalchemy import select
from app.worker.scraper import look

load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
ENDPOINT_URL = "https://places.googleapis.com/v1/places:searchNearby"

# to run once a month; i need close to 30*5*4=600 businesses / month
async def fetch_leads(response_data):    
    places = response_data.get("places", [])
    new_leads_count = 0

    async with AsyncSessionLocal() as db:
        for place in places:
            place_id = place.get("id")
        
            result = await db.execute(select(Client).where(Client.google_places_id == place_id))      
            existing_client = result.scalar_one_or_none()

            if not existing_client:
                name = place.get("displayName", {}).get("text", "Unknown")
                p_type = place.get("primaryType", "N/A")
                location = place.get("formattedAddress", "N/A")
                website = place.get("websiteUri")
                phone = place.get("nationalPhoneNumber", "N/A")

                emails = None
                if website:
                    emails = await look(website)

                new_client = Client( # messaged_at is now nullable; and will only be inserted once the message is actually sent
                    business_name = name,
                    google_places_id = place_id,
                    email = emails,
                    website = website,
                    phone = phone,
                    category=p_type,
                    location=location,
                    phone=phone
                )
                db.add(new_client)
                new_leads_count += 1
        await db.commit()
        print(f"Done. Saved {new_leads_count} new leads out of {len(places)} returned.")

async def main():
    # Official Google Places API primary types
    types = ["dentist", "electronics_store", "gym", "travel_agency", "real_estate_agency", "physiotherapist", "accounting"]
    
    locations = [
        [41.158002, -8.629176],  # Porto Center / Matosinhos / Maia
        [41.3800, -8.7600],      # Póvoa + Vila do Conde
        [41.1900, -8.3800],      # Valongo + Paredes
        [40.9200, -8.5500]       # Feira + SJ Madeira
    ]

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.primaryType,places.formattedAddress,places.websiteUri,places.nationalPhoneNumber"
    }

    # Total requests: 4 locations * 7 types = 28 API Calls (~560 potential leads)
    async with httpx.AsyncClient() as client:
        for loc in locations:
            for place_type in types:
                print(f"Fetching '{place_type}' around [{loc[0]}, {loc[1]}]...")
                
                payload = {
                    "includedTypes": [place_type],  
                    "maxResultCount": 20,
                    "rankPreference": "DISTANCE",
                    "locationRestriction": {
                        "circle": {
                            "center": {
                                "latitude": loc[0], 
                                "longitude": loc[1]
                            },
                            "radius": 10000.0  # 10 km
                        }
                    }
                }

                response = await client.post(ENDPOINT_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    await fetch_leads(response.json())
                else:
                    print(f" Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())