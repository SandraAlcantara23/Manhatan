from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from manhatan import calcular_ruta_manhattan

app = Flask(__name__)
CORS(app)

# Diccionario con las coordenadas de los estados de México
coordenadas = {
    "Aguascalientes": (21.8853, -102.2916),
    "Baja California": (32.5343, -117.0382),
    "Campeche": (19.8301, -90.5349),
    "Chiapas": (16.7569, -93.1292),
    "Chihuahua": (28.6353, -106.0889),
    "Ciudad de México": (19.4326, -99.1332),
    "Durango": (24.0277, -104.6532),
    "Guanajuato": (21.0190, -101.2574),
    "Guerrero": (17.4392, -99.5451),
    "Hidalgo": (20.0911, -98.7624),
    "Jalisco": (20.6597, -103.3496),
    "México": (19.3574, -99.0860),
    "Michoacán": (19.5665, -101.7068),
    "Morelos": (18.6813, -99.1013),
    "Nayarit": (21.7514, -104.8455),
    "Nuevo León": (25.5922, -99.9962),
    "Oaxaca": (17.0732, -96.7266),
    "Puebla": (19.0414, -98.2063),
    "Querétaro": (20.5888, -100.3899),
    "Quintana Roo": (18.5211, -88.3258),
    "San Luis Potosí": (22.1565, -100.9855),
    "Sinaloa": (24.8081, -107.3940),
    "Sonora": (29.0729, -110.9559),
    "Tabasco": (17.8409, -92.6189),
    "Tamaulipas": (23.7369, -99.1411),
    "Tlaxcala": (19.3182, -98.2375),
    "Veracruz": (19.1738, -96.1342),
    "Yucatán": (20.7099, -89.0943),
    "Zacatecas": (22.7709, -102.5832)
}

def calcular_ruta_osrm(origen, destino):
    # Función para calcular la ruta usando el servicio OSRM
    url = f"http://router.project-osrm.org/route/v1/driving/{origen['lng']},{origen['lat']};{destino['lng']},{destino['lat']}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return [origen, destino], 0, 0
        data = response.json()
        coords = data['routes'][0]['geometry']['coordinates']
        distancia_metros = data['routes'][0]['distance']
        duracion_segundos = data['routes'][0]['duration']
        ruta = [{"lat": lat, "lng": lng} for lng, lat in coords]
        return ruta, distancia_metros, duracion_segundos
    except requests.RequestException:
        return [origen, destino], 0, 0

@app.route("/")
def index():
    # Renderiza la página principal
    return render_template("index.html")

@app.route("/calcular_ruta", methods=["POST"])
def calcular_ruta():
    # Endpoint para calcular la ruta entre dos estados
    datos = request.get_json()
    origen_nombre = datos["origen"]
    destino_nombre = datos["destino"]
    metodo = datos.get("metodo", "osrm")

    if origen_nombre not in coordenadas or destino_nombre not in coordenadas:
        return jsonify({"error": "Origen o destino no válido"}), 400

    lat1, lon1 = coordenadas[origen_nombre]
    lat2, lon2 = coordenadas[destino_nombre]
    origen = {"lat": lat1, "lng": lon1}
    destino = {"lat": lat2, "lng": lon2}

    if metodo == "manhattan":
        ruta, distancia_km = calcular_ruta_manhattan(origen, destino)
        duracion_min = distancia_km / 60 * 60  # Asumiendo 60 km/h
        distancia_metros = distancia_km * 1000
        duracion_segundos = duracion_min * 60
    else:
        ruta, distancia_metros, duracion_segundos = calcular_ruta_osrm(origen, destino)
        distancia_km = distancia_metros / 1000
        duracion_min = duracion_segundos / 60

    return jsonify({
        "origen": {"estado": origen_nombre, "lat": lat1, "lon": lon1},
        "destino": {"estado": destino_nombre, "lat": lat2, "lon": lon2},
        "distancia_km": round(distancia_km, 2),
        "duracion_min": round(duracion_min, 2),
        "ruta": ruta
    })

@app.route("/buscar_pois", methods=["POST"])
def buscar_pois():
    # Nuevo endpoint para buscar Puntos de Interés (POI)
    datos = request.get_json()
    lat = datos["lat"]
    lon = datos["lon"]
    poi_type = datos["poi_type"]
    radius = datos.get("radius", 5000)  # Radio de búsqueda en metros (5km por defecto)

    # Mapeo de tipos de POI a las etiquetas de Overpass API
    poi_map = {
        "hospitales": '"amenity"="hospital"',
        "escuelas": '"amenity"="school"',
        "restaurantes": '"amenity"="restaurant"',
        "gasolineras": '"amenity"="fuel"',
        "tiendas": '"shop"~"convenience|supermarket"'
    }

    if poi_type not in poi_map:
        return jsonify({"error": "Tipo de POI no válido"}), 400

    tag = poi_map[poi_type]
    
    # Consulta a la API Overpass
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node[{tag}](around:{radius},{lat},{lon});
      way[{tag}](around:{radius},{lat},{lon});
      relation[{tag}](around:{radius},{lat},{lon});
    );
    out center;
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    try:
        response = requests.post(overpass_url, data=overpass_query, timeout=25)
        response.raise_for_status() # Lanza un error si la petición falla
        data = response.json()
    except requests.RequestException as e:
        return jsonify({"error": f"Error al contactar Overpass API: {e}"}), 502

    # Procesamiento de la respuesta para extraer los datos de los POIs
    pois = []
    for element in data.get("elements", []):
        poi_info = {"name": element.get("tags", {}).get("name", "Sin nombre")}
        if element["type"] == "node":
            poi_info["lat"] = element.get("lat")
            poi_info["lon"] = element.get("lon")
        elif "center" in element:  # Para 'ways' y 'relations'
            poi_info["lat"] = element.get("center", {}).get("lat")
            poi_info["lon"] = element.get("center", {}).get("lon")
        
        # Asegurarse de que tenemos latitud y longitud antes de añadir
        if "lat" in poi_info and "lon" in poi_info:
            pois.append(poi_info)

    return jsonify(pois)


if __name__ == "__main__":
    app.run(debug=True)
