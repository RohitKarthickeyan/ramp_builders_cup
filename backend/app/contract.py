"""Turn an agreed offer into a structured contract draft for human approval."""
from __future__ import annotations

import datetime

from .models import BuyerConfig, Contract, Offer, Vendor


def build(buyer: BuyerConfig, vendor: Vendor, offer: Offer) -> Contract:
    seats = buyer.seats
    annual = offer.annual_total(seats)
    list_annual = round(vendor.list_price_per_seat * seats * 12, 2)
    savings = round(list_annual - annual, 2)
    savings_pct = round(100 * savings / list_annual, 1) if list_annual else 0.0
    effective = datetime.date.today().isoformat()

    clauses = [
        f"{buyer.company} commits to {seats} seats of {vendor.name} for a "
        f"{offer.contract_length_months}-month term.",
        f"Price locked at ${offer.price_per_seat:.2f} per seat / month, billed annually.",
    ]
    if offer.free_seats:
        clauses.append(f"{offer.free_seats} additional seats provided at no charge.")
    clauses.append(f"Support level: {offer.support_tier}.")
    clauses.append("Price protection: no increase on renewal beyond 5% for one additional term.")
    clauses.append("30-day out for cause; data export provided in standard formats on termination.")

    return Contract(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        buyer_company=buyer.company,
        seats=seats,
        price_per_seat=offer.price_per_seat,
        contract_length_months=offer.contract_length_months,
        free_seats=offer.free_seats,
        support_tier=offer.support_tier,
        annual_total=annual,
        list_annual_total=list_annual,
        savings=savings,
        savings_pct=savings_pct,
        effective_date=effective,
        clauses=clauses,
    )
