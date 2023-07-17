from odoo import models, fields, api
from odoo.tools.translate import _
from dateutil import relativedelta
from datetime import datetime
from datetime import date
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
import re
from odoo.exceptions import UserError


class Sample(models.Model):
    _name = 'sample.sample'
    _description = 'Sample'
    _rec_name = 'sample_no'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    patient_id = fields.Many2one('patient.rider', string='Patient', required=False, track_visibility='onchange')
    case_number = fields.Char(string='Case Number/Patient', required=False, track_visibility='onchange')
    facility_sending_id = fields.Many2one('facility.rider', string='Sending Facility', required=False, track_visibility='onchange')
    facility_receiving_id = fields.Many2one('facility.rider', string='Destination Facility', required=True, track_visibility='onchange')
    third_party_agent_id = fields.Many2one('res.partner', string='Assigned Riders', track_visibility='onchange', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('awaiting_pickup', 'Awaiting Pickup'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
    ], string='Status', default='pending', required=True, track_visibility='onchange')
    result_status = fields.Selection([
        ('sample_undelivered', 'Pending Sample Delivery'),
        ('awaiting_result', 'Awaiting Result'),
        ('in_progress', 'Result Delivery In Progress'),
        ('delivered', 'Result Delivered'),
    ], string='Result Status', default='sample_undelivered', required=True, track_visibility='onchange')
    schedule_pickup_date = fields.Datetime(string='scheduled Date', track_visibility='onchange')
    temp_logger = fields.Many2one('temperature.logger', string='Temperature Logger', track_visibility='onchange')
    pickup_date = fields.Datetime(string='Pickup Date', track_visibility='onchange')
    delivery_date = fields.Datetime(string='Delivery Date', track_visibility='onchange')
    turnaround_time = fields.Float(string='Turnaround Time(in Seconds)', track_visibility='onchange', compute='_compute_turnaround_time')
    barcode = fields.Char(string='Barcode', required=False, track_visibility='onchange')
    sample_no = fields.Char(string="Sample Number", default=lambda self: _('New'),
                          requires=False, readonly=True, trace_visibility='onchange', )
    days = fields.Integer(string='Days', compute='_compute_days_hours_mins')
    hours = fields.Integer(string='Hours', compute='_compute_days_hours_mins')
    minutes = fields.Integer(string='Minutes', compute='_compute_days_hours_mins')
    test_type = fields.Selection(
        string='Test type',
        selection=[('es', 'ES'),
                   ('afp', 'AFP'), ],
        required=False, )

    specimen_type = fields.Selection(
        string='Specimen type',
        selection=[('blood', 'Blood sample'),
                   ('urine', 'Urine sample'),
                   ('fecal', 'Fecal sample'),
                   ('saliva', 'Saliva sample'),
                   ('stool', 'Stool sample'),
                   ('sputum', 'Sputum sample'),
                   ('water', 'Water sample'),
                   ('soil', 'Soil sample'),
                   ('tissue', 'Tissue sample'), ],
        required=False, )

    location = fields.Many2one(
        comodel_name='sample.location',
        string='Pick up / Sending Location',
        required=True)

    sample_temperature_ids = fields.One2many(
        comodel_name='sample.temperature.log',
        inverse_name='sample_id',
        string='Sample temperature logs',
        required=False)
    logs_get = fields.Boolean(string='Logs_get', required=False)
    company_id = fields.Many2one(
        'res.company',
        string='State',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
    )
    progress_percentage = fields.Integer(string='Progress Percentage', required=False)

    def get_temperature_logs(self):
        # Assuming you're running this method on a single record.
        if not self.temp_logger:
            raise UserError("No temperature logger found for this sample.")

        domain = [
            ('temperature_logger_id', '=', self.temp_logger.id),
            ('time', '>=', self.pickup_date),
            ('time', '<=', self.delivery_date),
        ]

        temperature_logs = self.env['temperature.log'].search(domain)
        if not temperature_logs:
            raise UserError("No temperature logs found for the specified time range.")
        # sample_logs = []
        for line in temperature_logs:
            vals = {
                'sample_id': self.id,
                'time': line.time,
                'temperature': line.temperature,
                'humidity': line.humidity,
            }
            # sample_logs.append(vals)
            self.env['sample.temperature.log'].create(vals)
        self.logs_get = True

    @api.multi
    def schedule_pickup(self):
        self.write({
            'state': 'awaiting_pickup',
            'schedule_pickup_date': fields.Datetime.now(),
        })

    @api.multi
    def mark_pickup(self):
        self.write({
            'state': 'in_progress',
            'pickup_date': fields.Datetime.now(),
        })

    @api.multi
    def assign_third_party_agent(self, third_party_agent_id):
        self.write({
            'third_party_agent_id': third_party_agent_id,
        })

    @api.multi
    def mark_delivered(self):
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Datetime.now(),
            'result_status': 'awaiting_result',
        })

    @api.depends('delivery_date', 'pickup_date')
    def _compute_turnaround_time(self):
        for rec in self:
            if rec.delivery_date and rec.pickup_date:
                rec.turnaround_time = (rec.delivery_date - rec.pickup_date).total_seconds()
            else:
                rec.turnaround_time = 0

    @api.depends('turnaround_time')
    def _compute_days_hours_mins(self):
        for rec in self:
            if rec.turnaround_time:
                minutes, seconds = divmod(rec.turnaround_time, 60)
                hours, minutes = divmod(minutes, 60)
                days, hours = divmod(hours, 24)
                rec.days = days
                rec.hours = hours
                rec.minutes = minutes

    @api.model
    def create(self, vals):
        record = super(Sample, self).create(vals)
        record.add_user_as_follower()
        return record

    def write(self, vals):
        result = super(Sample, self).write(vals)
        self.add_user_as_follower()
        return result

    def add_user_as_follower(self):
        for record in self:
            user = record.third_party_agent_id
            if user:
                record.message_subscribe(partner_ids=[user.id])

    def unlink(self):
        # self is a recordset
        for sample in self:
            if sample.state == 'in_progress':
                raise UserError("You can not delete Samples in progress")
            if sample.state == 'delivered':
                raise UserError("You can not delete Delivered Samples")

        return super(Sample, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('sample_no', _('New')) == _('New'):
            vals['sample_no'] = self.env['ir.sequence'].next_by_code('increment_sample') or _('New')
        result = super(Sample, self).create(vals)
        return result

    @api.depends('sample_temperature_ids.temperature')
    def _compute_temperature_stats(self):
        for sample in self:
            temperatures = sample.sample_temperature_ids.mapped('temperature')
            if temperatures:
                sample.avg_temperature = sum(temperatures) / len(temperatures)
                sample.min_temperature = min(temperatures)
                sample.max_temperature = max(temperatures)
                sample.median_temperature = sorted(temperatures)[len(temperatures) // 2]
            else:
                sample.avg_temperature = 0.0
                sample.min_temperature = 0.0
                sample.max_temperature = 0.0
                sample.median_temperature = 0.0

    avg_temperature = fields.Float(compute='_compute_temperature_stats', string='Average Temperature')
    min_temperature = fields.Float(compute='_compute_temperature_stats', string='Lowest Temperature')
    max_temperature = fields.Float(compute='_compute_temperature_stats', string='Highest Temperature')
    median_temperature = fields.Float(compute='_compute_temperature_stats', string='Median Temperature')


class Patient(models.Model):
    _name = 'patient.rider'
    _description = 'Patient'

    age = fields.Integer(string='Age')
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Sex')
    facility_id = fields.Many2one('facility.rider', string='Patient Facility', required=True, track_visibility='onchange')
    patient_no = fields.Char(string="Patient Number", default=lambda self: _('New'),
                                    requires=False, readonly=True, trace_visibility='onchange', )
    sample_ids = fields.One2many('sample.sample', 'patient_id', string='Samples')
    name = fields.Char(string='Name', required=False)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
    )

    def _get_facility_sequence(self, facility_id):
        facility_sequence = self.env['facility.patient.sequence'].search([('facility_id', '=', facility_id)], limit=1)
        if not facility_sequence:
            facility_name = self.env['facility.rider'].browse(facility_id).name
            sequence_data = {
                'name': "Patient Rider - {}".format(facility_name),
                'code': "patient.rider.{}".format(facility_id),
                'implementation': 'standard',
                'padding': 4,
                'prefix': "{}/%(year)s/".format(facility_name),
                'suffix': '',
            }
            sequence_id = self.env['ir.sequence'].create(sequence_data)
            facility_sequence = self.env['facility.patient.sequence'].create({
                'facility_id': facility_id,
                'sequence_id': sequence_id.id,
            })
        return facility_sequence.sequence_id

    @api.model
    def create(self, vals):
        if 'facility_id' in vals:
            sequence = self._get_facility_sequence(vals['facility_id'])
            vals['patient_no'] = sequence.next_by_id()
        # if vals.get('patient_no', _('New')) == _('New'):
        #     vals['patient_no'] = self.env['ir.sequence'].next_by_code('increment_patient') or _('New')
        result = super(Patient, self).create(vals)
        return result


class Facility(models.Model):
    _name = 'facility.rider'
    _description = 'Facilities'

    facility_type = fields.Selection([
        ('sending', 'Sending Facility'),
        ('receiving', 'Receiving Facility'),
    ], string='Facility Type')
    name = fields.Char(string='Name', required=False)
    sample_ids = fields.One2many('sample.sample', 'facility_sending_id', string='Sent Samples')
    patients_ids = fields.One2many('patient.rider', 'facility_id', string='Patients')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
    )


class FacilityPatientSequence(models.Model):
    _name = 'facility.patient.sequence'
    _description = 'Facility Patient Sequence'

    facility_id = fields.Many2one('facility.rider', string='Facility', required=True, ondelete='cascade')
    sequence_id = fields.Many2one('ir.sequence', string='Sequence', required=True, ondelete='cascade')


class SampleLocation(models.Model):
    _name = 'sample.location'
    _description = 'Sample Location'

    name = fields.Char(string='Site Name')
    latitude = fields.Float('Latitude', digits=(9, 6))
    longitude = fields.Float('Longitude', digits=(9, 6))
    altitude = fields.Float('Altitude', digits=(9, 2))
    street = fields.Char('Street')
    state_id = fields.Many2one('res.country.state', 'State')
    lga = fields.Char(string='LGA')
    status = fields.Char(string='Status')
    epid_no = fields.Char(string='Epid Number')
    postal_code = fields.Char('Postal Code')
    zone = fields.Selection(
        string='Zone',
        selection=[('nez', 'NEZ'),
                   ('ssz', 'SSZ'),
                   ('nwz', 'NWZ'),
                   ('ncz', 'NCZ'),
                   ('swz', 'SWZ'),
                   ('sez', 'SEZ'), ],
        required=False, )

    nearest_landmark = fields.Char(string='Nearest landmark', required=False)
    type_location = fields.Selection(
        string='Type of location',
        selection=[('urban', 'Urban'),
                   ('rural', 'rural'), ],
        required=False, )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        help='Select the company for this record',
        store=True,
        index=True,
    )



