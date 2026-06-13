import requests
import os
import re
import json
from datetime import datetime as dtt
from dotenv import load_dotenv

load_dotenv() 
USERNAME = os.environ["PIXELA_USERNAME"]
TOKEN = os.environ["PIXELA_TOKEN"]
THANKS_CODE = os.environ["PIXELA_THANKS_CODE"]

PIXELA_ENDPOINT = "https://pixe.la/v1/users"
TOTAL_GRAPH_NAME = "Learning Tracker"
TOTAL_GRAPH_ID = "tr-learning-trac"

def create_user():
    user_params = {
    "token": TOKEN,
    "username": USERNAME,
    "agreeTermsOfService": "yes",
    "notMinor": "yes",
    "thanksCode": THANKS_CODE
}
    # POST
    response = requests.post(url=PIXELA_ENDPOINT, json=user_params)
    print(f"Create user: {response.text}")

    create_graph(TOTAL_GRAPH_NAME)
    
    # PIN The Learning Tracker Total graph
    graph_config = {"pinnedGraphID": TOTAL_GRAPH_ID}

    headers = {"X-USER-TOKEN": TOKEN}

    user_endpoint = f"https://pixe.la/@{USERNAME}"
    response = requests.put(url=user_endpoint, json=graph_config, headers=headers)
    print(f"Pinned total Graph: {response.text}")

def delete_user():
    url = f"{PIXELA_ENDPOINT}/{USERNAME}"
    headers = {"X-USER-TOKEN": TOKEN}

    # Ask for confirmation
    confirm = input(f"⚠️ Are you sure you want to delete the Pixela user '{USERNAME}'? (yes/no): ").strip().lower()

    if confirm == "yes":
        response = requests.delete(url, headers=headers)
        print(response.text)
    else:
        print("❎ Deletion cancelled.")

def update_user_with_thanks_code():
    url = f"{PIXELA_ENDPOINT}/{USERNAME}"
    headers = {"X-USER-TOKEN": TOKEN}
    data = {"thanksCode": THANKS_CODE}

    response = requests.put(url, headers=headers, json=data)
    print("Response:", response.text)

def to_graph_id(name: str) -> str:
    # Lowercase everything
    s = name.lower()
    # Replace spaces with hyphens
    s = s.replace(" ", "-")
    # Ensure it starts with 'tr-'
    if not s.startswith("tr-"):
        s = "tr-" + s
    # Keep only allowed characters: a-z, 0-9, -
    s = re.sub(r'[^a-z0-9-]', '', s)
    # Truncate to max length (17 chars total)
    return s[:16]

def create_graph(name: str):
    graph_endpoint = f"{PIXELA_ENDPOINT}/{USERNAME}/graphs"

   # print(to_graph_id(name))

    graph_id = to_graph_id(name)

    graph_config = {
    "id": graph_id,
    "name": name,
    "unit": "minutes",
    "type": "int",
    "color": "sora",
    "startOnMonday": True,
    "publishOptionalData": True,
    "timezone": "Europe/Vienna"
    }

    headers = {
    "X-USER-TOKEN": TOKEN
    }

    response = requests.post(url=graph_endpoint, json=graph_config, headers=headers)
    print(f"Create graph {name}: {response.text}")

def get_graph_list(date: str) -> list:
    import requests
    import os

    USERNAME = os.environ["PIXELA_USERNAME"] 
    TOKEN = os.environ["PIXELA_TOKEN"]
    DATE = date  # yyyymmdd

    s = requests.Session()
    s.headers.update({"X-USER-TOKEN": TOKEN})
    hits = []
    try: 
        # 1) get all graph IDs
        graphs = s.get(f"https://pixe.la/v1/users/{USERNAME}/graphs").json()["graphs"]

        for g in graphs:
            gid = g["id"]
            r = s.get(f"https://pixe.la/v1/users/{USERNAME}/graphs/{gid}/{DATE}")
            if r.status_code == 200 and gid.startswith("tr-") and gid != TOTAL_GRAPH_ID:
                qty = r.json().get("quantity")
                hits.append({"graphID": gid, "name": g.get("name"), "quantity": qty})
    except:
        print("get_graph_list: Please retry this request")

    return hits  # list of graphs that have a pixel on DATE

def delete_graph(graph_id: str):
    graph_delete_endpoint = f"{PIXELA_ENDPOINT}/{USERNAME}/graphs/{graph_id}"

    headers = {
    "X-USER-TOKEN": TOKEN
    }

    response = requests.delete(url=graph_delete_endpoint, headers=headers)
    print(f"Delete graph {graph_id}: {response.text}")

def add_pixel(graph_id: str, date: str, quantity: str, optional_data: str =""):
    headers = {
    "X-USER-TOKEN": TOKEN
    }
    post_pixel_endpoint = f"{PIXELA_ENDPOINT}/{USERNAME}/graphs/{graph_id}"
    post_pixel_config = {
    "date": date,
    "quantity": quantity,
    "optionalData": optional_data
    }

    response = requests.post(url=post_pixel_endpoint, json=post_pixel_config, headers=headers)
    print(f"Add pixel for {graph_id}: {response.text}")

def get_pixel_optional_data(graph_id: str, date: str) -> str:
    endpoint = f"{PIXELA_ENDPOINT}/{USERNAME}/graphs/{graph_id}/{date}"
    headers = {"X-USER-TOKEN": TOKEN}
    try:
        response = requests.get(url=endpoint, headers=headers)
        if response.status_code == 200:
            return response.json().get("optionalData", "") or ""
    except Exception:
        pass
    return ""

def merge_session(existing_optional_data: str, new_session: dict | None) -> str:
    """Append new_session to the sessions already stored on the pixel.

    Accepts the legacy single-object format ({"time":.., "comment":..}) and
    upgrades it to a list. Sessions are keyed by their start time, so
    re-uploading the same session (same start) replaces it rather than
    creating a duplicate.
    """
    try:
        data = json.loads(existing_optional_data) if existing_optional_data else []
    except (json.JSONDecodeError, TypeError):
        data = []
    if isinstance(data, dict):          # legacy single-session format
        data = [data]
    elif not isinstance(data, list):
        data = []

    if new_session:
        new_start = str(new_session.get("time", "")).split(" - ")[0].strip()
        if new_start:
            data = [s for s in data
                    if not (isinstance(s, dict)
                            and str(s.get("time", "")).split(" - ")[0].strip() == new_start)]
        data.append(new_session)

    return json.dumps(data, ensure_ascii=False)

def update_total_tracker(date: str, new_session: dict | None = None):
    total_minutes = 0
    for graph in get_graph_list(date):
        total_minutes += int(graph["quantity"])

    if total_minutes == 0:
        delete_pixel(date, TOTAL_GRAPH_ID)
    else:
        merged = merge_session(get_pixel_optional_data(TOTAL_GRAPH_ID, date), new_session)
        add_pixel(TOTAL_GRAPH_ID, date, str(total_minutes), merged)

def delete_pixel(date: str, graph_id: str):
    endpoint = f"https://pixe.la/v1/users/{USERNAME}/graphs/{graph_id}/{date}"

    headers = {"X-USER-TOKEN": TOKEN
        }
    response = requests.delete(url=endpoint, headers=headers)
    print(f"Delete pixel for {graph_id}: {response.text}")

# ---  Pixela user and total tracker graph setup  ---
# create_user()
# delete_user()
# update_user_with_thanks_code()
