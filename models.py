from odoo import tools, models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def write(self, vals):
        res = super(AccountPayment, self).write(vals)
        if 'state' in vals:
            for rec in self:
                if rec.order_id:
                    order_id = rec.order_id
                    order_id.payment_status = rec.state
        return res

    order_id = fields.Many2one('sale.order',string='Pedido de Venta')

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def confirm_payments(self):
        for rec in self.filtered(lambda o: o.state in ['draft','sent']):
            for payment in rec.payment_ids:
                if payment.payment_id:
                    continue
                percent = payment.percent
                amount = rec.amount_total * percent / 100
                payment_method = self.env['account.payment.method'].search([('code','=','manual'),('payment_type','=','inbound')])
                if not payment_method:
                    raise ValidationError('Metodo de pago inexistente')
                vals_payment = {
                        'partner_id': rec.partner_id.id,
                        'journal_id': payment.journal_id.id,
                        'payment_type': 'inbound',
                        'amount': amount,
                        'partner_type': 'customer',
                        'payment_date': rec.date_order,
                        'communication': '%s %s'%(rec.name,payment.journal_id.display_name),
                        'order_id': rec.id,
                        'payment_method_id': payment_method.id,
                        }
                payment_id = self.env['account.payment'].create(vals_payment)
                payment_id.post()
                payment.payment_id = payment_id.id

    payment_ids = fields.One2many('sale.order.payment',inverse_name='order_id',string='Pagos',copy=False)
    payment_status = fields.Char('Estado Pagos',copy=False) 

class SaleOrderPayment(models.Model):
    _name = 'sale.order.payment'
    _description = 'sale.order.payment'

    def _default_percent(self):
        res = 100
        order_id = 0
        if self.env.context.get('params'):
            if self.env.context.get('params').get('id'):
                order_id = self.env.context.get('params').get('id')
        order = self.env['sale.order'].browse(order_id)
        for payment in order.payment_ids:
            res = res - payment.percent
        return res

    order_id = fields.Many2one('sale.order',string='Pedido de venta')
    journal_id = fields.Many2one('account.journal',string='Medio de pago/cuotas',domain=[('type','in',['bank','cash'])])
    ref = fields.Char('Referencia')
    percent = fields.Float('Porcentaje',default=_default_percent)
    payment_id = fields.Many2one('account.payment',string='Pago')
