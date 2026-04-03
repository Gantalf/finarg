"""SIRADIG tools: deterministic Playwright automation for AFIP tax deductions.

Replicates tomastoloza/siradig-uploader AfipService using Playwright directly.
Two tools that encapsulate full flows — no LLM decisions mid-flow.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from finarg.constants import ENV_FILE, FINARG_HOME

log = logging.getLogger(__name__)

# ── Selectors (from siradig-uploader) ──────────────────────────────

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

# ── Persistent state ───────────────────────────────────────────────

AUTH_STATE_PATH = FINARG_HOME / "afip_auth_state.json"

# Playwright browser/page kept alive between tool calls within a session
_browser = None
_page = None


def _load_env() -> dict[str, str]:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


async def _dismiss_modals(page) -> None:
    """Try to close any AFIP modal."""
    for _ in range(5):
        found = False
        for selector in DISMISS_SELECTORS:
            try:
                if await page.is_visible(selector):
                    await page.click(selector, timeout=2000)
                    await page.wait_for_timeout(500)
                    found = True
            except Exception:
                pass
        if not found:
            break


async def _get_browser_and_page():
    """Get or create Playwright browser + page with persistent auth state."""
    global _browser, _page

    if _browser and _page:
        try:
            # Check if page is still alive
            await _page.title()
            return _browser, _page
        except Exception:
            _browser = None
            _page = None

    from playwright.async_api import async_playwright

    pw = await async_playwright().start()

    storage_state = str(AUTH_STATE_PATH) if AUTH_STATE_PATH.exists() else None

    _browser = await pw.chromium.launch(headless=False)
    context = await _browser.new_context(storage_state=storage_state)
    _page = await context.new_page()

    return _browser, _page


async def _save_auth_state():
    """Save session cookies/storage for reuse."""
    global _page
    if _page:
        try:
            await _page.context.storage_state(path=str(AUTH_STATE_PATH))
        except Exception:
            pass


# ── Tool: siradig_login ───────────────────────────────────────────

async def siradig_login(args: dict[str, Any]) -> str:
    """Login to AFIP and navigate to SIRADIG. Exact replica of siradig-uploader."""
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
            "error": "AFIP_CLAVE_FISCAL not configured",
            "hint": "Run: finarg config set AFIP_CLAVE_FISCAL=yourpassword",
        })

    try:
        browser, page = await _get_browser_and_page()
        steps: list[str] = []

        # 1. Navigate to AFIP login
        await page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml")
        await page.wait_for_load_state("networkidle")
        steps.append("Opened AFIP login")

        # 2. Check if already logged in (session restored)
        try:
            if await page.is_visible(NAV["service_link"]):
                steps.append("Already logged in (session restored)")
                # Go directly to SIRADIG
                await page.click(NAV["service_link"])
                new_page = await page.context.wait_for_event("page")
                _page_ref_update(new_page)
                await new_page.wait_for_load_state("networkidle")
                steps.append("Navigated to SIRADIG")

                await _handle_represented_person(new_page, steps)
                await _select_period(new_page, period, steps)
                await _save_auth_state()

                return json.dumps({"success": True, "message": "Logged in and navigated to SIRADIG", "steps": steps})
        except Exception:
            pass

        # 3. Fill CUIT
        await page.fill(LOGIN["username"], cuit)
        await page.click(LOGIN["next_btn"])
        await page.wait_for_load_state("networkidle")
        steps.append(f"Entered CUIT")

        # 4. Fill password
        await page.fill(LOGIN["password"], clave)
        await page.click(LOGIN["submit_btn"])
        await page.wait_for_load_state("networkidle")
        steps.append("Entered password and submitted")

        # 5. Save session
        await _save_auth_state()
        steps.append("Session saved")

        # 6. Navigate to SIRADIG
        await page.wait_for_selector(NAV["service_link"], timeout=15000)
        await page.click(NAV["service_link"])

        # SIRADIG opens in new tab
        new_page = await page.context.wait_for_event("page")
        _page_ref_update(new_page)
        await new_page.wait_for_load_state("networkidle")
        steps.append("Navigated to SIRADIG")

        # 7. Handle represented person
        await _handle_represented_person(new_page, steps)

        # 8. Select period
        await _select_period(new_page, period, steps)

        return json.dumps({"success": True, "message": "Logged in and navigated to SIRADIG", "steps": steps})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def _page_ref_update(new_page):
    """Update the global page reference when SIRADIG opens in a new tab."""
    global _page
    _page = new_page


async def _handle_represented_person(page, steps: list[str]) -> None:
    try:
        await page.wait_for_selector(NAV["represented_btn"], timeout=5000)
        await page.click(NAV["represented_btn"])
        steps.append("Selected represented person")
    except Exception:
        pass


async def _select_period(page, period: str, steps: list[str]) -> None:
    try:
        # Check if period select exists (some flows skip it or pass via URL)
        try:
            await page.wait_for_selector(NAV["period_select"], timeout=5000)
            await page.select_option(NAV["period_select"], period)
            await page.click(NAV["continue_btn"])
            await page.wait_for_load_state("networkidle")
            steps.append(f"Selected period: {period}")
        except Exception:
            # Period may already be set (URL param) — check if we're in SIRADIG
            if "codigo=" in page.url or "radig" in page.url:
                steps.append(f"Period already set (via URL)")
            else:
                steps.append(f"Period selection skipped")

        # Always dismiss modals after period (AFIP shows "Recordatorio" modal)
        await _dismiss_modals(page)
        await page.wait_for_timeout(1000)
        await _dismiss_modals(page)
    except Exception as e:
        steps.append(f"Period error: {e}")


# ── Tool: siradig_add_deduction ────────────────────────────────────

async def siradig_add_deduction(args: dict[str, Any]) -> str:
    """Fill and save a deduction in SIRADIG. Exact replica of siradig-uploader."""
    global _page

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

    # Validate
    missing = [f for f in ["category", "provider_cuit", "month", "voucher_date",
                           "voucher_type", "voucher_pos", "voucher_number", "voucher_amount"]
               if not args.get(f)]
    if missing:
        return json.dumps({"success": False, "error": f"Missing: {', '.join(missing)}"})

    category_link = CATEGORY_LINKS.get(category)
    if not category_link:
        return json.dumps({"success": False, "error": f"Unknown category: {category}", "available": list(CATEGORY_LINKS.keys())})

    month_value = MONTHS.get(month)
    if not month_value:
        return json.dumps({"success": False, "error": f"Unknown month: {month}"})

    receipt_code = RECEIPT_TYPES.get(voucher_type)
    if not receipt_code:
        return json.dumps({"success": False, "error": f"Unknown voucher type: {voucher_type}", "available": list(RECEIPT_TYPES.keys())})

    if not _page:
        return json.dumps({"success": False, "error": "Not logged in. Call siradig_login first."})

    try:
        page = _page
        steps: list[str] = []

        await _dismiss_modals(page)

        # 1. Open deductions form (replica of openDeductionsForm)
        await page.wait_for_selector(NAV["form_tab"], state="attached")
        await page.evaluate(f"document.querySelector('{NAV['form_tab']}')?.click()")
        await page.wait_for_load_state("networkidle")

        # Click deductions header
        try:
            await page.wait_for_selector(NAV["deductions_header"], timeout=5000)
            await page.click(NAV["deductions_header"])
            await page.wait_for_timeout(1000)
        except Exception:
            await page.evaluate(
                "const t = Array.from(document.querySelectorAll('a, span, div, td'))"
                ".find(e => e.textContent?.includes('Deducciones y desgravaciones'));"
                "if(t) t.click();"
            )

        await page.wait_for_selector(NAV["add_deduction_btn"], timeout=10000)
        await page.click(NAV["add_deduction_btn"], force=True)
        await page.wait_for_selector(NAV["menu_container"], state="visible", timeout=5000)
        steps.append("Opened deductions form")

        # 2. Select category (replica of startProviderEntry)
        await page.click(category_link)
        await page.wait_for_load_state("networkidle")
        steps.append(f"Selected category: {category}")

        # 3. Fill provider CUIT
        await page.fill(FORM["cuit"], provider_cuit)
        await page.press(FORM["cuit"], "Tab")
        await page.wait_for_timeout(1500)
        steps.append(f"Filled provider CUIT")

        # 4. Select concept (for indumentaria)
        if concept and category == "indumentaria":
            concept_value = "1" if concept.lower() == "indumentaria" else "2"
            await page.select_option(FORM["concept"], concept_value)
            steps.append(f"Selected concept: {concept}")

        # 5. Select month
        await page.select_option(FORM["month"], month_value)
        steps.append(f"Selected month: {month}")

        # 6. Add voucher (replica of addVoucher)
        await page.click(FORM["add_voucher_btn"])
        await page.wait_for_selector(FORM["modal_container"], state="visible")

        await page.fill(MODAL["date"], voucher_date)
        await page.select_option(MODAL["type"], receipt_code)
        await page.fill(MODAL["pos"], voucher_pos)
        await page.fill(MODAL["num"], voucher_number)
        await page.fill(MODAL["amount"], voucher_amount)

        if voucher_reimbursed:
            await page.fill(MODAL["reimbursed"], voucher_reimbursed)

        await page.click(MODAL["submit"])
        await page.wait_for_selector(FORM["modal_container"], state="hidden")
        steps.append("Added voucher")

        # 7. Save (replica of saveAndReturn)
        for sel in [FORM["save_btn"], 'a:has-text("Guardar")', 'button:has-text("Guardar")']:
            try:
                if await page.is_visible(sel):
                    await page.click(sel)
                    break
            except Exception:
                continue
        await page.wait_for_load_state("networkidle")
        await _dismiss_modals(page)
        steps.append("Saved deduction")

        # 8. Return
        for sel in [FORM["back_btn"], 'a:has-text("Volver")', 'button:has-text("Volver")']:
            try:
                if await page.is_visible(sel):
                    await page.click(sel)
                    break
            except Exception:
                continue
        await page.wait_for_load_state("networkidle")
        steps.append("Returned to dashboard")

        return json.dumps({"success": True, "message": "Deduction saved", "steps": steps})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ── Registration ───────────────────────────────────────────────────

def register_siradig_tools() -> None:
    from finarg.tools.registry import registry

    registry.register(
        name="siradig_login",
        toolset="siradig",
        description=(
            "Login to AFIP and navigate to SIRADIG tax deductions form. "
            "Opens a visible browser window, logs in with AFIP_CUIT + AFIP_CLAVE_FISCAL from env, "
            "navigates to SIRADIG, and selects the fiscal period. "
            "Session is persisted — subsequent calls reuse the login. "
            "Must be called BEFORE siradig_add_deduction."
        ),
        parameters={
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Fiscal year (default: current year)"},
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
                },
                "provider_cuit": {"type": "string", "description": "Provider CUIT (11 digits)"},
                "concept": {"type": "string", "description": "For indumentaria: 'Indumentaria' or 'Equipamiento'"},
                "month": {"type": "string", "description": "Month in Spanish (e.g. 'Marzo')"},
                "voucher_date": {"type": "string", "description": "DD/MM/YYYY"},
                "voucher_type": {"type": "string", "description": "e.g. 'Factura B', 'Tique Factura B'"},
                "voucher_pos": {"type": "string", "description": "Point of sale (4-5 digits)"},
                "voucher_number": {"type": "string", "description": "Invoice number (8 digits)"},
                "voucher_amount": {"type": "string", "description": "Total amount"},
                "voucher_reimbursed": {"type": "string", "description": "Reimbursed amount (optional)"},
            },
            "required": ["category", "provider_cuit", "month", "voucher_date",
                         "voucher_type", "voucher_pos", "voucher_number", "voucher_amount"],
        },
        handler=siradig_add_deduction,
        emoji="\U0001f4dd",
    )
