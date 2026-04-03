"""SIRADIG tools: deterministic browser automation for AFIP tax deductions.

Two tools that encapsulate full flows (no LLM decisions mid-flow):
- siradig_login: login + navigate to SIRADIG form
- siradig_add_deduction: fill deduction form + save

Based on tomastoloza/siradig-uploader (Playwright flow replicated with agent-browser CLI).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import shutil
import time
from typing import Any

from finarg.constants import ENV_FILE

log = logging.getLogger(__name__)

# ── Selectores (from siradig-uploader) ─────────────────────────────

LOGIN = {
    "username": '[id="F1:username"]',
    "next_btn": '[id="F1:btnSiguiente"]',
    "password": '[id="F1:password"]',
    "submit_btn": '[id="F1:btnIngresar"]',
}

NAV = {
    "service_link": "text=SiRADIG - Trabajador",
    "represented_btn": "input.btn_empresa",
    "period_select": "#codigo",
    "continue_btn": "#btn_continuar",
    "form_tab": "#tab_principal_carga_formulario",
    "deductions_header": 'text=/3 -.*Deducciones y desgravaciones/i',
    "add_deduction_btn": "#btn_agregar_deducciones",
    "menu_container": "#menu_deducciones",
}

FORM = {
    "cuit": "#numeroDoc",
    "concept": "#idConcepto",
    "month": "#mesDesde",
    "add_voucher_btn": "#btn_alta_comprobante",
    "modal_container": "#dialog_alta_comprobante",
    "save_btn": "#btn_guardar",
    "back_btn": "#btn_volver",
}

MODAL = {
    "date": "#cmpFechaEmision",
    "type": "#cmpTipo",
    "pos": "#cmpPuntoVenta",
    "num": "#cmpNumero",
    "amount": "#cmpMontoFacturado",
    "reimbursed": "#cmpMontoReintegrado",
    "submit": '.ui-dialog-buttonset button:has-text("Agregar")',
}

DISMISS_SELECTORS = [
    'button:has-text("Aceptar")',
    'button:has-text("Continuar")',
    'button:has-text("Cerrar")',
    ".ui-dialog-buttonset button",
    "#btn_aceptar",
    ".ui-dialog-titlebar-close",
]

CATEGORY_LINKS = {
    "gastos_medicos": "#link_agregar_gastos_medicos",
    "indumentaria": "#link_agregar_gastos_indu_equip",
    "alquiler": "#link_agregar_alquileres",
    "seguros": "#link_agregar_seguros",
    "servicio_domestico": "#link_agregar_serv_domestico",
    "donaciones": "#link_agregar_donaciones",
    "cuotas_sindicales": "#link_agregar_cuotas_sindicales",
}

MONTHS = {
    "enero": "1", "febrero": "2", "marzo": "3", "abril": "4",
    "mayo": "5", "junio": "6", "julio": "7", "agosto": "8",
    "septiembre": "9", "octubre": "10", "noviembre": "11", "diciembre": "12",
}

RECEIPT_TYPES = {
    "factura b": "6", "nota de débito b": "7", "nota de crédito b": "8",
    "factura c": "11", "nota de débito c": "12", "nota de crédito c": "13",
    "tique factura b": "6", "tique factura c": "11",
}

# ── agent-browser helpers ──────────────────────────────────────────

_binary: str | None = None


def _find_binary() -> str:
    global _binary
    if _binary:
        return _binary
    path = shutil.which("agent-browser")
    if path:
        _binary = path
        return path
    for c in ("/opt/homebrew/bin/agent-browser", "/usr/local/bin/agent-browser"):
        if shutil.which(c):
            _binary = c
            return c
    npx = shutil.which("npx")
    if npx:
        _binary = "npx agent-browser"
        return _binary
    raise RuntimeError("agent-browser not found")


def _cmd(command: str, args: list[str] | None = None, timeout: int = 30) -> dict:
    """Run agent-browser command with afip session (headed + persistent)."""
    if args is None:
        args = []
    binary = _find_binary()
    flags = ["--session", "finarg-afip", "--headed", "--session-name", "afip", "--json"]

    if binary.startswith("npx "):
        full_cmd = binary.split() + flags + [command] + args
    else:
        full_cmd = [binary] + flags + [command] + args

    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        stdout = result.stdout.strip()
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip() or "command failed"}
        if not stdout:
            return {"success": True}
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"success": True, "raw": result.stdout[:300]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wait(target: str, timeout: int = 10) -> dict:
    return _cmd("wait", [target], timeout=timeout + 5)


def _click(selector: str) -> dict:
    return _cmd("click", [selector])


def _fill(selector: str, text: str) -> dict:
    return _cmd("fill", [selector, text])


def _select(selector: str, value: str) -> dict:
    return _cmd("select", [selector, value])


def _snapshot() -> dict:
    return _cmd("snapshot", ["-c"])


def _sleep(ms: int) -> dict:
    return _cmd("wait", [str(ms)])


def _dismiss_modals() -> None:
    """Try to close any AFIP modal that may have appeared."""
    for selector in DISMISS_SELECTORS:
        try:
            result = _cmd("eval", [
                f"document.querySelector('{selector}')?.click()"
            ], timeout=3)
        except Exception:
            pass
    _sleep(500)


def _load_env() -> dict[str, str]:
    """Load env vars from ~/.finarg/.env."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ── Tool: siradig_login ───────────────────────────────────────────

async def siradig_login(args: dict[str, Any]) -> str:
    """Login to AFIP and navigate to SIRADIG. Deterministic flow."""
    env = _load_env()
    cuit = env.get("AFIP_CUIT", "")
    clave = env.get("AFIP_CLAVE_FISCAL", "")
    period = args.get("period", str(time.localtime().tm_year))

    if not cuit:
        return json.dumps({
            "success": False,
            "error": "AFIP_CUIT not configured",
            "hint": "Run: finarg config set AFIP_CUIT=20XXXXXXXXX",
        })

    if not clave:
        return json.dumps({
            "success": False,
            "error": "AFIP_CLAVE_FISCAL not configured. Cannot do automatic login.",
            "hint": "Run: finarg config set AFIP_CLAVE_FISCAL=yourpassword",
        })

    def _run() -> dict:
        steps: list[str] = []

        # 1. Navigate to AFIP login
        r = _cmd("open", ["https://auth.afip.gob.ar/contribuyente_/login.xhtml"], timeout=30)
        if not r.get("success", True):
            return {"success": False, "error": f"Failed to open AFIP: {r.get('error')}"}
        steps.append("Opened AFIP login page")

        _sleep(2000)

        # 2. Check if already logged in (session persisted)
        snap = _snapshot()
        snap_text = json.dumps(snap).lower()
        if "siradig" in snap_text and "trabajador" in snap_text:
            steps.append("Already logged in (session restored)")
            # Click SIRADIG link
            _click(NAV["service_link"])
            _sleep(3000)
            steps.append("Navigated to SIRADIG")
        else:
            # 3. Fill CUIT
            _fill(LOGIN["username"], cuit)
            _sleep(500)
            _click(LOGIN["next_btn"])
            _sleep(2000)
            steps.append(f"Entered CUIT: {cuit}")

            # 4. Fill password
            r = _wait(LOGIN["password"], timeout=10)
            _fill(LOGIN["password"], clave)
            _sleep(500)
            _click(LOGIN["submit_btn"])
            _sleep(3000)
            steps.append("Entered password and submitted")

            # 5. Check login success
            snap = _snapshot()
            snap_text = json.dumps(snap).lower()
            if "error" in snap_text and ("clave" in snap_text or "password" in snap_text):
                return {"success": False, "error": "Login failed. Check AFIP_CLAVE_FISCAL."}

            # 6. Navigate to SIRADIG
            _wait(NAV["service_link"], timeout=15)
            _click(NAV["service_link"])
            _sleep(3000)
            steps.append("Clicked SIRADIG service link")

        # 7. Handle represented person (if shown)
        try:
            _cmd("eval", [
                f"document.querySelector('{NAV['represented_btn']}')?.click()"
            ], timeout=3)
            _sleep(1000)
            steps.append("Selected represented person")
        except Exception:
            pass

        # 8. Select period
        _wait(NAV["period_select"], timeout=10)
        _select(NAV["period_select"], period)
        _click(NAV["continue_btn"])
        _sleep(2000)
        steps.append(f"Selected period: {period}")

        # 9. Dismiss any modals
        _dismiss_modals()
        steps.append("Dismissed modals (if any)")

        return {"success": True, "message": "Logged in and navigated to SIRADIG", "steps": steps}

    result = await asyncio.to_thread(_run)
    return json.dumps(result, ensure_ascii=False)


# ── Tool: siradig_add_deduction ────────────────────────────────────

async def siradig_add_deduction(args: dict[str, Any]) -> str:
    """Fill a deduction form in SIRADIG and save. Deterministic flow."""
    category = args.get("category", "").lower().replace(" ", "_")
    provider_cuit = args.get("provider_cuit", "")
    concept = args.get("concept", "")
    month = args.get("month", "").lower()
    voucher_date = args.get("voucher_date", "")
    voucher_type = args.get("voucher_type", "").lower()
    voucher_pos = args.get("voucher_pos", "")
    voucher_number = args.get("voucher_number", "")
    voucher_amount = args.get("voucher_amount", "")
    voucher_reimbursed = args.get("voucher_reimbursed", "")

    # Validate required fields
    missing = []
    if not category:
        missing.append("category")
    if not provider_cuit:
        missing.append("provider_cuit")
    if not month:
        missing.append("month")
    if not voucher_date:
        missing.append("voucher_date")
    if not voucher_type:
        missing.append("voucher_type")
    if not voucher_pos:
        missing.append("voucher_pos")
    if not voucher_number:
        missing.append("voucher_number")
    if not voucher_amount:
        missing.append("voucher_amount")
    if missing:
        return json.dumps({"success": False, "error": f"Missing fields: {', '.join(missing)}"})

    # Resolve mappings
    category_link = CATEGORY_LINKS.get(category)
    if not category_link:
        return json.dumps({
            "success": False,
            "error": f"Unknown category: {category}",
            "available": list(CATEGORY_LINKS.keys()),
        })

    month_value = MONTHS.get(month)
    if not month_value:
        return json.dumps({"success": False, "error": f"Unknown month: {month}", "available": list(MONTHS.keys())})

    receipt_code = RECEIPT_TYPES.get(voucher_type)
    if not receipt_code:
        return json.dumps({
            "success": False,
            "error": f"Unknown voucher type: {voucher_type}",
            "available": list(RECEIPT_TYPES.keys()),
        })

    def _run() -> dict:
        steps: list[str] = []

        # 1. Open deductions form
        _dismiss_modals()

        # Click form tab
        _cmd("eval", [f"document.querySelector('{NAV['form_tab']}')?.click()"], timeout=5)
        _sleep(2000)
        steps.append("Clicked form tab")

        # Click deductions header
        _cmd("eval", [
            "const el = Array.from(document.querySelectorAll('a, span, div, td'))"
            ".find(e => e.textContent?.includes('Deducciones y desgravaciones'));"
            "if(el) el.click();"
        ], timeout=5)
        _sleep(1000)
        steps.append("Clicked deductions section")

        # Click add deduction
        _wait(NAV["add_deduction_btn"], timeout=10)
        _cmd("eval", [f"document.querySelector('{NAV['add_deduction_btn']}')?.click()"], timeout=5)
        _sleep(1000)
        steps.append("Clicked add deduction")

        # Wait for menu
        _wait(NAV["menu_container"], timeout=5)

        # 2. Select category
        _click(category_link)
        _sleep(2000)
        steps.append(f"Selected category: {category}")

        # 3. Fill provider CUIT
        _fill(FORM["cuit"], provider_cuit)
        _cmd("press", ["Tab"])
        _sleep(1500)
        steps.append(f"Filled provider CUIT: {provider_cuit}")

        # 4. Select concept (for indumentaria)
        if concept and category == "indumentaria":
            concept_value = "1" if concept.lower() == "indumentaria" else "2"
            _select(FORM["concept"], concept_value)
            steps.append(f"Selected concept: {concept}")

        # 5. Select month
        _select(FORM["month"], month_value)
        steps.append(f"Selected month: {month}")

        # 6. Add voucher
        _click(FORM["add_voucher_btn"])
        _wait(FORM["modal_container"], timeout=5)
        _sleep(500)
        steps.append("Opened voucher modal")

        # 7. Fill voucher fields
        _fill(MODAL["date"], voucher_date)
        _select(MODAL["type"], receipt_code)
        _fill(MODAL["pos"], voucher_pos)
        _fill(MODAL["num"], voucher_number)
        _fill(MODAL["amount"], voucher_amount)
        if voucher_reimbursed:
            _fill(MODAL["reimbursed"], voucher_reimbursed)
        steps.append("Filled voucher data")

        # 8. Submit voucher
        _click(MODAL["submit"])
        _sleep(2000)
        _dismiss_modals()
        steps.append("Submitted voucher")

        # 9. Save
        save_selectors = [FORM["save_btn"], 'a:has-text("Guardar")', 'button:has-text("Guardar")']
        for sel in save_selectors:
            try:
                r = _cmd("eval", [f"document.querySelector('{sel}')?.click()"], timeout=3)
                break
            except Exception:
                continue
        _sleep(2000)
        _dismiss_modals()
        steps.append("Saved deduction")

        # 10. Return to dashboard
        back_selectors = [FORM["back_btn"], 'a:has-text("Volver")', 'button:has-text("Volver")']
        for sel in back_selectors:
            try:
                _cmd("eval", [f"document.querySelector('{sel}')?.click()"], timeout=3)
                break
            except Exception:
                continue
        _sleep(1000)
        steps.append("Returned to dashboard")

        return {"success": True, "message": "Deduction saved successfully", "steps": steps}

    result = await asyncio.to_thread(_run)
    return json.dumps(result, ensure_ascii=False)


# ── Registration ───────────────────────────────────────────────────

def register_siradig_tools() -> None:
    """Register SIRADIG tools."""
    from finarg.tools.registry import registry

    registry.register(
        name="siradig_login",
        toolset="siradig",
        description=(
            "Login to AFIP and navigate to SIRADIG tax deductions form. "
            "Opens a visible browser window, logs in with stored credentials (AFIP_CUIT + AFIP_CLAVE_FISCAL), "
            "navigates to SIRADIG, and selects the fiscal period. "
            "Session is persisted — subsequent calls reuse the login. "
            "Must be called BEFORE siradig_add_deduction."
        ),
        parameters={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Fiscal year (default: current year)",
                },
            },
            "required": [],
        },
        handler=siradig_login,
        emoji="\U0001f510",
    )

    registry.register(
        name="siradig_add_deduction",
        toolset="siradig",
        description=(
            "Fill and save a tax deduction in SIRADIG. Must call siradig_login first. "
            "Categories: gastos_medicos, indumentaria, alquiler, seguros, servicio_domestico, donaciones, cuotas_sindicales."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["gastos_medicos", "indumentaria", "alquiler", "seguros",
                             "servicio_domestico", "donaciones", "cuotas_sindicales"],
                    "description": "Deduction category",
                },
                "provider_cuit": {
                    "type": "string",
                    "description": "Provider CUIT (11 digits, no dashes)",
                },
                "concept": {
                    "type": "string",
                    "description": "For indumentaria: 'Indumentaria' or 'Equipamiento'",
                },
                "month": {
                    "type": "string",
                    "description": "Month name in Spanish (e.g. 'Marzo')",
                },
                "voucher_date": {
                    "type": "string",
                    "description": "Invoice date (DD/MM/YYYY)",
                },
                "voucher_type": {
                    "type": "string",
                    "description": "Invoice type (e.g. 'Factura B', 'Factura C', 'Tique Factura B')",
                },
                "voucher_pos": {
                    "type": "string",
                    "description": "Point of sale number (4-5 digits)",
                },
                "voucher_number": {
                    "type": "string",
                    "description": "Invoice number (8 digits)",
                },
                "voucher_amount": {
                    "type": "string",
                    "description": "Total amount",
                },
                "voucher_reimbursed": {
                    "type": "string",
                    "description": "Reimbursed amount (for medical expenses, optional)",
                },
            },
            "required": ["category", "provider_cuit", "month", "voucher_date",
                         "voucher_type", "voucher_pos", "voucher_number", "voucher_amount"],
        },
        handler=siradig_add_deduction,
        emoji="\U0001f4dd",
    )
