# Actualizacion de Neon hasta Ciclo 2

Ejecutar los archivos en orden desde Neon SQL Editor:

1. `00_diagnostico_neon.sql` — solo lectura.
2. `01_esquema_hasta_ciclo2.sql` — crea o completa el esquema.
3. Volver a ejecutar `00_diagnostico_neon.sql`.
4. `02_reset_semilla_oficial_ciclo2.sql` — destructivo para datos de negocio.
5. `03_verificacion_ciclo2.sql` — solo lectura; debe terminar sin excepciones.

## Advertencias

- Confirmar visualmente el proyecto, branch y base de Neon antes del paso 4.
- Crear un branch/backup de Neon antes del reset.
- No ejecutar `pytest` contra Neon; las pruebas usan `fashionstore_test`.
- Los scripts no contienen URLs, claves de Neon, Stripe ni Gemini.
- `02_reset_semilla_oficial_ciclo2.sql` reemplaza los datos de negocio y deja
  vacías las operaciones de Ciclo 2. La contraseña temporal de las cuatro
  cuentas oficiales es `Fashion123!`.
- No continuar con Ciclo 3 hasta que `03_verificacion_ciclo2.sql` indique
  `SEMILLA_CICLO2_OK`.

