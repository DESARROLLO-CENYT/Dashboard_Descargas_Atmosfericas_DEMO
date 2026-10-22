-- =============================================================================
-- 002 - Una foto de cache por tablero
--
-- POR QUE
-- El 001 guarda la foto en una sola fila (id = 1), pensado para un unico
-- tablero. Hoy hay dos contra la misma base: el de produccion y el demo, que
-- dibuja una red ficticia en OTRA ventana de coordenadas para no delatar el
-- activo real. Sus zonas se solapan pero ninguna contiene a la otra:
--
--     produccion  lat 4,3180 - 4,5409   lon -72,8205 - -72,5029
--     demo        lat 4,4905 - 4,6909   lon -72,9834 - -72,6871
--
-- Una foto solo sirve si su caja cubre la zona que se esta pidiendo, asi que
-- con una sola fila cada tablero encuentra la foto del otro, la descarta, arma
-- su cache desde las filas (~3,4 MB) y la pisa. El siguiente arranque del otro
-- repite el ciclo: los dos quedan sin foto util para siempre y el egress de
-- cada uno pasa de ~225 MB a ~1,2 GB al mes, sobre los 5 GB del plan.
--
-- QUE HACE
-- Permite varias filas, una por tablero, y agrega una funcion que recibe el id.
--
-- COMPATIBILIDAD: PRODUCCION NO SE TOCA
-- La funcion de 4 argumentos del 001 sigue existiendo igual y sigue escribiendo
-- la fila 1, y el tablero de produccion lee con WHERE id = 1, asi que nunca ve
-- la fila del demo. No hay que redesplegar produccion ni cambiar su codigo.
--
-- COMO SE APLICA
-- Una sola vez, con el usuario postgres, en el SQL Editor de Supabase. Es
-- idempotente: correrlo de nuevo no rompe nada ni borra las fotos.
-- Requiere tener aplicado el 001.
--
-- REPARTO DE IDS
--     1  tablero de produccion (el valor por defecto, el del 001)
--     2  demo publico (FOTO_ID=2 en las variables de Render)
--   3-9  libres para otros tableros sobre la misma base
-- =============================================================================

DO $$
BEGIN
    IF to_regclass('public.gpk_tablero_foto') IS NULL THEN
        RAISE EXCEPTION 'Falta la tabla gpk_tablero_foto: aplicar primero sql/001_foto_tablero.sql';
    END IF;
END $$;

-- El CHECK (id = 1) del 001 es una restriccion de columna, asi que Postgres le
-- puso el nombre automatico. Se busca por su definicion en vez de suponerlo:
-- un nombre inventado dejaria la restriccion vieja en pie y el INSERT con
-- id = 2 fallaria igual.
DO $$
DECLARE
    c text;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'public.gpk_tablero_foto'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%id = 1%'
    LOOP
        EXECUTE format('ALTER TABLE public.gpk_tablero_foto DROP CONSTRAINT %I', c);
    END LOOP;
END $$;

-- Tope bajo a proposito: el id lo pone una variable de entorno, y un valor
-- disparatado por un dedazo no debe llenar la base de fotos de ~0,6 MB.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.gpk_tablero_foto'::regclass
          AND conname = 'gpk_tablero_foto_id_valido'
    ) THEN
        ALTER TABLE public.gpk_tablero_foto
            ADD CONSTRAINT gpk_tablero_foto_id_valido CHECK (id BETWEEN 1 AND 9);
    END IF;
END $$;

COMMENT ON COLUMN public.gpk_tablero_foto.id IS
    'Que tablero guardo la foto: 1 produccion, 2 demo publico, 3-9 libres. Cada uno solo lee la suya (WHERE id = ...), porque una foto de otra zona no le sirve.';

-- Misma funcion del 001 con el id por delante. Se agrega como sobrecarga en vez
-- de cambiar la de 4 argumentos: produccion la sigue llamando tal cual.
CREATE OR REPLACE FUNCTION public.guardar_foto_tablero(
    p_id        smallint,
    p_formato   smallint,
    p_caja      jsonb,
    p_huella    text,
    p_foto      bytea
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
-- search_path fijo: sin esto, quien ejecuta podria hacer que la funcion use
-- objetos suyos con el mismo nombre (riesgo clasico de SECURITY DEFINER).
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_id IS NULL OR p_id < 1 OR p_id > 9 THEN
        RAISE EXCEPTION 'Foto con id %: fuera del rango permitido (1 a 9)', p_id;
    END IF;

    IF octet_length(p_foto) > 20 * 1024 * 1024 THEN
        RAISE EXCEPTION 'Foto de % bytes: supera el tope de 20 MB', octet_length(p_foto);
    END IF;

    INSERT INTO public.gpk_tablero_foto (id, formato, caja, huella_global, bytes, generada_en, foto)
    VALUES (p_id, p_formato, p_caja, p_huella, octet_length(p_foto), now(), p_foto)
    ON CONFLICT (id) DO UPDATE
        SET formato       = EXCLUDED.formato,
            caja          = EXCLUDED.caja,
            huella_global = EXCLUDED.huella_global,
            bytes         = EXCLUDED.bytes,
            generada_en   = EXCLUDED.generada_en,
            foto          = EXCLUDED.foto;
END $$;

-- Permisos minimos, igual que en el 001: por defecto Postgres deja ejecutar
-- funciones nuevas a cualquiera, asi que se cierra y se abre solo al tablero.
REVOKE ALL ON FUNCTION public.guardar_foto_tablero(smallint, smallint, jsonb, text, bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.guardar_foto_tablero(smallint, smallint, jsonb, text, bytea) TO dashboard_readonly;

-- Cerrado a la API publica de Supabase (anon y authenticated). En un Postgres
-- local esos roles no existen: se revoca solo a los que haya.
DO $$
DECLARE
    r text;
BEGIN
    FOR r IN SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated') LOOP
        EXECUTE format(
            'REVOKE ALL ON FUNCTION public.guardar_foto_tablero(smallint, smallint, jsonb, text, bytea) FROM %I', r);
    END LOOP;
END $$;

-- La politica de lectura del 001 (FOR SELECT TO dashboard_readonly USING (true))
-- ya cubre las filas nuevas: no hace falta tocar RLS.
