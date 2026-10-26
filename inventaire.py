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

def get_stats(url, session, container_id):
    try:
        response = session.get(f"{url}/containers/{container_id}/stats?stream=false", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des infos du conteneur : {e}")
        return None

def get_cpu_usage(stats):
    # Comment je suis arrivé ici : le cpu stats de docker est un nombre qui est mis à jour à chaque interval (que je ne connais pas) et qui est un compteur cumulatif depuis le démarrage du conteneur au lieu d'un chiffre en live. Donc on fait - precpu, qui correspond au nombre avant le dernier cumul, ce qui nous donne le nombre à l'instant T.
    # Le reste est une simple formule mathématique.
    cpu_stats = stats.get("cpu_stats", {})
    precpu_stats = stats.get("precpu_stats", {})
    delta_cpu = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
    delta_system = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
    cpu_usage = (delta_cpu / delta_system) if delta_system > 0 else 0
    online_cpus = cpu_stats.get("online_cpus", 1)
    usage = cpu_usage * online_cpus * 100
    return usage

def get_memory_usage(stats):
    todo

if __name__ == "__main__":
    url = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375")
    docker_session = requests.Session()
    containers = list_containers(url, docker_session)
    if containers:
        print("Conteneurs disponibles :")
        for container in containers:
            id = container.get("Id", "Unknown")
            nom = container.get("Names", ["/Unknown"])[0][1:]
            state = container.get("State", "Unknown")
            if state == "running":
                print(f"Le conteneur {nom} est en cours d'exécution.")
                stats = get_stats(url, docker_session, id)
                print(f"Stats du conteneur {nom} : {stats}")
                cpu_usage = get_cpu_usage(stats)
                print(f"Utilisation CPU du conteneur {nom} : {cpu_usage:.2f}%")
    else:
        print("Aucun conteneur.")