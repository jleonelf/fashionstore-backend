import uuid
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.inventario import InventarioSucursal
from backend.app.models.organizacion import Sucursal, Ciudad

class InventarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def existenciaTotalPorVariante(self, variante_id: uuid.UUID) -> int:
        """Suma global disponible+reservado+comprometido+en_transito para variante."""
        query = select(
            func.coalesce(
                func.sum(
                    InventarioSucursal.disponible
                    + InventarioSucursal.reservado
                    + InventarioSucursal.comprometido_traslado
                    + InventarioSucursal.en_transito
                ),
                0,
            )
        ).where(InventarioSucursal.variante_id == variante_id)
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def buscarPorVarianteYSucursal(self, variante_id: uuid.UUID, sucursal_id: uuid.UUID) -> Optional[InventarioSucursal]:
        query = select(InventarioSucursal).where(
            InventarioSucursal.variante_id == variante_id,
            InventarioSucursal.sucursal_id == sucursal_id,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    # ---------- Primitivas transaccionales Ciclo 2 (Entrega 1) ----------
    # Protocolo obligatorio (plan-implementacion-ciclo-2-backend.md):
    #   1. Resolver y ORDENAR las claves (sucursal_id, variante_id).
    #   2. SELECT ... FOR UPDATE en ese orden (anti-deadlock).
    #   3. REVALIDAR cantidades y estado tras adquirir el bloqueo.
    #   4. Solo el servicio hace commit/rollback; aqui solo flush.

    @staticmethod
    def ordenarClavesBloqueo(
        claves: List[Tuple[uuid.UUID, uuid.UUID]],
    ) -> List[Tuple[uuid.UUID, uuid.UUID]]:
        """Orden determinista (sucursal_id, variante_id) para bloquear filas.

        Todas las mutaciones de inventario deben bloquear en este orden para
        reducir deadlocks cuando dos operaciones tocan las mismas filas.
        """
        return sorted(claves, key=lambda c: (str(c[0]), str(c[1])))

    async def bloquearFilas(
        self, claves: List[Tuple[uuid.UUID, uuid.UUID]]
    ) -> Dict[Tuple[uuid.UUID, uuid.UUID], Optional[InventarioSucursal]]:
        """Bloquea filas de inventario_sucursal con SELECT FOR UPDATE.

        Recibe claves (sucursal_id, variante_id); las ordena de forma
        determinista y devuelve el mapa clave -> fila (None si no existe).
        NO crea filas: una fila inexistente equivale a stock insuficiente y
        debe resolverse como 409 en el servicio (crearla aqui seria
        leer-modificar-guardar sin bloqueo ante inserciones fantasma).
        """
        ordenadas = self.ordenarClavesBloqueo(list(dict.fromkeys(claves)))
        if not ordenadas:
            return {}
        query = (
            select(InventarioSucursal)
            .where(
                tuple_(InventarioSucursal.sucursal_id, InventarioSucursal.variante_id).in_(ordenadas)
            )
            .order_by(InventarioSucursal.sucursal_id, InventarioSucursal.variante_id)
            .with_for_update()
        )
        result = await self.db.execute(query)
        filas = {(r.sucursal_id, r.variante_id): r for r in result.scalars().all()}
        return {clave: filas.get(clave) for clave in ordenadas}

    async def moverDisponibleAReservado(
        self, variante_id: uuid.UUID, sucursal_id: uuid.UUID, cantidad: int
    ) -> InventarioSucursal:
        """Mueve cantidad de disponible -> reservado con revalidacion.

        Debe llamarse DESPUES de bloquearFilas sobre la misma transaccion.
        Revalida stock (409 si insuficiente), actualiza y hace flush.
        """
        if cantidad <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cantidad a reservar debe ser mayor a cero",
            )
        filas = await self.bloquearFilas([(sucursal_id, variante_id)])
        registro = filas[(sucursal_id, variante_id)]
        if registro is None or registro.disponible < cantidad:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock insuficiente en sucursal destino",
            )
        registro.disponible -= cantidad
        registro.reservado += cantidad
        await self.db.flush()
        return registro

    async def liberarReservado(
        self, variante_id: uuid.UUID, sucursal_id: uuid.UUID, cantidad: int
    ) -> InventarioSucursal:
        """Mueve cantidad de reservado -> disponible con revalidacion.

        Uso: cancelacion/vencimiento/venta parcial (RN-03, RN-04).
        409 si lo reservado no alcanza (inconsistencia de dominio).
        """
        if cantidad <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cantidad a liberar debe ser mayor a cero",
            )
        filas = await self.bloquearFilas([(sucursal_id, variante_id)])
        registro = filas[(sucursal_id, variante_id)]
        if registro is None or registro.reservado < cantidad:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No hay suficiente stock reservado para liberar",
            )
        registro.reservado -= cantidad
        registro.disponible += cantidad
        await self.db.flush()
        return registro

    async def ingresar(self, variante_id: uuid.UUID, sucursal_id: uuid.UUID, cantidad: int) -> InventarioSucursal:
        """Upsert inventario: incrementa disponible. Crea registro si no existe."""
        registro = await self.buscarPorVarianteYSucursal(variante_id, sucursal_id)
        if registro is None:
            registro = InventarioSucursal(
                variante_id=variante_id,
                sucursal_id=sucursal_id,
                disponible=cantidad,
                reservado=0,
                comprometido_traslado=0,
                en_transito=0,
            )
            self.db.add(registro)
            await self.db.flush()
        else:
            registro.disponible = registro.disponible + cantidad
            await self.db.flush()
        return registro

    async def porVariante(self, variante_id: uuid.UUID) -> List[InventarioSucursal]:
        """
        CU06 - porVariante: SELECT inventario_sucursal WHERE variante_id AND disponible > 0
        Solo lectura, no modifica inventario. Filtra disponible>0.
        Performance: JOIN productos-variantes-inventario está en capas superiores; aquí directo.
        """
        query = select(InventarioSucursal).where(
            InventarioSucursal.variante_id == variante_id,
            InventarioSucursal.disponible > 0
        ).order_by(InventarioSucursal.sucursal_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def porVarianteEnriquecido(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        CU06 - porVariante con JOIN sucursales/ciudades WHERE disponible>0
        Retorna Sucursal + cantidades separadas (disponible, reservado, comprometido_traslado, en_transito)
        No total global, por sucursal. Diferenciando campos.
        """
        # Join inventario -> sucursal -> ciudad
        query = (
            select(InventarioSucursal, Sucursal, Ciudad)
            .join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .where(
                InventarioSucursal.variante_id == variante_id,
                InventarioSucursal.disponible > 0
            )
            .order_by(Sucursal.nombre)
        )
        result = await self.db.execute(query)
        rows = result.all()
        enriched = []
        for inv, suc, ciu in rows:
            enriched.append({
                "inventario_id": inv.id,
                "variante_id": inv.variante_id,
                "sucursal_id": suc.id,
                "sucursal_nombre": suc.nombre,
                "ciudad_id": ciu.id,
                "ciudad_nombre": ciu.nombre,
                "direccion": suc.direccion,
                "telefono": suc.telefono,
                "disponible": inv.disponible,
                "reservado": inv.reservado,
                "comprometido_traslado": inv.comprometido_traslado,
                "en_transito": inv.en_transito,
                "actualizado_en": inv.actualizado_en,
            })
        return enriched

    async def disponibilidadPorSucursal(self, variante_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Alias de porVarianteEnriquecido para contrato InventarioService.disponibilidadPorSucursal()
        """
        return await self.porVarianteEnriquecido(variante_id)

    async def existencias(self, sucursal_id: Optional[uuid.UUID] = None) -> List[InventarioSucursal]:
        """
        CU07 - existencias(sucursal_id): consulta existencias separadas disponible, reservado, comprometido_traslado, en_transito.
        Solo lectura, no modifica. Si sucursal_id None retorna todas.
        """
        query = select(InventarioSucursal)
        if sucursal_id:
            query = query.where(InventarioSucursal.sucursal_id == sucursal_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def existenciasEnriquecidas(self, sucursal_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        """
        Existencias enriquecidas con variante, producto, costo_promedio y cálculo valorizado.
        Para presentación consultarExistencias()
        """
        from backend.app.models.catalogo import VarianteProducto, Producto
        query = (
            select(InventarioSucursal, VarianteProducto, Producto, Sucursal, Ciudad)
            .join(VarianteProducto, VarianteProducto.id == InventarioSucursal.variante_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
        )
        if sucursal_id:
            query = query.where(InventarioSucursal.sucursal_id == sucursal_id)
        query = query.order_by(Sucursal.nombre, Producto.nombre)
        result = await self.db.execute(query)
        rows = result.all()
        lista: List[Dict[str, Any]] = []
        for inv, var, prod, suc, ciu in rows:
            existencia_total = inv.disponible + inv.reservado + inv.comprometido_traslado + inv.en_transito
            costo_prom = float(var.costo_promedio or 0)
            valorizado = existencia_total * costo_prom
            margen_unit = float(var.precio or 0) - costo_prom
            lista.append({
                "inventario_id": inv.id,
                "variante_id": var.id,
                "sku": var.sku,
                "producto_id": prod.id,
                "producto_nombre": prod.nombre,
                "sucursal_id": suc.id,
                "sucursal_nombre": suc.nombre,
                "ciudad_nombre": ciu.nombre,
                "disponible": inv.disponible,
                "reservado": inv.reservado,
                "comprometido_traslado": inv.comprometido_traslado,
                "en_transito": inv.en_transito,
                "existencia_total": existencia_total,
                "costo_promedio": costo_prom,
                "costo_ultimo": float(var.costo_ultimo or 0),
                "precio": float(var.precio or 0),
                "valorizacion": round(valorizado, 2),
                "margen_bruto_unitario": round(margen_unit, 2),
                "margen_bruto_total": round(margen_unit * existencia_total, 2),
                "actualizado_en": inv.actualizado_en,
            })
        return lista

    async def valorizacionPorSucursal(self, sucursal_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        """
        CU07 - valorizacionPorSucursal() = SELECT inventario_sucursal JOIN variantes_producto (costo_promedio)
        con cálculo existencia_total * costo_promedio, agrupado por sucursal.
        Para RF24/RF26: Σ existencia×costo_promedio por sucursal y global.
        Incluye margen bruto precio - costo_promedio.
        """
        from backend.app.models.catalogo import VarianteProducto
        # Cálculo por sucursal
        existencia_total_expr = (
            InventarioSucursal.disponible
            + InventarioSucursal.reservado
            + InventarioSucursal.comprometido_traslado
            + InventarioSucursal.en_transito
        )
        valorizacion_expr = existencia_total_expr * VarianteProducto.costo_promedio
        margen_expr = (VarianteProducto.precio - VarianteProducto.costo_promedio) * existencia_total_expr

        query = (
            select(
                InventarioSucursal.sucursal_id,
                Sucursal.nombre.label("sucursal_nombre"),
                Ciudad.nombre.label("ciudad_nombre"),
                func.sum(existencia_total_expr).label("total_unidades"),
                func.sum(InventarioSucursal.disponible).label("total_disponible"),
                func.sum(InventarioSucursal.reservado).label("total_reservado"),
                func.sum(InventarioSucursal.comprometido_traslado).label("total_comprometido"),
                func.sum(InventarioSucursal.en_transito).label("total_en_transito"),
                func.sum(valorizacion_expr).label("valorizacion"),
                func.sum(margen_expr).label("margen_bruto_total"),
            )
            .join(VarianteProducto, VarianteProducto.id == InventarioSucursal.variante_id)
            .join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .group_by(InventarioSucursal.sucursal_id, Sucursal.nombre, Ciudad.nombre)
            .order_by(Sucursal.nombre)
        )
        if sucursal_id:
            query = query.where(InventarioSucursal.sucursal_id == sucursal_id)

        result = await self.db.execute(query)
        rows = result.all()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append({
                "sucursal_id": r.sucursal_id,
                "sucursal_nombre": r.sucursal_nombre,
                "ciudad_nombre": r.ciudad_nombre,
                "total_unidades": int(r.total_unidades or 0),
                "total_disponible": int(r.total_disponible or 0),
                "total_reservado": int(r.total_reservado or 0),
                "total_comprometido": int(r.total_comprometido or 0),
                "total_en_transito": int(r.total_en_transito or 0),
                "valorizacion": float(round(r.valorizacion or 0, 2)),
                "margen_bruto_total": float(round(r.margen_bruto_total or 0, 2)),
            })
        return out

    async def valorizacionGlobal(self) -> Dict[str, Any]:
        """Valorización global (suma de todas las sucursales) para reporte RF26"""
        por_sucursal = await self.valorizacionPorSucursal()
        total_unidades = sum(s["total_unidades"] for s in por_sucursal)
        total_val = sum(s["valorizacion"] for s in por_sucursal)
        total_margen = sum(s["margen_bruto_total"] for s in por_sucursal)
        return {
            "por_sucursal": por_sucursal,
            "global": {
                "total_unidades": total_unidades,
                "valorizacion": round(total_val, 2),
                "margen_bruto_total": round(total_margen, 2),
                "sucursales": len(por_sucursal),
            }
        }
