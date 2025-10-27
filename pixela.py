import requests
import os
import re
from datetime import datetime as dtt

USERNAME = os.environ["PIXELA_USERNAME"]
TOKEN = os.environ["PIXELA_TOKEN"]
THANKS_CODE = os.environ["PIXELA_THANKS_CODE"]

PIXELA_ENDPOINT = "https://pixe.la/v1/users"
TOTAL_GRAPH_ID = "tr-trackertotal"


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

    create_graph(TOTAL_GRAPH_ID)

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

    # 1) get all graph IDs
    graphs = s.get(f"https://pixe.la/v1/users/{USERNAME}/graphs").json()["graphs"]

    hits = []
    for g in graphs:
        gid = g["id"]
        r = s.get(f"https://pixe.la/v1/users/{USERNAME}/graphs/{gid}/{DATE}")
        if r.status_code == 200 and gid.startswith("tr-"):
            qty = r.json().get("quantity")
            hits.append({"graphID": gid, "name": g.get("name"), "quantity": qty})

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

def update_total_tracker(date: str, optional_data: str = ""):
    total_minutes = 0
    for graph in get_graph_list(date):
        total_minutes += int(graph["quantity"])
    
    if total_minutes == 0:
        delete_pixel(date,TOTAL_GRAPH_ID)
    else:
        add_pixel(TOTAL_GRAPH_ID,date,str(total_minutes),optional_data)

def delete_pixel(date: str, graph_id: str):
    endpoint = f"https://pixe.la/v1/users/{USERNAME}/graphs/{graph_id}/{date}"

    headers = {"X-USER-TOKEN": TOKEN
        }
    response = requests.delete(url=endpoint, headers=headers)
    print(f"Delete pixel for {graph_id}: {response.text}")

# --- Pixela user and total tracker graph setup ---
# create_user()
