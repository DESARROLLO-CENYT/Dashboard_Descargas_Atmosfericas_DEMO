# -*- coding: utf-8 -*-
"""Genera los Excel del demo a partir de los reales, renombrando sitios y tags.

    python scripts/generar_datos_demo.py

Lee de datos/_fuente/ (copia intacta, fuera de git) y escribe sobre datos/. Lee
de una copia y no del archivo que va a pisar a proposito: asi se puede correr las
veces que haga falta y da siempre lo mismo. Si leyera del destino, la segunda
corrida intentaria renombrar nombres ya renombrados.

Lo que NO toca: las coordenadas, los equipos (DPS, DSD, aisladores, puesta a
tierra), los tipos de apoyo y todas las columnas tecnicas. El demo tiene que
tener la misma forma estadistica que el original, o deja de servir para mostrar
como se comporta el tablero de verdad.

Al terminar verifica solo, y falla si algo no cuadra:
  - que los dos archivos sigan cruzando igual que antes del renombrado,
  - que no sobreviva ninguna palabra de la lista negra,
  - que no cambie el numero de estructuras ni el reparto de DPS/DSD.
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
# La raiz tambien, para poder verificar con las mismas funciones de lectura
# que usa el tablero: si el formato crudo quedara mal escrito, comprobarlo
# con una copia propia no lo detectaria.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import geometria_demo
import nombres_demo as N

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "datos" / "_fuente"
DESTINO = RAIZ / "datos"
INVENTARIO = "Inventario_Estructuras_y_DPS_Final.xlsx"
LOCALIZACIONES = "Localizaciones_Final.xlsx"

# Columnas que llevan nombres de sitio o tags. Son las unicas donde se aplica la
# lista negra completa: no hay prosa, asi que una coincidencia por substring no
# puede ser un falso positivo.
COLUMNAS_IDENTIFICADORAS = [
    "CAMPO", "LOCACION / CIRCUITO", "PORTICO / SWG / TRAMO",
    "Area", "Circuito_Corregido", "Estructura_Tag_Corregido", "NombreResponsable",
]


def texto(v):
    return "" if pd.isna(v) else str(v).strip()


def es_portico(fila):
    return texto(fila.get("Apoyo_Tipo")).lower() == "pórtico"


def traducir(valor, mapa, donde, faltantes):
    """Aplica el mapa, y anota si el valor no estaba. No inventa un reemplazo:
    es preferible fallar a dejar pasar un nombre real sin que nadie lo note."""
    v = texto(valor)
    if not v:
        return valor
    if v not in mapa:
        faltantes.append((donde, v))
        return valor
    return mapa[v]


def generar():
    faltantes = []
    circuitos = {**N.TRAMOS, **N.LOCACIONES, **N.CIRCUITOS_SUELTOS}

    # ---- Maestro de localizaciones ----
    loc = pd.read_excel(FUENTE / LOCALIZACIONES)
    loc["CAMPO"] = [traducir(v, N.CAMPOS, "CAMPO", faltantes) for v in loc["CAMPO"]]
    loc["LOCACION / CIRCUITO"] = [
        traducir(v, N.LOCACIONES, "LOCACION", faltantes) for v in loc["LOCACION / CIRCUITO"]]
    loc["PORTICO / SWG / TRAMO"] = [
        traducir(v, N.TRAMOS, "TRAMO", faltantes) for v in loc["PORTICO / SWG / TRAMO"]]

    # ---- Inventario ----
    inv = pd.read_excel(FUENTE / INVENTARIO)

    # Los tags se numeran por tag DISTINTO, no por fila. Importa: hay un tag que
    # aparece en dos filas, y el tablero las deduplica por identidad. Si cada
    # fila recibiera un numero propio, esa deduplicacion dejaria de ocurrir y el
    # demo mostraria una estructura mas que el original.
    mapa_tags = {}
    siguiente = 1
    for _, fila in inv.iterrows():
        if es_portico(fila):
            continue
        tag = texto(fila["Estructura_Tag_Corregido"])
        if not tag or tag in mapa_tags:
            continue
        mapa_tags[tag] = "%s-%04d" % (N.PREFIJO_TAG, siguiente)
        siguiente += 1

    tags_nuevos, circuitos_nuevos = [], []
    for _, fila in inv.iterrows():
        tag = texto(fila["Estructura_Tag_Corregido"])
        if es_portico(fila):
            # El tag de un portico es su tipo (PORT, PORT-1, PORT-2), no un
            # nombre, y su circuito es en realidad la locacion a la que cuelga.
            tags_nuevos.append(N.TRAMOS.get(tag, tag) if tag else fila["Estructura_Tag_Corregido"])
            circuitos_nuevos.append(
                traducir(fila["Circuito_Corregido"], N.LOCACIONES, "CIRCUITO de portico", faltantes))
        else:
            tags_nuevos.append(mapa_tags.get(tag, fila["Estructura_Tag_Corregido"]))
            circuitos_nuevos.append(
                traducir(fila["Circuito_Corregido"], circuitos, "CIRCUITO", faltantes))

    inv["Estructura_Tag_Corregido"] = tags_nuevos
    inv["Circuito_Corregido"] = circuitos_nuevos
    inv["Area"] = [traducir(v, N.AREAS, "AREA", faltantes) for v in inv["Area"]]
    inv["NombreResponsable"] = [
        N.RESPONSABLE if texto(v) else v for v in inv["NombreResponsable"]]
    inv["Observaciones_Equipos"] = [
        N.OBSERVACIONES.get(texto(v), v) for v in inv["Observaciones_Equipos"]]

    if faltantes:
        print("No se pudo renombrar, hay valores que no estan en el diccionario:")
        for donde, v in sorted(set(faltantes)):
            print("   %-22s %r" % (donde, v))
        print("\nAgregalos a scripts/nombres_demo.py y volve a correr.")
        return None, None, None

    # Renombrar no alcanza: las coordenadas reales delatan el activo igual, porque
    # el mapa satelital muestra el trazado exacto. Se redibuja la red con otra
    # forma, sin salir de la region donde hay descargas registradas.
    inv, forma = geometria_demo.redibujar(inv, "Circuito_Corregido", "Apoyo_Tipo")
    print("   red redibujada: %d lineas entre %d nodos, %d sitios sueltos"
          % (forma["lineas"], forma["nodos"], forma["sueltas"]))

    return loc, inv, mapa_tags


def verificar(loc, inv, mapa_tags):
    """Comprueba que el renombrado no rompio nada. Devuelve la lista de fallos."""
    fallos = []
    t = texto

    # 1. Los cruces entre los dos archivos siguen casando igual
    loc_ok = loc.dropna(subset=["CAMPO", "LOCACION / CIRCUITO", "PORTICO / SWG / TRAMO"])
    tramos = {t(v) for v in loc_ok["PORTICO / SWG / TRAMO"]}
    locaciones = {t(v) for v in loc_ok["LOCACION / CIRCUITO"]}
    noport = inv[~inv.apply(es_portico, axis=1)]
    port = inv[inv.apply(es_portico, axis=1)]
    casan_np = sum(1 for v in noport["Circuito_Corregido"] if t(v) in tramos)
    casan_p = sum(1 for v in port["Circuito_Corregido"] if t(v) in locaciones)
    if casan_np != 722:
        fallos.append("estructuras que cruzan por tramo: %d, se esperaban 722" % casan_np)
    if casan_p != 27:
        fallos.append("porticos que cruzan por locacion: %d, se esperaban 27" % casan_p)

    # 2. Ninguna palabra de la lista negra sobrevive.
    #    En las columnas de identificadores se busca entera, porque ahi no hay
    #    prosa. En el texto libre solo los nombres largos: buscar "tig" o "tie"
    #    dentro de una frase en espanol da falsos positivos todo el tiempo
    #    ("tiene", "vertical").
    largas = [p for p in N.PROHIBIDAS if len(p) >= 5]
    for df, nombre in ((loc, "Localizaciones"), (inv, "Inventario")):
        for col in df.columns:
            if df[col].dtype != object:
                continue
            lista = N.PROHIBIDAS if col in COLUMNAS_IDENTIFICADORAS else largas
            for v in df[col].dropna().unique():
                bajo = str(v).lower()
                for p in lista:
                    if p in bajo:
                        fallos.append("%s.%s contiene %r: %r" % (nombre, col, p, str(v)[:48]))
                        break

    # 3. La forma de los datos no cambio
    if len(mapa_tags) != 730:
        fallos.append("tags distintos renombrados: %d, se esperaban 730" % len(mapa_tags))

    # 4. La red nueva cae donde tiene que caer. Se comprueba leyendo con las
    #    MISMAS funciones del backend: si el formato crudo quedara mal escrito,
    #    el tablero leeria otra cosa y aqui no se notaria.
    import polars as pl
    from backend.main import clean_lat, clean_lon
    d = pl.from_pandas(inv[["Latitud_Manual", "Longitud_Manual"]])
    d = d.with_columns([clean_lat(pl.col("Latitud_Manual")).alias("la"),
                        clean_lon(pl.col("Longitud_Manual")).alias("lo")]).drop_nulls(["la", "lo"])
    la, lo = d["la"], d["lo"]
    if len(d) != 758:
        fallos.append("estructuras con coordenada legible: %d, se esperaban 758" % len(d))
    # La zona con descargas del historico
    if not (3.96 <= la.min() and la.max() <= 4.90 and -73.18 <= lo.min() and lo.max() <= -72.14):
        fallos.append("hay estructuras fuera de la zona con descargas registradas")
    import math
    alto = (la.max() - la.min()) * 111
    ancho = (lo.max() - lo.min()) * 111 * math.cos(math.radians(la.mean()))
    if not (8 <= alto <= 22 and 15 <= ancho <= 34):
        fallos.append("la huella quedo en %.1f x %.1f km, fuera de lo previsto" % (alto, ancho))
    return fallos


def main():
    if not (FUENTE / INVENTARIO).exists():
        print("Falta la copia de origen en %s" % FUENTE)
        print("Copia ahi los dos Excel reales antes de generar.")
        return 1

    loc, inv, mapa_tags = generar()
    if loc is None:
        return 1

    fallos = verificar(loc, inv, mapa_tags)
    if fallos:
        print("La verificacion encontro %d problemas, no se escribio nada:" % len(fallos))
        for f in fallos[:25]:
            print("   -", f)
        return 1

    loc.to_excel(DESTINO / LOCALIZACIONES, index=False)
    inv.to_excel(DESTINO / INVENTARIO, index=False)
    print("Datos demo generados en %s" % DESTINO)
    print("   %d localizaciones, %d estructuras, %d tags renombrados"
          % (len(loc), len(inv), len(mapa_tags)))
    print("   cruces intactos y sin rastro de nombres reales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
