/*
FashionStore - Reset y semilla oficial hasta Ciclo 2.

ADVERTENCIA: este archivo ELIMINA TODOS LOS DATOS de las tablas de negocio
de Ciclos 1 y 2. Crear antes un branch/backup de Neon y ejecutar solamente
despues de que 01_esquema_hasta_ciclo2.sql termine correctamente.

No elimina tablas, esquemas, migraciones ni configuraciones de Neon.
*/
BEGIN;

DO $precondiciones$
DECLARE
  objeto text;
BEGIN
  FOREACH objeto IN ARRAY ARRAY[
    'seguridad.roles','seguridad.usuarios','seguridad.clientes','seguridad.empleados',
    'organizacion.ciudades','organizacion.sucursales','catalogo.productos',
    'catalogo.variantes_producto','inventario.inventario_sucursal',
    'inventario.movimientos_inventario','comercial.reservas','inventario.traslados',
    'comercial.ventas','comercial.pagos'
  ] LOOP
    IF to_regclass(objeto) IS NULL THEN
      RAISE EXCEPTION 'Falta %. Ejecute primero 01_esquema_hasta_ciclo2.sql', objeto;
    END IF;
  END LOOP;
END
$precondiciones$;

TRUNCATE TABLE
  comercial.pagos, comercial.detalles_venta, comercial.ventas,
  inventario.detalles_traslado, inventario.traslados,
  comercial.detalles_reserva, comercial.reservas,
  inventario.movimientos_inventario, inventario.inventario_sucursal,
  inventario.detalles_lote_recepcion, inventario.lotes_recepcion,
  catalogo.producto_coleccion, catalogo.producto_temporada,
  catalogo.imagenes_producto, catalogo.variantes_producto,
  catalogo.productos, catalogo.proveedores, catalogo.colecciones,
  catalogo.temporadas, catalogo.colores, catalogo.tallas,
  catalogo.categorias, seguridad.empleados, seguridad.clientes,
  seguridad.usuarios, organizacion.sucursales,
  organizacion.ciudades, seguridad.roles
RESTART IDENTITY CASCADE;

CREATE OR REPLACE FUNCTION pg_temp.fs_seed_uuid(valor text)
RETURNS uuid LANGUAGE sql IMMUTABLE STRICT AS $funcion$
  SELECT (
    substr(md5(valor),1,8)||'-'||substr(md5(valor),9,4)||'-'||
    substr(md5(valor),13,4)||'-'||substr(md5(valor),17,4)||'-'||
    substr(md5(valor),21,12)
  )::uuid
$funcion$;

INSERT INTO seguridad.roles(id,nombre,descripcion,activo,creado_en) VALUES
('1b25ede3-a41f-57f2-9c14-c762be8b1e70','ADMINISTRADOR','Administración integral',true,now()),
('5863c7b8-196e-5bf7-876b-bae72a22147b','ENCARGADO','Operaciones de sucursal',true,now()),
('85a66b1c-b44a-5b64-b06a-1916c452601b','CAJERO','Cobros y devoluciones',true,now()),
('54cb5f15-7870-5af5-8b21-8d7207997bbf','PROVEEDOR','Abastecimiento',true,now()),
('6af9ddb6-dccb-59d4-b6b8-27cbe7446097','CLIENTE','Catálogo, reservas y compras',true,now());

INSERT INTO organizacion.ciudades(id,nombre,activo) VALUES
('552af636-1176-5781-8fcb-3443ea2bb6d3','Santa Cruz de la Sierra',true);

INSERT INTO organizacion.sucursales(
 id,ciudad_id,nombre,direccion,telefono,numero_anillo,
 tarifa_base_delivery,incremento_anillo_delivery,anillo_minimo_delivery,
 anillo_maximo_delivery,delivery_activo,activa,adelanto_activo,
 modalidad_adelanto,valor_adelanto) VALUES
('69bdeb4b-9751-5f54-8ab1-d462d9fd9264','552af636-1176-5781-8fcb-3443ea2bb6d3','Sucursal Equipetrol','Av. San Martín, Equipetrol','+591 3 3400000',3,12,3,1,8,true,true,true,'PORCENTAJE',30),
('83cf6c68-a4b8-5432-b68b-25031d076eea','552af636-1176-5781-8fcb-3443ea2bb6d3','Sucursal Centro','Calle Libertad, centro histórico','+591 3 3400000',1,12,3,1,8,true,true,true,'PORCENTAJE',30),
('0235954d-078a-5786-b91d-22cc45717d2a','552af636-1176-5781-8fcb-3443ea2bb6d3','Sucursal Norte','Av. Cristo Redentor, 5.º anillo','+591 3 3400000',5,12,3,1,8,true,true,true,'PORCENTAJE',30);

-- Hash bcrypt válido de la contraseña temporal Fashion123!.
INSERT INTO seguridad.usuarios(
 id,rol_id,nombres,apellidos,correo_electronico,contrasenia_hash,telefono,estado,
 creado_en,actualizado_en) VALUES
('5ee989f2-c1ae-5053-bded-6e7c0a086a4e','1b25ede3-a41f-57f2-9c14-c762be8b1e70','Administrador','FashionStore','admin@fashionstore.com','$2b$12$ezZmtFiUUwne.Xe6F1PlT.ldI/J0u2HazqGmijFH26wLq5lnckyBy','+591 70000000','ACTIVO',now(),now()),
('7b75c569-0a10-52f9-96ca-78ee230f3749','5863c7b8-196e-5bf7-876b-bae72a22147b','Elena','Vargas','encargado@fashionstore.com','$2b$12$ezZmtFiUUwne.Xe6F1PlT.ldI/J0u2HazqGmijFH26wLq5lnckyBy','+591 70000000','ACTIVO',now(),now()),
('fdfd3b21-2038-5e73-8d72-c3c6cc88b80d','85a66b1c-b44a-5b64-b06a-1916c452601b','Carlos','Rojas','cajero@fashionstore.com','$2b$12$ezZmtFiUUwne.Xe6F1PlT.ldI/J0u2HazqGmijFH26wLq5lnckyBy','+591 70000000','ACTIVO',now(),now()),
('8d8df0e3-5756-5a88-af49-fa7a123cdcd5','6af9ddb6-dccb-59d4-b6b8-27cbe7446097','Andrea','Flores','cliente@fashionstore.com','$2b$12$ezZmtFiUUwne.Xe6F1PlT.ldI/J0u2HazqGmijFH26wLq5lnckyBy','+591 70000000','ACTIVO',now(),now());

INSERT INTO seguridad.empleados(usuario_id,sucursal_id,cargo,activo) VALUES
('5ee989f2-c1ae-5053-bded-6e7c0a086a4e',NULL,'Administrador',true),
('7b75c569-0a10-52f9-96ca-78ee230f3749','69bdeb4b-9751-5f54-8ab1-d462d9fd9264','Encargado',true),
('fdfd3b21-2038-5e73-8d72-c3c6cc88b80d','69bdeb4b-9751-5f54-8ab1-d462d9fd9264','Cajero',true);
INSERT INTO seguridad.clientes(usuario_id,direccion_referencia,fecha_nacimiento,preferencias) VALUES
('8d8df0e3-5756-5a88-af49-fa7a123cdcd5','3.er anillo, Equipetrol','1998-05-18','{"generos":["MUJER"],"tallas":["M"]}'::jsonb);

INSERT INTO catalogo.tallas(id,nombre,orden,activo) VALUES
('f47d8692-30d6-5652-9303-6240119887e7','XS',1,true),
('20fb2c37-31d1-54bb-9fc4-d1e03a0843a0','S',2,true),
('02ea034f-dda3-503e-a111-65fef974e626','M',3,true),
('6576219c-04e0-52e9-8430-8170750ce53d','L',4,true),
('f73527e4-7472-5909-9b09-cf6003291814','XL',5,true);
INSERT INTO catalogo.colores(id,nombre,codigo_hex,activo) VALUES
('30b1978f-8397-550a-b3a7-02be1de6818e','Negro','#171717',true),
('7214b34a-2572-5254-a3bc-ae1db4549916','Blanco','#F8F7F2',true),
('7caf9bc0-0702-5420-b67e-a8a1a2167e23','Azul marino','#14213D',true),
('cb3f1ddb-f42f-5814-8603-8e88620abdb0','Borgoña','#722F37',true),
('deec3682-5f6d-5b77-b132-3000749dddf9','Beige','#D8C3A5',true),
('83dd2402-3b3f-596f-a39e-eaee0315414e','Verde oliva','#66724B',true);
INSERT INTO catalogo.categorias(id,nombre,descripcion,activo) VALUES
('1cfd721d-5123-5671-ab35-8816c21c869a','Camisas y blusas','Colección de camisas y blusas',true),
('f3a901af-3937-576d-87f6-51999f8d56ef','Pantalones','Colección de pantalones',true),
('a0612dff-c657-5041-bbfa-3c3c3c438251','Vestidos','Colección de vestidos',true),
('82ef31ff-6067-57ee-aaef-bbe4140cc99c','Chaquetas','Colección de chaquetas',true);
INSERT INTO catalogo.temporadas(id,nombre,fecha_inicio,fecha_fin,activa) VALUES
('6059b205-59da-5c9f-a2bd-94466512a073','Primavera-Verano 2026','2026-09-01','2027-03-31',true);
INSERT INTO catalogo.colecciones(id,nombre,descripcion,activa) VALUES
('c0fa8f14-4231-5617-a1d2-a00ef7e4e38a','Esenciales urbanos','Prendas versátiles para uso diario',true);
INSERT INTO catalogo.proveedores(id,razon_social,nit,contacto,telefono,correo_electronico,direccion,convenio,activo) VALUES
('364dfe21-a11c-587c-9145-0b09a432cdf8','Textiles Andina SRL','1020304050','María Suárez','+591 70001111','ventas@textilesandina.test','Parque Industrial, Santa Cruz','Proveedor demostrativo oficial',true);

CREATE TEMP TABLE fs_productos_seed(
 orden int, producto_id uuid, imagen_id uuid, clave text, nombre text,
 categoria_id uuid, genero text, precio numeric(12,2), imagen text
) ON COMMIT DROP;
INSERT INTO fs_productos_seed VALUES
(1,'1c29ba36-6445-5377-8fdd-daac0aae1ae0','1304ea96-646e-5932-bf51-c40e0c246b76','camisa-lino','Camisa de lino clásica','1cfd721d-5123-5671-ab35-8816c21c869a','UNISEX',289,'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=900&auto=format&fit=crop&q=80'),
(2,'5af4d20c-559f-500c-99f7-6e4931bca657','cc011142-756b-51e7-ab50-0fbc9c8423d5','blusa-satin','Blusa satinada Aura','1cfd721d-5123-5671-ab35-8816c21c869a','MUJER',249,'https://images.unsplash.com/photo-1564257577054-11e0c9e9393f?w=900&auto=format&fit=crop&q=80'),
(3,'69e004a5-3df4-5bb7-a9e9-a98dc0168be2','3a25b1cd-28b8-5b37-b209-53dab697df5d','jean-recto','Jean recto índigo','f3a901af-3937-576d-87f6-51999f8d56ef','UNISEX',329,'https://images.unsplash.com/photo-1542272604-787c3835535d?w=900&auto=format&fit=crop&q=80'),
(4,'47afabd4-78f7-54e0-8abc-e712a516d8dd','95057d41-4192-5647-92b6-d502919cb4e1','pantalon-sastre','Pantalón sastre Nómada','f3a901af-3937-576d-87f6-51999f8d56ef','MUJER',359,'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=900&auto=format&fit=crop&q=80'),
(5,'d039feb0-e0ba-535e-a96f-faa9eb82d122','a19ebe3a-aa74-5b12-bf90-576d7a565c21','vestido-midi','Vestido midi Brisa','a0612dff-c657-5041-bbfa-3c3c3c438251','MUJER',449,'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=900&auto=format&fit=crop&q=80'),
(6,'0a83b5df-b164-5a83-871c-d94f0163bd2a','5639363b-deca-53e0-8d1a-b26ff88b47ae','vestido-negro','Vestido negro esencial','a0612dff-c657-5041-bbfa-3c3c3c438251','MUJER',399,'https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=900&auto=format&fit=crop&q=80'),
(7,'5aa88705-3274-52db-84cb-106772eb0aea','2a592e5f-f1a1-58b0-8a30-2e8b815df74d','chaqueta-denim','Chaqueta denim urbana','82ef31ff-6067-57ee-aaef-bbe4140cc99c','UNISEX',499,'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=900&auto=format&fit=crop&q=80'),
(8,'9dd7be48-02f7-5811-b1be-76fbb89e2440','903cd605-b302-54c6-a96f-b18898ff27a2','blazer-negro','Blazer estructura moderna','82ef31ff-6067-57ee-aaef-bbe4140cc99c','MUJER',549,'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=900&auto=format&fit=crop&q=80');

INSERT INTO catalogo.productos(id,categoria_id,proveedor_principal_id,nombre,descripcion,genero,marca,precio_base,activo,creado_en,actualizado_en)
SELECT producto_id,categoria_id,'364dfe21-a11c-587c-9145-0b09a432cdf8',nombre,
       nombre||'. Prenda de demostración con disponibilidad por sucursal.',genero,'FashionStore',precio,true,now(),now()
FROM fs_productos_seed;
INSERT INTO catalogo.imagenes_producto(id,producto_id,enlace_imagen,texto_alternativo,orden,es_principal)
SELECT imagen_id,producto_id,imagen,nombre,1,true FROM fs_productos_seed;
INSERT INTO catalogo.producto_temporada
SELECT producto_id,'6059b205-59da-5c9f-a2bd-94466512a073' FROM fs_productos_seed;
INSERT INTO catalogo.producto_coleccion
SELECT producto_id,'c0fa8f14-4231-5617-a1d2-a00ef7e4e38a' FROM fs_productos_seed;

CREATE TEMP TABLE fs_variantes_seed(
 vi int,id uuid,producto_id uuid,talla_id uuid,color_id uuid,sku text,
 codigo text,precio numeric(12,2),costo numeric(12,2)
) ON COMMIT DROP;
INSERT INTO fs_variantes_seed VALUES
(0,'b73cb46e-9ce7-5a5f-9a05-daf1ecb79bf6','1c29ba36-6445-5377-8fdd-daac0aae1ae0','02ea034f-dda3-503e-a111-65fef974e626','7214b34a-2572-5254-a3bc-ae1db4549916','FS-001-1','7800000011',289,138.72),
(1,'9a511b2a-70c6-5591-b448-ceab77a3d7a2','1c29ba36-6445-5377-8fdd-daac0aae1ae0','6576219c-04e0-52e9-8430-8170750ce53d','30b1978f-8397-550a-b3a7-02be1de6818e','FS-001-2','7800000012',289,138.72),
(2,'3f83242f-2442-5496-8483-297cd83b5a71','5af4d20c-559f-500c-99f7-6e4931bca657','02ea034f-dda3-503e-a111-65fef974e626','cb3f1ddb-f42f-5814-8603-8e88620abdb0','FS-002-1','7800000021',249,119.52),
(3,'de3c8273-d3a5-51e9-bd5e-4b7d9aaa06fc','5af4d20c-559f-500c-99f7-6e4931bca657','6576219c-04e0-52e9-8430-8170750ce53d','30b1978f-8397-550a-b3a7-02be1de6818e','FS-002-2','7800000022',249,119.52),
(4,'d80fcf57-2a83-5bad-b2ae-f81702a99464','69e004a5-3df4-5bb7-a9e9-a98dc0168be2','02ea034f-dda3-503e-a111-65fef974e626','7caf9bc0-0702-5420-b67e-a8a1a2167e23','FS-003-1','7800000031',329,157.92),
(5,'7b00de24-5198-536e-94dd-3317df08b2d5','69e004a5-3df4-5bb7-a9e9-a98dc0168be2','6576219c-04e0-52e9-8430-8170750ce53d','30b1978f-8397-550a-b3a7-02be1de6818e','FS-003-2','7800000032',329,157.92),
(6,'c51b7556-5679-5ccc-beb9-2f81d79a9605','47afabd4-78f7-54e0-8abc-e712a516d8dd','20fb2c37-31d1-54bb-9fc4-d1e03a0843a0','deec3682-5f6d-5b77-b132-3000749dddf9','FS-004-1','7800000041',359,172.32),
(7,'053b1dfb-566e-5b00-a287-5689981ec44a','47afabd4-78f7-54e0-8abc-e712a516d8dd','6576219c-04e0-52e9-8430-8170750ce53d','30b1978f-8397-550a-b3a7-02be1de6818e','FS-004-2','7800000042',359,172.32),
(8,'00573cd6-637c-5f4f-8f45-9f045fd612bf','d039feb0-e0ba-535e-a96f-faa9eb82d122','02ea034f-dda3-503e-a111-65fef974e626','83dd2402-3b3f-596f-a39e-eaee0315414e','FS-005-1','7800000051',449,215.52),
(9,'dd60be23-9874-5ff2-a5ad-7c5318886cab','d039feb0-e0ba-535e-a96f-faa9eb82d122','6576219c-04e0-52e9-8430-8170750ce53d','30b1978f-8397-550a-b3a7-02be1de6818e','FS-005-2','7800000052',449,215.52),
(10,'158495c2-44ab-589d-8edf-0eac646a893a','0a83b5df-b164-5a83-871c-d94f0163bd2a','20fb2c37-31d1-54bb-9fc4-d1e03a0843a0','30b1978f-8397-550a-b3a7-02be1de6818e','FS-006-1','7800000061',399,191.52),
(11,'62a4362c-6e17-5a37-9cab-b0403997616d','0a83b5df-b164-5a83-871c-d94f0163bd2a','6576219c-04e0-52e9-8430-8170750ce53d','deec3682-5f6d-5b77-b132-3000749dddf9','FS-006-2','7800000062',399,191.52),
(12,'743cb9fe-6fe5-5e55-9cbc-b2d13044f978','5aa88705-3274-52db-84cb-106772eb0aea','6576219c-04e0-52e9-8430-8170750ce53d','7caf9bc0-0702-5420-b67e-a8a1a2167e23','FS-007-1','7800000071',499,239.52),
(13,'8c104a87-2235-582d-8c87-998fe22d49a3','5aa88705-3274-52db-84cb-106772eb0aea','02ea034f-dda3-503e-a111-65fef974e626','30b1978f-8397-550a-b3a7-02be1de6818e','FS-007-2','7800000072',499,239.52),
(14,'ce7bef4f-6c7f-58b2-8af9-579cd318fcc7','9dd7be48-02f7-5811-b1be-76fbb89e2440','02ea034f-dda3-503e-a111-65fef974e626','30b1978f-8397-550a-b3a7-02be1de6818e','FS-008-1','7800000081',549,263.52),
(15,'e0707dcb-d3ed-53dc-90e0-01051a16f2cb','9dd7be48-02f7-5811-b1be-76fbb89e2440','6576219c-04e0-52e9-8430-8170750ce53d','deec3682-5f6d-5b77-b132-3000749dddf9','FS-008-2','7800000082',549,263.52);
INSERT INTO catalogo.variantes_producto(
 id,producto_id,talla_id,color_id,sku,codigo_barras,precio,peso_gramos,costo_promedio,costo_ultimo,recurso_prueba_virtual,activa)
SELECT id,producto_id,talla_id,color_id,sku,codigo,precio,420,costo,costo,NULL,true
FROM fs_variantes_seed;

CREATE TEMP TABLE fs_sucursales_seed(si int,id uuid,lote_id uuid,documento text) ON COMMIT DROP;
INSERT INTO fs_sucursales_seed VALUES
(0,'69bdeb4b-9751-5f54-8ab1-d462d9fd9264','930d94bc-a165-5a72-ae89-a90b24aed15a','SEMILLA-2026-01'),
(1,'83cf6c68-a4b8-5432-b68b-25031d076eea','3a47c48f-cd41-5ac5-a649-0b89cbf282d7','SEMILLA-2026-02'),
(2,'0235954d-078a-5786-b91d-22cc45717d2a','c8eda6da-428f-519c-82ba-dc0623e7df57','SEMILLA-2026-03');
INSERT INTO inventario.lotes_recepcion(
 id,proveedor_id,sucursal_id,temporada_id,coleccion_id,recibido_por_id,numero_documento,fecha_recepcion,observacion)
SELECT lote_id,'364dfe21-a11c-587c-9145-0b09a432cdf8',id,
       '6059b205-59da-5c9f-a2bd-94466512a073','c0fa8f14-4231-5617-a1d2-a00ef7e4e38a',
       '5ee989f2-c1ae-5053-bded-6e7c0a086a4e',documento,now(),'Carga inicial oficial'
FROM fs_sucursales_seed;

CREATE TEMP TABLE fs_stock_seed ON COMMIT DROP AS
SELECT s.si,s.id AS sucursal_id,s.lote_id,v.vi,v.id AS variante_id,v.costo,
       5+mod(v.vi+s.si,5) AS cantidad,
       pg_temp.fs_seed_uuid('detalle:'||s.si||':'||v.vi) AS detalle_id,
       pg_temp.fs_seed_uuid('stock:'||s.si||':'||v.vi) AS stock_id,
       pg_temp.fs_seed_uuid('mov:'||s.si||':'||v.vi) AS movimiento_id,
       pg_temp.fs_seed_uuid('idem:'||s.si||':'||v.vi) AS idem_id
FROM fs_sucursales_seed s CROSS JOIN fs_variantes_seed v;

INSERT INTO inventario.detalles_lote_recepcion(id,lote_id,variante_id,cantidad,costo_unitario)
SELECT detalle_id,lote_id,variante_id,cantidad,costo FROM fs_stock_seed;
INSERT INTO inventario.inventario_sucursal(
 id,variante_id,sucursal_id,disponible,reservado,comprometido_traslado,en_transito,actualizado_en)
SELECT stock_id,variante_id,sucursal_id,cantidad,0,0,0,now() FROM fs_stock_seed;
INSERT INTO inventario.movimientos_inventario(
 id,variante_id,sucursal_destino_id,responsable_id,tipo,cantidad,costo_unitario,
 referencia_tipo,referencia_id,linea_referencia_id,clave_idempotencia,fecha_hora,observacion)
SELECT movimiento_id,variante_id,sucursal_id,'5ee989f2-c1ae-5053-bded-6e7c0a086a4e',
       'RECEPCION_PROVEEDOR',cantidad,costo,'LOTE_RECEPCION',lote_id,detalle_id,idem_id,
       now(),'Stock inicial oficial'
FROM fs_stock_seed;

DO $validacion$
DECLARE errores text[] := ARRAY[]::text[];
BEGIN
  IF (SELECT count(*) FROM seguridad.roles) <> 5 THEN errores:=array_append(errores,'roles<>5'); END IF;
  IF (SELECT count(*) FROM seguridad.usuarios) <> 4 THEN errores:=array_append(errores,'usuarios<>4'); END IF;
  IF (SELECT count(*) FROM organizacion.sucursales) <> 3 THEN errores:=array_append(errores,'sucursales<>3'); END IF;
  IF (SELECT count(*) FROM catalogo.productos) <> 8 THEN errores:=array_append(errores,'productos<>8'); END IF;
  IF (SELECT count(*) FROM catalogo.variantes_producto) <> 16 THEN errores:=array_append(errores,'variantes<>16'); END IF;
  IF (SELECT count(*) FROM inventario.inventario_sucursal) <> 48 THEN errores:=array_append(errores,'inventario<>48'); END IF;
  IF (SELECT count(*) FROM inventario.movimientos_inventario) <> 48 THEN errores:=array_append(errores,'movimientos<>48'); END IF;
  IF cardinality(errores)>0 THEN
    RAISE EXCEPTION 'Semilla inválida: %', array_to_string(errores,', ');
  END IF;
END
$validacion$;

COMMIT;
