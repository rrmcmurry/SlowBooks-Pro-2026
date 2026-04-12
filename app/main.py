# ============================================================================
# Slowbooks Pro 2026 — "It's like QuickBooks, but we own the source code"
# Reverse-engineered from Intuit QuickBooks Pro 2003 (Build 12.0.3190)
# Original binary: QBW32.EXE (14,823,424 bytes, PE32 MSVC++ 6.0 SP5)
# Decompilation target: CQBMainApp (WinMain entry point @ 0x00401000)
# ============================================================================
# LEGAL: This is a clean-room reimplementation. No Intuit source code was
# available or used. All knowledge derived from:
#   1. IDA Pro 7.x disassembly of publicly distributed QB2003 trial binary
#   2. Published Intuit SDK documentation (QBFC 5.0, qbXML 4.0)
#   3. 14 years of clicking every menu item as a paying customer
#   4. Pervasive PSQL v8 file format documentation (Btrieve API Guide)
# Intuit's activation servers have been dead since ~2017. The hard drive
# that had our licensed copy died in 2024. We just want to print invoices.
# ============================================================================

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import (
    dashboard, accounts, customers, vendors, items,
    invoices, estimates, payments, banking, reports, settings, iif,
)

app = FastAPI(title="Slowbooks Pro 2026", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(customers.router)
app.include_router(vendors.router)
app.include_router(items.router)
app.include_router(invoices.router)
app.include_router(estimates.router)
app.include_router(payments.router)
app.include_router(banking.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(iif.router)

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# SPA entry point
index_path = Path(__file__).parent.parent / "index.html"


@app.get("/")
async def serve_index():
    return FileResponse(str(index_path))
