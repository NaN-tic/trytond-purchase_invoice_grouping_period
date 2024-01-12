# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import party
from . import purchase


def register():
    Pool.register(
        party.Party,
        party.PartyPurchaseInvoiceGroupingMethod,
        purchase.Purchase,
        purchase.PurchaseLine,
        module='purchase_invoice_grouping_period', type_='model')
