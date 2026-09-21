/*
FashionStore - Upgrade de Neon desde Ciclo 2 a Ciclo 3.

Requisito: public.alembic_version debe estar en 0003_ciclo2_linea_invariante
o en una version posterior de Ciclo 3. No elimina ni reemplaza datos.
Equivale a las migraciones Alembic 0004_ciclo3_backend y
0005_ciclo3_correcciones.
*/
BEGIN;

DO $precondiciones$
DECLARE version_actual text;
BEGIN
  IF to_regclass('comercial.ventas') IS NULL
     OR to_regclass('comercial.pagos') IS NULL
     OR to_regclass('catalogo.variantes_producto') IS NULL THEN
    RAISE EXCEPTION 'Falta el esquema de Ciclo 2. Ejecute y verifique primero 01_esquema_hasta_ciclo2.sql';
  END IF;
  SELECT version_num INTO version_actual FROM public.alembic_version LIMIT 1;
  IF version_actual IS NULL OR version_actual NOT IN (
    '0003_ciclo2_linea_invariante','0004_ciclo3_backend','0005_ciclo3_correcciones'
  ) THEN
    RAISE EXCEPTION 'Version Alembic no compatible: %', coalesce(version_actual,'NULL');
  END IF;
END
$precondiciones$;

CREATE SCHEMA IF NOT EXISTS inteligencia;

DO $tipo$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
    WHERE n.nspname='comercial' AND t.typname='estado_entrega'
  ) THEN
    CREATE TYPE comercial.estado_entrega AS ENUM
      ('SOLICITADO','PREPARADO','LISTO_RECOJO','EN_REPARTO','RECOGIDO','ENTREGADO','CANCELADO');
  END IF;
END
$tipo$;

CREATE TABLE IF NOT EXISTS comercial.carritos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id uuid NOT NULL REFERENCES seguridad.clientes(usuario_id),
  canal varchar(10) NOT NULL DEFAULT 'WEB' CHECK(canal IN ('WEB','MOVIL')),
  estado varchar(20) NOT NULL DEFAULT 'ACTIVO' CHECK(estado IN ('ACTIVO','CONVERTIDO','ABANDONADO')),
  creada_en timestamptz NOT NULL DEFAULT now(),
  actualizada_en timestamptz NOT NULL DEFAULT now(),
  convertida_en timestamptz,
  venta_id uuid REFERENCES comercial.ventas(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_carritos_activo_por_cliente_canal
  ON comercial.carritos(cliente_id,canal) WHERE estado='ACTIVO';
CREATE INDEX IF NOT EXISTS idx_carritos_cliente_estado
  ON comercial.carritos(cliente_id,estado);

CREATE TABLE IF NOT EXISTS comercial.detalles_carrito (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  carrito_id uuid NOT NULL REFERENCES comercial.carritos(id) ON DELETE CASCADE,
  variante_id uuid NOT NULL REFERENCES catalogo.variantes_producto(id),
  cantidad integer NOT NULL CHECK(cantidad>0),
  agregado_en timestamptz NOT NULL DEFAULT now(),
  actualizado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_detalle_carrito_carrito_variante UNIQUE(carrito_id,variante_id)
);
CREATE INDEX IF NOT EXISTS idx_detalle_carrito_carrito
  ON comercial.detalles_carrito(carrito_id);

CREATE TABLE IF NOT EXISTS comercial.pedidos_entrega (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  venta_id uuid NOT NULL UNIQUE REFERENCES comercial.ventas(id) ON DELETE CASCADE,
  sucursal_id uuid NOT NULL REFERENCES organizacion.sucursales(id),
  cliente_id uuid NOT NULL REFERENCES seguridad.clientes(usuario_id),
  modalidad varchar(20) NOT NULL CHECK(modalidad IN ('RECOJO','DELIVERY')),
  estado varchar(20) NOT NULL DEFAULT 'SOLICITADO'
    CHECK(estado IN ('SOLICITADO','PREPARADO','LISTO_RECOJO','EN_REPARTO','RECOGIDO','ENTREGADO','CANCELADO')),
  anillo_sucursal smallint,
  anillo_destino smallint,
  anillo_minimo smallint,
  anillo_maximo smallint,
  direccion text,
  tarifa_base numeric(12,2) NOT NULL DEFAULT 0 CHECK(tarifa_base>=0),
  incremento_anillo numeric(12,2) NOT NULL DEFAULT 0 CHECK(incremento_anillo>=0),
  costo_entrega numeric(12,2) NOT NULL DEFAULT 0 CHECK(costo_entrega>=0),
  codigo_recojo varchar(20),
  creada_en timestamptz NOT NULL DEFAULT now(),
  actualizada_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_pedidos_delivery_requiere_datos CHECK(
    modalidad='RECOJO' OR (direccion IS NOT NULL AND anillo_destino IS NOT NULL)
  ),
  CONSTRAINT ck_pedidos_recojo_sin_tarifa CHECK(modalidad='DELIVERY' OR costo_entrega=0)
);
CREATE INDEX IF NOT EXISTS idx_pedidos_sucursal_estado
  ON comercial.pedidos_entrega(sucursal_id,estado);
CREATE INDEX IF NOT EXISTS idx_pedidos_venta ON comercial.pedidos_entrega(venta_id);

CREATE TABLE IF NOT EXISTS catalogo.promociones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo varchar(40) NOT NULL UNIQUE,
  nombre varchar(180) NOT NULL,
  descripcion text,
  tipo varchar(20) NOT NULL CHECK(tipo IN ('PORCENTAJE','MONTO_FIJO')),
  valor numeric(12,2) NOT NULL CHECK(valor>=0),
  activa boolean NOT NULL DEFAULT true,
  vigencia_inicio timestamptz,
  vigencia_fin timestamptz,
  creada_en timestamptz NOT NULL DEFAULT now(),
  actualizada_en timestamptz NOT NULL DEFAULT now(),
  creada_por uuid REFERENCES seguridad.usuarios(id),
  CONSTRAINT ck_promociones_porcentaje_max CHECK(tipo<>'PORCENTAJE' OR valor<=100),
  CONSTRAINT ck_promociones_vigencia_coherente CHECK(
    vigencia_fin IS NULL OR vigencia_inicio IS NULL OR vigencia_inicio<=vigencia_fin
  )
);
CREATE INDEX IF NOT EXISTS idx_promociones_vigencia
  ON catalogo.promociones(activa,vigencia_inicio,vigencia_fin);

CREATE TABLE IF NOT EXISTS catalogo.promocion_variante (
  promocion_id uuid NOT NULL REFERENCES catalogo.promociones(id) ON DELETE CASCADE,
  variante_id uuid NOT NULL REFERENCES catalogo.variantes_producto(id) ON DELETE CASCADE,
  creada_en timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(promocion_id,variante_id)
);
CREATE INDEX IF NOT EXISTS idx_promocion_variante_variante
  ON catalogo.promocion_variante(variante_id);

CREATE TABLE IF NOT EXISTS inteligencia.historial_navegacion (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id uuid REFERENCES seguridad.clientes(usuario_id),
  usuario_id uuid REFERENCES seguridad.usuarios(id),
  variante_id uuid REFERENCES catalogo.variantes_producto(id),
  producto_id uuid REFERENCES catalogo.productos(id),
  evento varchar(40) NOT NULL,
  metadatos jsonb NOT NULL DEFAULT '{}'::jsonb,
  creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_navegacion_cliente_fecha
  ON inteligencia.historial_navegacion(cliente_id,creada_en DESC);
CREATE INDEX IF NOT EXISTS idx_navegacion_evento
  ON inteligencia.historial_navegacion(evento);

CREATE TABLE IF NOT EXISTS inteligencia.solicitudes_ia (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id uuid REFERENCES seguridad.usuarios(id),
  cliente_id uuid REFERENCES seguridad.clientes(usuario_id),
  tipo varchar(30) NOT NULL CHECK(tipo IN ('RECOMENDACION','BUSQUEDA_VOZ','REPORTE','DECISION_INVENTARIO')),
  entrada text NOT NULL DEFAULT '',
  funcion_usada varchar(60),
  parametros jsonb NOT NULL DEFAULT '{}'::jsonb,
  respuesta text NOT NULL DEFAULT '',
  datos jsonb NOT NULL DEFAULT '{}'::jsonb,
  proveedor varchar(20) NOT NULL DEFAULT 'DETERMINISTA',
  latencia_ms integer NOT NULL DEFAULT 0 CHECK(latencia_ms>=0),
  creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_solicitudes_tipo_fecha
  ON inteligencia.solicitudes_ia(tipo,creada_en DESC);
CREATE INDEX IF NOT EXISTS idx_solicitudes_usuario
  ON inteligencia.solicitudes_ia(usuario_id);

CREATE TABLE IF NOT EXISTS comercial.registros_idempotencia (
  clave uuid NOT NULL DEFAULT gen_random_uuid(),
  usuario_id uuid NOT NULL,
  recurso_tipo varchar(40) NOT NULL,
  operacion varchar(80) NOT NULL,
  hash_solicitud text NOT NULL,
  recurso_id uuid,
  respuesta jsonb NOT NULL DEFAULT '{}'::jsonb,
  creada_en timestamptz NOT NULL DEFAULT now(),
  expira_en timestamptz,
  CONSTRAINT registros_idempotencia_pkey PRIMARY KEY(clave,usuario_id,recurso_tipo,operacion)
);

-- Completa instalaciones que ya ejecutaron 0004 pero todavia no 0005.
ALTER TABLE comercial.registros_idempotencia ADD COLUMN IF NOT EXISTS usuario_id uuid;
ALTER TABLE comercial.registros_idempotencia ADD COLUMN IF NOT EXISTS operacion varchar(80);
UPDATE comercial.registros_idempotencia SET operacion=recurso_tipo WHERE operacion IS NULL;
UPDATE comercial.registros_idempotencia
SET usuario_id='00000000-0000-0000-0000-000000000000'::uuid WHERE usuario_id IS NULL;
ALTER TABLE comercial.registros_idempotencia ALTER COLUMN usuario_id SET NOT NULL;
ALTER TABLE comercial.registros_idempotencia ALTER COLUMN operacion SET NOT NULL;
DO $pk_idempotencia$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    WHERE c.conrelid='comercial.registros_idempotencia'::regclass
      AND c.conname='registros_idempotencia_pkey'
      AND pg_get_constraintdef(c.oid) LIKE '%clave, usuario_id, recurso_tipo, operacion%'
  ) THEN
    ALTER TABLE comercial.registros_idempotencia DROP CONSTRAINT IF EXISTS registros_idempotencia_pkey;
    ALTER TABLE comercial.registros_idempotencia ADD CONSTRAINT registros_idempotencia_pkey
      PRIMARY KEY(clave,usuario_id,recurso_tipo,operacion);
  END IF;
END
$pk_idempotencia$;
CREATE INDEX IF NOT EXISTS idx_idempotencia_expira
  ON comercial.registros_idempotencia(expira_en);
CREATE INDEX IF NOT EXISTS idx_idempotencia_usuario_expira
  ON comercial.registros_idempotencia(usuario_id,expira_en);

ALTER TABLE comercial.ventas ADD COLUMN IF NOT EXISTS expira_en timestamptz;
ALTER TABLE comercial.detalles_venta ADD COLUMN IF NOT EXISTS promocion_id uuid
  REFERENCES catalogo.promociones(id);
CREATE INDEX IF NOT EXISTS idx_ventas_estado_expira ON comercial.ventas(estado,expira_en);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pagos_referencia_externa
  ON comercial.pagos(referencia_externa) WHERE referencia_externa IS NOT NULL;

DELETE FROM public.alembic_version;
INSERT INTO public.alembic_version(version_num) VALUES('0005_ciclo3_correcciones');

COMMIT;

