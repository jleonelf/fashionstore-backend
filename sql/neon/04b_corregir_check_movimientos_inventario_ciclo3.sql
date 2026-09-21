/*
04b_corregir_check_movimientos_inventario_ciclo3.sql
Agrega 'COMPROMISO_DIGITAL' y 'LIBERACION_DIGITAL' al CHECK de movimientos_inventario.
*/
BEGIN;

ALTER TABLE inventario.movimientos_inventario 
  DROP CONSTRAINT IF EXISTS movimientos_inventario_tipo_check;

ALTER TABLE inventario.movimientos_inventario 
  ADD CONSTRAINT movimientos_inventario_tipo_check CHECK (
    tipo IN (
      'RECEPCION_PROVEEDOR',
      'RESERVA',
      'LIBERACION_RESERVA',
      'COMPROMISO_TRASLADO',
      'DESPACHO_TRASLADO',
      'RECEPCION_TRASLADO',
      'VENTA_PRESENCIAL',
      'VENTA_DIGITAL',
      'DEVOLUCION',
      'MERMA',
      'AJUSTE',
      'COMPROMISO_DIGITAL',
      'LIBERACION_DIGITAL'
    )
  );

COMMIT;
