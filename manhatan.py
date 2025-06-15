import math

def calcular_ruta_manhattan(origen, destino):
    ox, oy = origen['lat'], origen['lng']
    dx, dy = destino['lat'], destino['lng']

    delta_lat_km = abs(ox - dx) * 111
    delta_lon_km = abs(oy - dy) * 111 * abs(math.cos(math.radians((ox + dx) / 2)))
    distancia_km = delta_lat_km + delta_lon_km

    ruta = [
        {"lat": ox, "lng": oy},
        {"lat": dx, "lng": oy},
        {"lat": dx, "lng": dy}
    ]

    return ruta, distancia_km
