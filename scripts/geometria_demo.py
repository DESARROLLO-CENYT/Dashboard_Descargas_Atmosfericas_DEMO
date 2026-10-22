# -*- coding: utf-8 -*-
"""Redibuja la red electrica del demo: trazados nuevos, misma zona de rayos.

Las coordenadas reales delatan el activo aunque los nombres sean ficticios: el
mapa satelital muestra el trazado exacto y cualquiera que ubique la zona lo
reconoce. Este modulo genera una red con OTRA forma, sin salirse de la region
donde hay descargas registradas, para que el demo siga teniendo impactos reales
sobre estructuras ficticias.

Como se construye, y por que asi:

La red no es un monton de lineas sueltas: los circuitos se llaman por sus dos
extremos ("BOREAL - AUSTRAL", "N1 - N6"), asi que forman un grafo. Si cada
circuito se dibujara por su cuenta, los que comparten subestacion terminarian
lejos unos de otros y el conjunto no se leeria como una red. Por eso primero se
colocan los nodos y despues se tiende cada linea entre los suyos: los anillos
cierran y las derivaciones salen de donde deben.

El largo de cada linea no se elige: lo impone su cantidad de estructuras por el
paso real entre postes (mediana 104 m). Cuando dos nodos quedan mas cerca que
eso, la linea no se acorta sino que serpentea para absorber la diferencia, que es
justo lo que hace una linea de verdad siguiendo vias y linderos.
"""
import math
import random
import re

import numpy as np

# Ventana destino, elegida midiendo la densidad de descargas del historico: es
# la que mas actividad concentra (3,8 % del total, contra 2,9 % de la zona
# actual) y no se solapa con la posicion real de la red.
#
# La longitud no puede salirse de la franja -72.x: clean_lon() en backend/main.py
# fuerza ese prefijo al leer el Excel, asi que cualquier valor fuera de ella se
# leeria mal.
LAT_BASE, LON_BASE = 4.5285, -72.9520
ALTO_KM, ANCHO_KM = 14.0, 25.0

# Paso entre estructuras consecutivas, medido sobre la red real.
PASO_MEDIANO = 104.0
PASO_MIN, PASO_MAX = 55.0, 132.0

# Fija el azar. Misma entrada, misma red: sin esto cada corrida moveria todo y
# las capturas del demo dejarian de servir.
SEMILLA = 20261008

GRADOS_POR_KM_LAT = 1 / 111.0


def _grados_por_km_lon(lat):
    return 1 / (111.0 * math.cos(math.radians(lat)))


def _extremos(circuito):
    """Los dos nodos que une un circuito, deducidos de su nombre.

    Los nombres compuestos ("N1 - N6 / N7 - N6 TR3") describen un tramo
    compartido por dos circuitos; se toma el primero, que es el que da el
    recorrido. El sufijo TRn numera el tramo y no es un extremo.
    """
    nombre = str(circuito).split("/")[0]
    nombre = re.sub(r"\s+TR\d+\s*$", "", nombre).strip()
    partes = [p.strip() for p in nombre.split("-") if p.strip()]
    if len(partes) >= 2:
        return partes[0], partes[1]
    return (partes[0], None) if partes else (nombre, None)


def _colocar_nodos(aristas, nodos, azar):
    """Reparte los nodos en la huella y los acomoda para que cada linea quepa.

    Relajacion simple: cada arista tira de sus dos nodos hacia la distancia que
    necesita, y los nodos se repelen para no amontonarse. Con 30 pasadas basta;
    no hace falta un optimo, solo que ninguna linea quede imposible de tender.
    """
    pos = {n: np.array([azar.uniform(0, ANCHO_KM), azar.uniform(0, ALTO_KM)])
           for n in nodos}
    # Se busca que los nodos queden algo mas cerca que el largo de su linea: la
    # holgura es la que deja serpentear, y una linea recta se ve artificial.
    objetivo = {par: largo * 0.62 for par, largo in aristas.items()}

    for _ in range(300):
        empuje = {n: np.zeros(2) for n in nodos}
        for (a, b), meta in objetivo.items():
            d = pos[b] - pos[a]
            dist = max(np.linalg.norm(d), 1e-6)
            correccion = (dist - meta) / dist * d * 0.1
            empuje[a] += correccion
            empuje[b] -= correccion
        lista = list(nodos)
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                d = pos[b] - pos[a]
                dist = max(np.linalg.norm(d), 1e-6)
                if dist < 1.5:
                    repulsion = (1.5 - dist) / dist * d * 0.25
                    empuje[a] -= repulsion
                    empuje[b] += repulsion
        for n in nodos:
            pos[n] = pos[n] + empuje[n]
            pos[n][0] = min(max(pos[n][0], 0.5), ANCHO_KM - 0.5)
            pos[n][1] = min(max(pos[n][1], 0.5), ALTO_KM - 0.5)
    return pos


def _trazar(origen, destino, largo_km, azar):
    """Una linea de 'largo_km' entre dos puntos, como corre una de verdad.

    Tramos rectos de uno a tres kilometros con giros marcados entre ellos, no un
    serpenteo continuo: una linea electrica sigue vias y linderos, y una curva
    suave y constante se lee como un rio, no como infraestructura.

    Cuando los dos nodos estan mas cerca que el largo que impone la cantidad de
    estructuras, la holgura se gasta desviandose del rumbo directo; cuando ya
    queda justo, se apunta derecho al destino para llegar.
    """
    puntos = [origen.copy()]
    actual = origen.copy()
    recorrido = 0.0
    rumbo = None

    while recorrido < largo_km * 0.97:
        hacia = destino - actual
        falta_destino = float(np.linalg.norm(hacia))
        falta_total = largo_km - recorrido
        directo = hacia / max(falta_destino, 1e-9)

        if falta_total <= falta_destino * 1.08 or falta_destino < 0.4:
            rumbo = directo                      # ya no sobra: derecho al nodo
        else:
            # Holgura que gastar. Se desvia, pero sin alejarse del destino mas
            # de lo que el presupuesto de largo permite recuperar.
            margen = min(1.25, (falta_total / max(falta_destino, 0.3) - 1.0) * 1.6)
            angulo = math.atan2(directo[1], directo[0]) + azar.uniform(-margen, margen)
            rumbo = np.array([math.cos(angulo), math.sin(angulo)])

        tramo = min(azar.uniform(0.8, 3.0), falta_total)
        actual = actual + rumbo * tramo
        actual[0] = min(max(actual[0], 0.3), ANCHO_KM - 0.3)
        actual[1] = min(max(actual[1], 0.3), ALTO_KM - 0.3)
        puntos.append(actual.copy())
        recorrido += tramo

    puntos.append(destino.copy())
    return np.array(puntos)


def _repartir(puntos, cuantas, azar):
    """Coloca 'cuantas' estructuras sobre la linea, con el paso real medido."""
    pasos = np.array([min(max(azar.gauss(PASO_MEDIANO, 22), PASO_MIN), PASO_MAX)
                      for _ in range(cuantas - 1)])
    acumulado = np.concatenate([[0.0], np.cumsum(pasos)]) / 1000.0

    largos = np.concatenate([[0.0], np.cumsum(
        np.linalg.norm(np.diff(puntos, axis=0), axis=1))])
    total = largos[-1]
    if acumulado[-1] > total:              # la linea quedo corta: se reescala
        acumulado *= total / acumulado[-1]
    return np.column_stack([np.interp(acumulado, largos, puntos[:, 0]),
                            np.interp(acumulado, largos, puntos[:, 1])])


def _a_grados(xy_km):
    lat = LAT_BASE + xy_km[:, 1] * GRADOS_POR_KM_LAT
    lon = LON_BASE + xy_km[:, 0] * _grados_por_km_lon(LAT_BASE)
    return lat, lon


def crudo_lat(lat):
    """Formato en el que el Excel guarda la latitud (clean_lat lee los digitos
    y pone la coma despues del primero)."""
    return float(int(round(lat * 1e7)))


def crudo_lon(lon):
    return float(-int(round(abs(lon) * 1e7)))


def redibujar(inv, columna_circuito, columna_tipo):
    """Reemplaza las coordenadas del inventario por la red nueva.

    Devuelve (inventario, resumen). No toca ninguna otra columna: los equipos,
    los tipos de apoyo y la pertenencia a cada circuito viajan con su fila.
    """
    azar = random.Random(SEMILLA)
    inv = inv.copy()
    es_portico = inv[columna_tipo].astype(str).str.strip().str.lower() == "pórtico"

    # Las filas que ya venian sin coordenada legible se quedan sin ella. El
    # tablero las descarta, y darles una haria aparecer estructuras que el
    # original no tiene: serian 760 donde habia 758.
    import polars as pl
    from backend.main import clean_lat, clean_lon
    leidas = pl.from_pandas(inv[["Latitud_Manual", "Longitud_Manual"]]).with_columns([
        clean_lat(pl.col("Latitud_Manual")).alias("la"),
        clean_lon(pl.col("Longitud_Manual")).alias("lo")])
    tiene_coord = (~leidas["la"].is_null() & ~leidas["lo"].is_null()).to_list()
    tiene_coord = {fila: ok for fila, ok in zip(inv.index, tiene_coord)}

    # ---- El grafo que forman los circuitos ----
    lineas = {}
    for circuito, grupo in inv[~es_portico].groupby(columna_circuito, sort=True):
        filas = [i for i in grupo.index if tiene_coord[i]]
        if len(filas) >= 2:
            lineas[str(circuito)] = filas

    aristas, nodos = {}, set()
    for circuito, filas in lineas.items():
        a, b = _extremos(circuito)
        if b is None:                       # ramal sin segundo extremo
            b = "%s·fin" % a
        nodos.update([a, b])
        largo = (len(filas) - 1) * PASO_MEDIANO / 1000.0
        aristas[(a, b)] = max(aristas.get((a, b), 0.0), largo)

    pos = _colocar_nodos(aristas, sorted(nodos), azar)

    # ---- Se tiende cada linea y se reparten sus estructuras ----
    for circuito, filas in sorted(lineas.items()):
        a, b = _extremos(circuito)
        if b is None:
            b = "%s·fin" % a
        largo = (len(filas) - 1) * PASO_MEDIANO / 1000.0
        puntos = _trazar(pos[a], pos[b], largo, azar)
        xy = _repartir(puntos, len(filas), azar)
        lat, lon = _a_grados(xy)
        for i, fila in enumerate(filas):
            inv.at[fila, "Latitud_Manual"] = crudo_lat(lat[i])
            inv.at[fila, "Longitud_Manual"] = crudo_lon(lon[i])

    # ---- Porticos y circuitos de una sola estructura ----
    # Son sitios sueltos, no lineas. Se siembran separados entre si para que no
    # se amontonen sobre el trazado.
    en_linea = {i for filas in lineas.values() for i in filas}
    sueltas = [i for i in inv.index if tiene_coord[i] and i not in en_linea]
    colocados = []
    for fila in sueltas:
        for _ in range(200):
            p = np.array([azar.uniform(0.5, ANCHO_KM - 0.5),
                          azar.uniform(0.5, ALTO_KM - 0.5)])
            if all(np.linalg.norm(p - q) > 0.6 for q in colocados):
                break
        colocados.append(p)
        lat, lon = _a_grados(p.reshape(1, 2))
        inv.at[fila, "Latitud_Manual"] = crudo_lat(lat[0])
        inv.at[fila, "Longitud_Manual"] = crudo_lon(lon[0])

    resumen = {"lineas": len(lineas), "nodos": len(nodos), "sueltas": len(sueltas)}
    return inv, resumen
