from odoo import models, fields, api
from odoo.tools.translate import _
from dateutil import relativedelta
from datetime import datetime
from datetime import date
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
import re


class TemperatureLogger(models.Model):
    _name = 'temperature.logger'
    _description = 'Temperature Logger'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', required=False)
    serial_no = fields.Char(string='Serial Number', required=False)
    temperature_logs_ids = fields.One2many(comodel_name='temperature.log', inverse_name='temperature_logger_id', 
                                           string='Temperature_logs_ids', required=False)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
    )
    

class TemperatureLog(models.Model):
    _name = 'temperature.log'
    _description = 'Temperature Logs entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    temperature_logger_id = fields.Many2one(comodel_name='temperature.logger', string='Temperature logger', required=False)
    time = fields.Datetime(string='Time', required=False)
    temperature = fields.Float(string='Temperature°C', digits=(4, 1))
    humidity = fields.Float(string='Humidity', required=False)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
    )


class SampleTemperatureLog(models.Model):
    _name = 'sample.temperature.log'
    _description = 'Temperature Logs entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sample_id = fields.Many2one(comodel_name='sample.sample', string='Sample', required=False)
    time = fields.Datetime(string='Time', required=False)
    temperature = fields.Float(string='Temperature°C', digits=(4, 1))
    humidity = fields.Float(string='Humidity', required=False)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
    )
