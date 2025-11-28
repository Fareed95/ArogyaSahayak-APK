from fastapi import FastAPI
from pydantic import BaseModel
import urllib.parse

app = FastAPI()

class HospitalRequest(BaseModel):
    hospital_name: str
    city: str = "Mumbai"

@app.post("/book-uber")
def book_uber(data: HospitalRequest):
    hospital = data.hospital_name.strip()
    city = data.city.strip()

    # Encode the destination
    encoded = urllib.parse.quote_plus(f"{hospital}, {city}")

    google_maps = f"https://www.google.com/maps/search/?api=1&query={encoded}"
    uber_link = f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={encoded}"

    return {
        "hospital": hospital,
        "google_maps_link": google_maps,
        "uber_link": uber_link
    }
