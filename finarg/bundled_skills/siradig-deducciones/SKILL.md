---
name: siradig-deducciones
description: Cargar deducciones de ganancias en SIRADIG (ARCA/AFIP) via browser automation
version: 1.0.0
prerequisites:
  env_vars: [AFIP_CUIT]
---

# SIRADIG — Carga de Deducciones de Ganancias

Automatiza la carga del formulario F572 (deducciones de Impuesto a las Ganancias) en el sistema SIRADIG de ARCA (ex AFIP).

No existe API para SIRADIG — se usa browser automation.

## Requisitos

- `AFIP_CUIT`: CUIT del contribuyente (sin guiones)
- `AFIP_CLAVE_FISCAL` (opcional): clave fiscal para login automático
- Si no tiene clave fiscal configurada, el usuario logea manualmente

Configurar: `finarg config set AFIP_CUIT=20XXXXXXXXX`

## Flow completo

### Paso 1: Leer la factura

Usar `analyze_document` para extraer datos del PDF/imagen:

```
analyze_document(
  path="/ruta/al/archivo.pdf",
  prompt="Extraé de esta factura argentina: CUIT del proveedor (11 dígitos sin guiones), razón social/denominación, fecha de emisión (DD/MM/YYYY), tipo de comprobante (ej: Factura B, Factura C), punto de venta (4-5 dígitos), número de comprobante (8 dígitos), monto total. Devolvé en JSON."
)
```

### Paso 2: Confirmar datos con el usuario

Mostrar los datos extraídos y pedir:
- Confirmación de que los datos son correctos
- **Categoría de deducción** (el usuario la elige, NO auto-detectar):
  - Gastos médicos / Honorarios médicos
  - Cuotas médico asistencial (prepaga/obra social)
  - Indumentaria y equipamiento
  - Alquiler de inmueble
  - Primas de seguro
  - Donaciones
  - Servicio doméstico
  - Cuotas sindicales
  - Gastos de educación
  - Intereses préstamo hipotecario

### Paso 3: Login en AFIP

URL: `https://auth.afip.gob.ar/contribuyente_/login.xhtml`

**Con clave fiscal guardada:**
1. `browser_navigate` a la URL de login
2. `browser_snapshot` para ver el estado
3. Buscar el campo CUIT: selector `[id="F1:username"]`
4. `browser_type` el CUIT
5. Click en "Siguiente": selector `[id="F1:btnSiguiente"]`
6. Esperar carga
7. `browser_snapshot` — verificar que aparece el campo de contraseña
8. Buscar campo contraseña: `[id="F1:password"]`
9. `browser_type` la clave fiscal
10. Click en "Ingresar": `[id="F1:btnIngresar"]`

**Si aparece captcha:**
Decirle al usuario: "Apareció un captcha en el login de AFIP. Por favor resolvelo en el browser y avisame cuando estés logueado."

**Sin clave fiscal (login manual):**
1. `browser_navigate` a la URL de login
2. Decirle al usuario: "Abrí el browser y logueate en AFIP. Avisame cuando estés en el portal."
3. Esperar que el usuario confirme

### Paso 4: Navegar al SIRADIG

1. `browser_snapshot` — buscar link "SiRADIG - Trabajador"
2. Click en el link del servicio
3. Puede abrir nueva pestaña — hacer `browser_snapshot` para verificar
4. Si aparece pantalla de "persona representada", click en `input.btn_empresa`
5. Seleccionar período (año): selector `#codigo`, valor = año actual
6. Click "Continuar": `#btn_continuar`
7. Manejar modals que aparezcan (ver sección "Modals")

### Paso 5: Ir a Deducciones

1. Click en la pestaña del formulario: `#tab_principal_carga_formulario`
2. Click en la sección "3 - Deducciones y desgravaciones"
3. Click "Agregar": `#btn_agregar_deducciones`
4. En el menú de deducciones, click en la categoría elegida por el usuario

### Paso 6: Llenar el formulario de deducción

1. Campo CUIT proveedor: `#numeroDoc` — ingresar CUIT del proveedor (11 dígitos)
2. Campo concepto: `#idConcepto` — seleccionar según categoría
3. Campo mes: `#mesDesde` — seleccionar mes de la factura (1-12)

### Paso 7: Agregar comprobante

1. Click "Agregar comprobante": `#btn_alta_comprobante`
2. En el modal que aparece:
   - Fecha emisión: `#cmpFechaEmision` — formato DD/MM/YYYY
   - Tipo: `#cmpTipo` — código según tabla:
     - Factura B = 6
     - Nota de Débito B = 7
     - Nota de Crédito B = 8
     - Factura C = 11
     - Nota de Débito C = 12
     - Nota de Crédito C = 13
   - Punto de venta: `#cmpPuntoVenta` — 4-5 dígitos
   - Número: `#cmpNumero` — 8 dígitos
   - Monto: `#cmpMontoFacturado`
   - Monto reintegrado (si aplica): `#cmpMontoReintegrado`
3. Click "Agregar": `.ui-dialog-buttonset button:has-text("Agregar")`

### Paso 8: Guardar

1. Click "Guardar": `#btn_guardar`
2. Confirmar al usuario que se guardó correctamente

## Manejo de modals

AFIP muestra modals informativos aleatorios. Intentar cerrarlos con estos selectores en orden:
1. `button:has-text("Aceptar")`
2. `button:has-text("Continuar")`
3. `button:has-text("Cerrar")`
4. `.ui-dialog-buttonset button`
5. `#btn_aceptar`
6. `.ui-dialog-titlebar-close`

Si ninguno funciona, hacer `browser_snapshot` y evaluar qué dice el modal.

## Múltiples facturas

Si el usuario da una carpeta con varios archivos:
1. Leer cada archivo con `analyze_document`
2. Mostrar tabla resumen de todas las facturas
3. Pedir confirmación
4. Logear una sola vez
5. Cargar cada factura secuencialmente en SIRADIG
6. Confirmar cada una antes de guardar

## Referencia

Ver `references/selectors.md` para la tabla completa de selectores y mappings.
