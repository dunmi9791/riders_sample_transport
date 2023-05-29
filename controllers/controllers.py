# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class MarkPickup(http.Controller):

    @http.route('/pickup/<int:record_id>', type='json', auth='user')
    def pick_up(self, record_id, **kwargs):
        # Fetch the record
        record = request.env['sample.sample'].sudo().browse(record_id)

        # Call the pick_up method
        result = record.mark_pickup()

        # Return a response
        return "State changed to: %s" % record.state


class MarkDelivered(http.Controller):

    @http.route('/deliver/<int:record_id>', type='json', auth='user')
    def deliver(self, record_id, **kwargs):
        # Fetch the record
        record = request.env['sample.sample'].sudo().browse(record_id)

        # Call the pick_up method
        result = record.mark_delivered()

        # Return a response
        return "State changed to: %s" % record.state


class GetSamples(http.Controller):
    @http.route('/assigned_samples', type='json', auth='user')
    def get_my_samples(self, **kwargs):
        # Get the current user
        user_id = request.uid
        user = request.env['res.users'].browse(user_id)
        partner = user.partner_id

        # Get the records linked to the current user and in the specified states
        records = request.env['sample.sample'].sudo().search([
            ('third_party_agent_id', '=', partner.id),
        ])

        # Format the results into list of dictionaries
        results = [{'ID': record.id, 'State': record.state, 'No': record.sample_no} for record in records]

        # Return the results
        return results


class MobileApiTestTypes(http.Controller):
    @http.route('/loggers/', website=True, type='json', auth='public')
    def loggers(self):
        # return "List of all Samples"
        loggers_list = []
        loggers_all = request.env['temperature.logger'].search([])
        for rec in loggers_all:
            vals = {
                'id': rec.id,
                'name': rec.name,

            }
            loggers_list.append(vals)

        data = {'status': 200, 'response': loggers_list, 'message': 'Loggers Returned'}
        return data
