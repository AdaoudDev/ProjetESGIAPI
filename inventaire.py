import requests
import os
from dotenv import load_dotenv

load_dotenv()   # reads .env and loads its variables


def list_containers(url, session):
    try:
        response = session.get(f"{url}/containers/json?all=true", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Une erreur est survenue : {e}")
        return []


if __name__ == "__main__":
    url = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375")
    docker_session = requests.Session()
    containers = list_containers(url, docker_session)
    if containers:
        print("Conteneurs disponibles :")
        for container in containers:
            nom = container.get("Names", ["/Unnamed"])[0][1:]
            image = container.get("Image", "Unknown")
            state = container.get("State", "Unknown")
            print(f"nom : {nom}, image : {image}, state : {state}")
    else:
        print("Aucun conteneur.")