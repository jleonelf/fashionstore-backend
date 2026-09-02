import asyncio
import uuid
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.seguridad import Rol, Usuario, Empleado
from backend.app.models.organizacion import Ciudad, Sucursal
from backend.app.models.catalogo import Talla, Color, Categoria, Temporada
from backend.app.core.seguridad import generar_contrasenia_hash

async def sembrar_datos_ciclo_1():
    print("[*] Sembrando datos base para el Ciclo 1...")
    async with AsyncSessionLocal() as db:
        # 1. Sembrar Roles
        roles_base = [
            ("ADMINISTRADOR", "Acceso total a la configuracion y gestion"),
            ("ENCARGADO", "Gestion de reservas, almacen y stock local"),
            ("CAJERO", "Cobro y facturacion de ventas presenciales"),
            ("PROVEEDOR", "Gestion de suministros y convenios"),
            ("CLIENTE", "Exploracion de catalogo, reservas y compras"),
        ]

        roles_map = {}
        for nombre, desc in roles_base:
            res = await db.execute(select(Rol).where(Rol.nombre == nombre))
            rol_existente = res.scalars().first()
            if not rol_existente:
                rol_existente = Rol(nombre=nombre, descripcion=desc, activo=True)
                db.add(rol_existente)
                await db.flush()
                print(f"  + Rol creado: {nombre}")
            roles_map[nombre] = rol_existente

        # 2. Sembrar Usuario Administrador por defecto
        correo_admin = "admin@fashionstore.com"
        res_admin = await db.execute(select(Usuario).where(Usuario.correo_electronico == correo_admin))
        if not res_admin.scalars().first():
            usuario_admin = Usuario(
                rol_id=roles_map["ADMINISTRADOR"].id,
                nombres="Administrador",
                apellidos="Sistema",
                correo_electronico=correo_admin,
                contrasenia_hash=generar_contrasenia_hash("admin123456"),
                telefono="+591 70000001",
                estado="ACTIVO"
            )
            db.add(usuario_admin)
            await db.flush()
            print(f"  + Usuario Admin creado: {correo_admin} (clave: admin123456)")

        # 3. Sembrar Ciudad y Sucursal Base (Santa Cruz de la Sierra)
        res_ciudad = await db.execute(select(Ciudad).where(Ciudad.nombre == "Santa Cruz de la Sierra"))
        ciudad_scz = res_ciudad.scalars().first()
        if not ciudad_scz:
            ciudad_scz = Ciudad(nombre="Santa Cruz de la Sierra", activo=True)
            db.add(ciudad_scz)
            await db.flush()
            print("  + Ciudad creada: Santa Cruz de la Sierra")

        res_sucursal = await db.execute(select(Sucursal).where(Sucursal.nombre == "Sucursal Central Equipetrol"))
        if not res_sucursal.scalars().first():
            sucursal = Sucursal(
                ciudad_id=ciudad_scz.id,
                nombre="Sucursal Central Equipetrol",
                direccion="Av. San Martin esq. Calle 5 Este",
                telefono="+591 3 3445566",
                numero_anillo=3,
                tarifa_base_delivery=15.00,
                incremento_anillo_delivery=3.50,
                anillo_minimo_delivery=1,
                anillo_maximo_delivery=8,
                delivery_activo=True,
                activa=True
            )
            db.add(sucursal)
            print("  + Sucursal creada: Sucursal Central Equipetrol")

        # 4. Sembrar Tallas
        tallas_base = [("XS", 1), ("S", 2), ("M", 3), ("L", 4), ("XL", 5), ("XXL", 6)]
        for nombre_talla, orden in tallas_base:
            res_talla = await db.execute(select(Talla).where(Talla.nombre == nombre_talla))
            if not res_talla.scalars().first():
                db.add(Talla(nombre=nombre_talla, orden=orden, activo=True))
        print("  + Tallas maestras registradas.")

        # 5. Sembrar Colores
        colores_base = [
            ("Negro", "#000000"),
            ("Blanco", "#FFFFFF"),
            ("Azul Marino", "#001F3F"),
            ("Rojo Borgona", "#800020"),
            ("Verde Oliva", "#556B2F"),
            ("Beige", "#F5F5DC")
        ]
        for nombre_color, hex_val in colores_base:
            res_color = await db.execute(select(Color).where(Color.nombre == nombre_color))
            if not res_color.scalars().first():
                db.add(Color(nombre=nombre_color, codigo_hex=hex_val, activo=True))
        print("  + Colores maestros registrados.")

        # 6. Sembrar Categorias
        categorias_base = ["Poleras y Camisas", "Pantalones y Jeans", "Vestidos y Faldas", "Abrigos y Chaquetas", "Calzados"]
        for cat in categorias_base:
            res_cat = await db.execute(select(Categoria).where(Categoria.nombre == cat))
            if not res_cat.scalars().first():
                db.add(Categoria(nombre=cat, activo=True))
        print("  + Categorias base registradas.")

        # 7. Sembrar Temporada
        res_temp = await db.execute(select(Temporada).where(Temporada.nombre == "Primavera - Verano 2026"))
        if not res_temp.scalars().first():
            db.add(Temporada(nombre="Primavera - Verano 2026", activa=True))
            print("  + Temporada registrada: Primavera - Verano 2026")

        await db.commit()
        print("[EXITO] Siembra de datos base completada con exito!")

if __name__ == "__main__":
    asyncio.run(sembrar_datos_ciclo_1())
