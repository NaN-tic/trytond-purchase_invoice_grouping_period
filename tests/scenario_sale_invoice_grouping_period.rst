=====================================
Sale Invoice Grouping Period Scenario
=====================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules, set_user
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> from trytond.modules.stock.exceptions import MoveFutureWarning

Install sale_invoice_grouping::

    >>> config = activate_modules('purchase_invoice_grouping_period')

Compute dates after module activation::

    >>> today = datetime.date.today()
    >>> start_month = today - relativedelta(day=1)
    >>> same_biweekly = today - relativedelta(day=10) - relativedelta(months=1)
    >>> past_biweekly = today - relativedelta(day=20) - relativedelta(months=1)
    >>> past_month = today - relativedelta(months=1)
    >>> past_week = today - datetime.timedelta(days=7)
    >>> past_week2 = today - datetime.timedelta(days=14)

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create purchase user::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> purchase_user = User()
    >>> purchase_user.name = 'purchase'
    >>> purchase_user.login = 'purchase'
    >>> purchase_group, = Group.find([('name', '=', 'Purchase')])
    >>> purchase_user.groups.append(purchase_group)
    >>> purchase_group, = Group.find([('name', '=', 'Stock')])
    >>> purchase_user.groups.append(purchase_group)
    >>> purchase_user.save()

Create stock user::

    >>> stock_user = User()
    >>> stock_user.name = 'Stock'
    >>> stock_user.login = 'stock'
    >>> stock_group, = Group.find([('name', '=', 'Stock')])
    >>> stock_user.groups.append(stock_group)
    >>> stock_user.save()

Create account user::

    >>> account_user = User()
    >>> account_user.name = 'Account'
    >>> account_user.login = 'account'
    >>> account_group, = Group.find([('name', '=', 'Account')])
    >>> account_user.groups.append(account_group)
    >>> account_user.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='supplier')
    >>> supplier.save()
    >>> supplier_daily = Party(name='supplier Daily')
    >>> supplier_daily.purchase_invoice_grouping_method = 'standard'
    >>> supplier_daily.purchase_invoice_grouping_period = 'daily'
    >>> supplier_daily.save()
    >>> supplier_weekly = Party(name='supplier BiWeekly')
    >>> supplier_weekly.purchase_invoice_grouping_method = 'standard'
    >>> supplier_weekly.purchase_invoice_grouping_period = 'weekly-0'
    >>> supplier_weekly.save()
    >>> supplier_biweekly = Party(name='supplier BiWeekly')
    >>> supplier_biweekly.purchase_invoice_grouping_method = 'standard'
    >>> supplier_biweekly.purchase_invoice_grouping_period = 'biweekly'
    >>> supplier_biweekly.save()
    >>> supplier_monthly = Party(name='supplier Monthly')
    >>> supplier_monthly.purchase_invoice_grouping_method = 'standard'
    >>> supplier_monthly.purchase_invoice_grouping_period = 'monthly'
    >>> supplier_monthly.save()
    >>> supplier_weekly_break = Party(name='supplier Weekly 0 break')
    >>> supplier_weekly_break.purchase_invoice_grouping_method = 'standard'
    >>> supplier_weekly_break.purchase_invoice_grouping_period = 'weekly-0-break'
    >>> supplier_weekly_break.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')

    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.list_price = Decimal('10')
    >>> template.account_category = account_category
    >>> template.save()
    >>> product, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'product2'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.list_price = Decimal('10')
    >>> template.account_category = account_category
    >>> template.save()
    >>> product2, = template.products


Purchase some products::

    >>> set_user(purchase_user)
    >>> Purchase = Model.get('purchase.purchase')
    >>> purchase = Purchase()
    >>> purchase.party = supplier
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 2.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

Make another purchase::

    >>> purchase, = Purchase.duplicate([purchase])
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

Check the invoices::

    >>> config.user = account_user.id
    >>> Invoice = Model.get('account.invoice')
    >>> invoices = Invoice.find([('party', '=', supplier.id)])
    >>> len(invoices)
    2
    >>> invoice = invoices[0]
    >>> invoice.type
    'in'

Now we'll use the same scenario with the daily supplier::

    >>> set_user(purchase_user)
    >>> purchase = Purchase()
    >>> purchase.party = supplier_daily
    >>> purchase.purchase_date = today
    >>> purchase.invoice_method = 'shipment'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 1.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> Move = Model.get('stock.move')
    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_weekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = today
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')

Make another purchase::

    >>> purchase = Purchase()
    >>> purchase.party = supplier_daily
    >>> purchase.purchase_date = today
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 2.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> Move = Model.get('stock.move')
    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_weekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = today
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')

Make another purchase::

    >>> purchase = Purchase()
    >>> purchase.party = supplier_daily
    >>> purchase.purchase_date = today + relativedelta(day=1)
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 3.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> Move = Model.get('stock.move')
    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_weekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = today
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')

Check the invoices::

    >>> config.user = account_user.id
    >>> invoices = Invoice.find([
    ...     ('party', '=', supplier_daily.id),
    ...     ('start_date', '=', today),
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> len(invoices)
    1
    >>> invoice, = invoices
    >>> invoice.start_date == today
    True
    >>> len(invoice.lines)
    3
    >>> invoice.lines[0].quantity
    1.0
    >>> invoice.lines[1].quantity
    2.0
    >>> invoice.lines[2].quantity
    3.0

Now we'll use the same scenario with the monthly supplier::

    >>> set_user(purchase_user)
    >>> purchase = Purchase()
    >>> purchase.party = supplier_monthly
    >>> purchase.purchase_date = today
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 1.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_weekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = today
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')


Make another Purchase (monthly)::

    >>> purchase = Purchase()
    >>> purchase.party = supplier_monthly
    >>> purchase.invoice_method = 'shipment'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 2.0
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product2
    >>> purchase_line.quantity = 2.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> Move = Model.get('stock.move')
    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_monthly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = past_week
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')
    >>> set_user(purchase_user)
    >>> purchase.reload()


Make another Purchase (monthly)::

    >>> purchase = Purchase()
    >>> purchase.party = supplier_monthly
    >>> purchase.purchase_date = past_month
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 3.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_weekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = past_month
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')

Check the invoices::

    >>> config.user = account_user.id
    >>> invoices = Invoice.find([
    ...     ('party', '=', supplier_monthly.id),
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> len(invoices)
    2
    >>> invoice = invoices[1]
    >>> invoice.start_date == start_month
    True
    >>> len(invoice.lines)
    3
    >>> invoice.lines[0].quantity
    1.0
    >>> invoice.lines[1].quantity
    2.0
    >>> invoice.lines[2].quantity
    2.0


Now we'll use the same scenario with the biweekly supplier::

    >>> set_user(purchase_user)
    >>> purchase = Purchase()
    >>> purchase.party = supplier_biweekly
    >>> purchase.purchase_date = past_month
    >>> purchase.invoice_method = 'shipment'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 1.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_weekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = same_biweekly
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')


Make another purchase (biweekly)::

    >>> purchase = Purchase()
    >>> purchase.party = supplier_biweekly
    >>> purchase.purchase_date = past_month
    >>> purchase.invoice_method = 'shipment'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 2.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_biweekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = same_biweekly
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')


Check the invoices::

    >>> config.user = account_user.id
    >>> invoices = Invoice.find([
    ...     ('party', '=', supplier_biweekly.id),
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> len(invoices)
    1
    >>> invoice, = invoices
    >>> len(invoice.lines)
    2
    >>> invoice.lines[0].quantity
    1.0
    >>> invoice.lines[1].quantity
    2.0

Create a purchase for the next biweekly::

    >>> set_user(purchase_user)
    >>> purchase = Purchase()
    >>> purchase.party = supplier_biweekly
    >>> purchase.purchase_date = same_biweekly
    >>> purchase.invoice_method = 'shipment'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 4.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.state
    'processing'

    >>> shipment = ShipmentIn()
    >>> shipment.supplier = supplier_biweekly
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     shipment.incoming_moves.append(incoming_move)
    >>> shipment.save()
    >>> shipment.effective_date = past_biweekly
    >>> shipment.save()
    >>> shipment.click('receive')
    >>> shipment.click('done')

.. [(x.start_date, x.end_date, past_biweekly, same_biweekly, start_month) for x in invoices]

A new invoice is created::

    >>> config.user = account_user.id
    >>> invoices = Invoice.find([
    ...     ('party', '=', supplier_biweekly.id),
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> len(invoices)
    2

