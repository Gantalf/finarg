---
name: arca-facturacion
description: Facturación electrónica argentina via ARCA (ex AFIP) usando @ramiidv/arca-sdk
version: 1.0.0
prerequisites:
  env_vars: [ARCA_CUIT, ARCA_CERT_PATH, ARCA_KEY_PATH]
  commands: [node]
---

# ARCA Facturación Electrónica

Emite facturas, notas de crédito/débito, y consulta contribuyentes usando el SDK `@ramiidv/arca-sdk` (TypeScript/Node.js).

## Setup (una sola vez)

### 1. Instalar el SDK

```bash
npm install -g @ramiidv/arca-sdk
```

### 2. Configurar credenciales

El usuario debe configurar estas variables con `finarg config set`:

```bash
finarg config set ARCA_CUIT=20123456789
finarg config set ARCA_CERT_PATH=/path/to/cert.crt
finarg config set ARCA_KEY_PATH=/path/to/key.key
finarg config set ARCA_PRODUCTION=false
```

- **Testing**: generar certificado en https://wsass-homo.afip.gob.ar/wsass/portal/main.aspx
- **Producción**: generar en https://www.afip.gob.ar/ws/documentacion/certificados.asp (requiere clave fiscal)

## Cómo ejecutar

Todos los scripts se ejecutan con `terminal` usando Node.js. El patrón base:

```javascript
node -e "
const fs = require('fs');
const { Arca, CbteTipo, IvaTipo, DocTipo, CondicionIva } = require('@ramiidv/arca-sdk');

const arca = new Arca({
  cuit: Number(process.env.ARCA_CUIT),
  cert: fs.readFileSync(process.env.ARCA_CERT_PATH, 'utf-8'),
  key: fs.readFileSync(process.env.ARCA_KEY_PATH, 'utf-8'),
  production: process.env.ARCA_PRODUCTION === 'true',
});

// ... operación ...
"
```

## Operaciones disponibles

### Factura B — Consumidor final

```javascript
const result = await arca.facturar({
  ptoVta: 1,
  cbteTipo: CbteTipo.FACTURA_B,
  items: [{ neto: 1000, iva: IvaTipo.IVA_21 }],
});
console.log(JSON.stringify({
  aprobada: result.aprobada,
  cae: result.cae,
  cbteNro: result.cbteNro,
  total: result.importes.total,
}));
```

### Factura A — Servicios a empresa (Responsable Inscripto)

```javascript
const result = await arca.facturar({
  ptoVta: 1,
  cbteTipo: CbteTipo.FACTURA_A,
  docTipo: DocTipo.CUIT,
  docNro: 30712345678,
  condicionIva: CondicionIva.RESPONSABLE_INSCRIPTO,
  items: [{ neto: 50000, iva: IvaTipo.IVA_21 }],
  servicio: {
    desde: new Date('2026-03-01'),
    hasta: new Date('2026-03-31'),
    vtoPago: new Date('2026-04-15'),
  },
});
```

### Factura C — Monotributista

```javascript
const result = await arca.facturar({
  ptoVta: 1,
  cbteTipo: CbteTipo.FACTURA_C,
  items: [{ neto: 5000 }],
});
```

### Nota de Crédito

El tipo se infiere automáticamente del comprobante original.

```javascript
const result = await arca.notaCredito({
  ptoVta: 1,
  comprobanteOriginal: {
    tipo: CbteTipo.FACTURA_B,
    ptoVta: 1,
    nro: 150,
  },
  items: [{ neto: 100, iva: IvaTipo.IVA_21 }],
});
```

### Nota de Débito

```javascript
const result = await arca.notaDebito({
  ptoVta: 1,
  comprobanteOriginal: {
    tipo: CbteTipo.FACTURA_A,
    ptoVta: 1,
    nro: 200,
  },
  docTipo: DocTipo.CUIT,
  docNro: 30712345678,
  condicionIva: CondicionIva.RESPONSABLE_INSCRIPTO,
  items: [{ neto: 500, iva: IvaTipo.IVA_21 }],
});
```

### Factura de Exportación

```javascript
const result = await arca.facturarExpo({
  ptoVta: 1,
  cbteTipo: CbteTipo.FACTURA_E,
  tipoExpo: 2, // 1=Bienes, 2=Servicios, 4=Otros
  pais: 203,   // 203 = Estados Unidos
  cliente: {
    nombre: 'ACME Corp',
    cuitPais: 50000000016,
    domicilio: '123 Main St, New York',
    idImpositivo: '12-3456789',
  },
  moneda: 'DOL',
  cotizacion: 1200,
  formaPago: 'Wire Transfer',
  incoterms: 'FOB',
  idioma: 2,
  items: [{
    codigo: 'SKU001',
    descripcion: 'Consulting services',
    cantidad: 1,
    unidad: 7,
    precioUnitario: 1000,
  }],
});
```

### Consultar contribuyente (Padrón)

```javascript
const persona = await arca.consultarCuit(30712345678);
console.log(JSON.stringify({
  nombre: persona.nombre,
  tipoPersona: persona.tipoPersona,
  estadoClave: persona.estadoClave,
  impuestos: persona.impuestos,
}));
```

### Consultar último comprobante

```javascript
const ultimo = await arca.ultimoComprobante(1, CbteTipo.FACTURA_B);
console.log(JSON.stringify({ ultimoComprobante: ultimo }));
```

### Cotización de moneda

```javascript
const { Moneda } = require('@ramiidv/arca-sdk');
const cotiz = await arca.getCotizacion(Moneda.DOLARES);
console.log(JSON.stringify(cotiz));
```

### Generar QR para factura impresa

```javascript
const url = Arca.generateQRUrl({
  fecha: '2026-03-28',
  cuit: 20123456789,
  ptoVta: 1,
  tipoCmp: CbteTipo.FACTURA_B,
  nroCmp: 150,
  importe: 121,
  moneda: 'PES',
  ctz: 1,
  tipoDocRec: DocTipo.CONSUMIDOR_FINAL,
  nroDocRec: 0,
  codAut: 73429843294823,
});
console.log(url);
```

### Previsualizar totales sin emitir

```javascript
const { importes, iva } = Arca.calcularTotales([
  { neto: 1000, iva: IvaTipo.IVA_21 },
  { neto: 500, iva: IvaTipo.IVA_10_5 },
]);
console.log(JSON.stringify(importes));
// { total: 1762.5, neto: 1500, iva: 262.5, exento: 0, noGravado: 0, tributos: 0 }
```

## Tipos de comprobante

| Tipo | Código | Quién lo usa |
|------|--------|-------------|
| Factura A | 1 | Resp. Inscripto → Resp. Inscripto |
| Factura B | 6 | Resp. Inscripto → Consumidor Final |
| Factura C | 11 | Monotributista → Cualquiera |
| Factura E | 19 | Exportación |
| Factura M | 51 | Nuevos inscriptos (primeros 12 meses) |

## Alícuotas de IVA

| Enum | Porcentaje |
|------|-----------|
| `IVA_0` | 0% |
| `IVA_2_5` | 2.5% |
| `IVA_5` | 5% |
| `IVA_10_5` | 10.5% |
| `IVA_21` | 21% |
| `IVA_27` | 27% |

## Errores comunes

- **ArcaAuthError**: Certificado inválido o expirado. Regenerar en ARCA.
- **ArcaWSFEError**: Error de negocio (CUIT no autorizado, punto de venta inválido, etc.). Revisar `e.errors[].code` y `e.errors[].msg`.
- **ArcaSoapError**: Error de red/servidor. Reintentar.

## Referencia

- SDK: https://github.com/ramiidv/arca-facturacion
- ARCA Web Services: https://www.afip.gob.ar/ws/
- Certificados testing: https://wsass-homo.afip.gob.ar/wsass/portal/main.aspx
