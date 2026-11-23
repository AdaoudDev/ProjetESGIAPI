import requests
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()   # reads .env and loads its variables


def list_containers(url, session):
    try:
        response = session.get(f"{url}/containers/json?all=true", timeout=10)
        response.raise_for_status()
    except requests.ConnectionError:
        sys.exit("Impossible de joindre le service. Est-il démarré ?")
    except requests.exceptions.RequestException as e:
        sys.exit(f"Erreur lors de la récupération des conteneurs : {e}")
    return response.json()

def get_stats(url, session, container_id):
    try:
        response = session.get(f"{url}/containers/{container_id}/stats?stream=false", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"Erreur HTTP : {e.response.status_code} - {e.response.reason}")
        if isinstance(e, requests.exceptions.ConnectionError):
            print(f"Erreur de connexion : {e}")
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
    # Docker donne la mémoire utilisée en octets, on convertit en Mo en divisant par un octet deux fois (1024).
    memory_stats = stats.get("memory_stats", {})
    memory_usage = memory_stats.get("usage", 0)
    usage = memory_usage / 1024 / 1024 
    return usage

if __name__ == "__main__":
    url = os.environ.get("DOCKER_API_URL", "http://127.0.0.1:2375")
    docker_session = requests.Session()
    containers = list_containers(url, docker_session)
    inventaire = []
    if containers:
        print("Recherche des conteneurs...")
        for container in containers:
            container_id = container.get("Id", "Unknown")
            nom = container.get("Names", ["/Unknown"])[0][1:]
            image = container.get("Image", "Unknown")
            state = container.get("State", "Unknown")
            conteneur_info = {
                "id": container_id,
                "nom": nom,
                "image": image,
                "state": state
            }

            if state == "running":
                stats = get_stats(url, docker_session, container_id)
                if stats is None:
                    print(f"Impossible de récupérer les statistiques pour le conteneur {nom}.")
                    inventaire.append(conteneur_info)
                    continue
                cpu_usage = get_cpu_usage(stats)
                memory_usage = get_memory_usage(stats)
                conteneur_info["cpu_usage"] = cpu_usage
                conteneur_info["memory_usage"] = memory_usage
            
            inventaire.append(conteneur_info)
        running_containers = [c for c in inventaire if c.get("state") == "running"]
        print(f"Conteneurs : {len(containers)}")
        print(f"Conteneurs en cours d'exécution : {len(running_containers)}")
        print(f"Conteneurs arrêtés : {len([c for c in inventaire if c.get("state") == "exited"])}")
        print(f"Conteneurs en pause : {len([c for c in inventaire if c.get("state") == "paused"])}")
        print(f"Conteneurs en redémarrage : {len([c for c in inventaire if c.get("state") == "restarting"])}")
        if len(running_containers) > 0:
            average_cpu = sum(c.get("cpu_usage", 0) for c in running_containers) / len(running_containers)
            average_memory = sum(c.get("memory_usage", 0) for c in running_containers) / len(running_containers)
            print(f"Utilisation CPU moyenne : {average_cpu:.2f} %")
            print(f"Utilisation mémoire moyenne : {average_memory:.0f} Mo")
        else:
            print("Aucun conteneur en cours d'exécution. Impossible de calculer les moyennes CPU et mémoire.")
    else:
        print("Aucun conteneur.")
    date =datetime.now().isoformat()
    
    with open("inventaire.json", "w") as f:
        json.dump({"date": date, "containers": inventaire}, f, indent=4)
        print("Lecture des conteneurs terminée. Résultats sauvegardés dans inventaire.json.")
