# -*- coding: utf-8 -*-
"""Diccionario de nombres del demo: real -> ficticio.

Este archivo es el unico sitio donde se decide como se llama cada cosa. El
generador (scripts/generar_datos_demo.py) no inventa nada: solo aplica lo que
esta aqui. Para cambiar un nombre, se cambia aqui y se vuelve a generar.

Los nombres reales de los campos son aves de los Llanos (Jacana, Chiricoca,
Guaco, Guala), asi que los ficticios se apartan a proposito de esa familia: usan
puntos cardinales para las zonas grandes y materiales para los satelites, de
forma que ni el criterio de nombrado se parezca al original.

Por que un diccionario explicito y no una regla automatica: son 58 nombres y se
leen de un vistazo. Una regla por substrings seria mas corta pero imposible de
auditar, y aqui lo que importa es poder mirar la lista y confirmar que no quedo
ningun nombre real.
"""

# Los tres campos de la jerarquia.
CAMPOS = {
    "JAC": "BOREAL",
    "TGN": "AUSTRAL",
    "CAMPO MENOR": "CENTRAL",
}

# Las 32 locaciones. Se conserva la forma del nombre original ("ANILLO X",
# "CTO X-Y", "DERIVACION X", o el sitio suelto) porque esa forma dice que es cada
# cosa en la red, y perderla haria el demo menos creible.
LOCACIONES = {
    "ANILLO JAC":               "ANILLO BOREAL",
    "ANILLO TGN":               "ANILLO AUSTRAL",
    "ANILLO TIG":               "ANILLO ÁMBAR",
    "CHIRICOCA":                "NÁCAR",
    "CTO TGN-JAC":              "CTO AUSTRAL-BOREAL",
    "CTO TSUR":                 "CTO AUSTRAL SUR",
    "CTO TUA/TT":               "CTO CORAL/N9",
    "DERIVACION TIGANAS":       "DERIVACION AUSTRALES",
    "DERIVACION TIGUI ESTE":    "DERIVACION ÁMBAR ESTE",
    "DERIVACION TUA-TARO TARO": "DERIVACION CORAL-MARFIL",
    "GUACO":                    "ÓPALO",
    "GUALA":                    "CUARZO",
    "JACANA B":                 "BOREAL B",
    "JACANA CENTRAL":           "BOREAL CENTRO",
    "JACANA CORCEL":            "BOREAL ESTE",
    "JACANA SUR":               "BOREAL SUR",
    "MAX":                      "MICA",
    "TARO TARO":                "MARFIL",
    "TIGANA":                   "AUSTRAL",
    "TIGANA A":                 "AUSTRAL A",
    "TIGANA B":                 "AUSTRAL B",
    "TIGANA SUR":               "AUSTRAL SUR",
    "TIGANA SUR B":             "AUSTRAL SUR B",
    "TIGANA SUR W":             "AUSTRAL SUR O",
    "TIGUI":                    "ÁMBAR",
    "TIGUI ESTE":               "ÁMBAR ESTE",
    "TIGUI SUR ESTE":           "ÁMBAR SURESTE",
    "TILO":                     "BASALTO",
    "TUA":                      "CORAL",
    "TUA A":                    "CORAL A",
    "TUA B":                    "CORAL B",
    "TUA FACILIDADES":          "CORAL FACILIDADES",
}

# Los 23 tramos. Son segmentos de red nombrados por sus dos extremos, asi que los
# ficticios siguen la misma idea: las zonas grandes conservan su nombre y las
# subestaciones intermedias pasan a nodos numerados. Los sufijos TR1/TR2/TR3 y
# los tramos compuestos con "/" se mantienen tal cual: son parte de como esta
# modelada la red, no un nombre.
#
# PORT, PORT-1 y PORT-2 NO se tocan. No son un nombre sino el tipo de la
# estructura, y que "PORT" se repita en veinte locaciones distintas es justo el
# caso que el backend resuelve con el par circuito + tag. Cambiarlos por algo
# unico haria desaparecer ese caso y el demo dejaria de ejercitarlo.
TRAMOS = {
    "JAC - JCB":                  "BOREAL - N1",
    "JAC - JCS":                  "BOREAL - N2",
    "JAC - TIG":                  "BOREAL - ÁMBAR",
    "JAC -TGN":                   "BOREAL - AUSTRAL",
    "JCB - TIE":                  "N1 - N6",
    "JCB - TIE / TISE - TIE TR3": "N1 - N6 / N7 - N6 TR3",
    "JCE - JCC / JP -JCC TR2":    "N3 - N4 / N5 - N4 TR2",
    "JCP - JCC TR1":              "N5 - N4 TR1",
    "JCS - JCE":                  "N2 - N3",
    "PDT-TT":                     "N8-N9",
    "PDT-TUA":                    "N8-CORAL",
    "PORT":                       "PORT",
    "PORT-1":                     "PORT-1",
    "PORT-2":                     "PORT-2",
    "TGA1-TGA3":                  "N10-N11",
    "TGN - PDT":                  "AUSTRAL - N8",
    "TGN-TGA":                    "AUSTRAL-N10",
    "TGN-TGB":                    "AUSTRAL-N12",
    "TGN-TSUR":                   "AUSTRAL-N13",
    "TGN3":                       "AUSTRAL3",
    "TIG -TISE / TISE - TIE TR1": "ÁMBAR -N7 / N7 - N6 TR1",
    "TISE -TIE TR2":              "N7 -N6 TR2",
    "TSUR-TSW":                   "N13-N14",
}

# Circuitos del inventario que no existen en el maestro. Se renombran igual, pero
# se mantienen huerfanos a proposito: el tablero ya sabe mostrarlos como "sin
# campo asignado" y ese camino tiene que seguir ejercitandose en el demo.
CIRCUITOS_SUELTOS = {
    "Derivación Buco": "Derivación N15",
}

# La columna Area. Los dos valores genericos se quedan como estan porque no
# identifican nada.
AREAS = {
    "JACANA": "BOREAL",
    "TIGANA": "AUSTRAL",
    "CAMPO MENOR": "CENTRAL",
    "PÓRTICO DERIVACIÓN": "PÓRTICO DERIVACIÓN",
    "OTRO": "OTRO",
}

# Quien levanto el inventario en campo.
RESPONSABLE = "OPERADOR CEN&T"

# Texto libre que menciona un sitio real. El resto de las observaciones (69 de
# templete y 19 de equipos) son tecnicas y no nombran nada, asi que no se tocan:
# son las que le dan al demo el detalle de un inventario de verdad.
OBSERVACIONES = {
    "DPS solo para circuito Jacana pozos": "DPS solo para circuito de pozos",
}

# Prefijo de los tags de estructura. Las 733 estructuras que no son portico pasan
# a EST-0001, EST-0002... numeradas en el orden en que aparecen en el Excel, que
# es estable: la misma entrada da siempre la misma salida y las capturas no
# cambian entre corridas.
PREFIJO_TAG = "EST"

# Palabras que no pueden sobrevivir en los archivos generados. La verificacion
# falla si encuentra cualquiera de estas.
PROHIBIDAS = [
    "geopark", "gpk", "llanos",
    "jacana", "jac", "tigana", "tgn", "tigui", "tig", "tua", "taro",
    "chiricoca", "guaco", "guala", "tilo", "corcel", "buco",
    "jcb", "jcs", "jce", "jcc", "jcp", "tie", "tise", "pdt", "tga", "tgb",
    "tsur", "tsw",
]
