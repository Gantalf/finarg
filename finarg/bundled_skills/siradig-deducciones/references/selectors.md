# SIRADIG Form Selectors

Reference selectors for browser automation. Source: tomastoloza/siradig-uploader

## Login (AFIP)

| Element | Selector |
|---------|----------|
| CUIT input | `[id="F1:username"]` |
| Next button | `[id="F1:btnSiguiente"]` |
| Password input | `[id="F1:password"]` |
| Submit button | `[id="F1:btnIngresar"]` |

## Navigation (Portal → SIRADIG)

| Element | Selector |
|---------|----------|
| SIRADIG service link | `text=SiRADIG - Trabajador` |
| Represented person button | `input.btn_empresa` |
| Period select | `#codigo` |
| Continue button | `#btn_continuar` |
| Form tab | `#tab_principal_carga_formulario` |
| Deductions header | `text=/3 -.*Deducciones y desgravaciones/i` |
| Add deduction button | `#btn_agregar_deducciones` |
| Deduction menu | `#menu_deducciones` |

## Deduction category links

| Category | Selector |
|----------|----------|
| Gastos médicos | `#link_agregar_gastos_medicos` |
| Indumentaria y equipamiento | `#link_agregar_gastos_indu_equip` |
| Alquiler | `#link_agregar_alquileres` |
| Seguros | `#link_agregar_seguros` |
| Servicio doméstico | `#link_agregar_serv_domestico` |
| Donaciones | `#link_agregar_donaciones` |
| Cuotas sindicales | `#link_agregar_cuotas_sindicales` |

## Deduction form

| Element | Selector |
|---------|----------|
| Provider CUIT | `#numeroDoc` |
| Concept | `#idConcepto` |
| Month | `#mesDesde` |
| Add voucher button | `#btn_alta_comprobante` |
| Save button | `#btn_guardar` |
| Back button | `#btn_volver` |

## Voucher modal

| Element | Selector |
|---------|----------|
| Date | `#cmpFechaEmision` |
| Type | `#cmpTipo` |
| Point of sale | `#cmpPuntoVenta` |
| Number | `#cmpNumero` |
| Amount | `#cmpMontoFacturado` |
| Reimbursed amount | `#cmpMontoReintegrado` |
| Submit (Agregar) | `.ui-dialog-buttonset button:has-text("Agregar")` |

## Mappings

### Months
| Name | Value |
|------|-------|
| Enero | 1 |
| Febrero | 2 |
| Marzo | 3 |
| Abril | 4 |
| Mayo | 5 |
| Junio | 6 |
| Julio | 7 |
| Agosto | 8 |
| Septiembre | 9 |
| Octubre | 10 |
| Noviembre | 11 |
| Diciembre | 12 |

### Receipt types
| Name | Code |
|------|------|
| Factura B | 6 |
| Nota de Débito B | 7 |
| Nota de Crédito B | 8 |
| Factura C | 11 |
| Nota de Débito C | 12 |
| Nota de Crédito C | 13 |

## Dismiss modals

AFIP shows random modals. Try these selectors in order:
1. `button:has-text("Aceptar")`
2. `button:has-text("Continuar")`
3. `button:has-text("Cerrar")`
4. `.ui-dialog-buttonset button`
5. `#btn_aceptar`
6. `.ui-dialog-titlebar-close`
