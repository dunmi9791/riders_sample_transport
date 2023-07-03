# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import math


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


class OdooAcademy(http.Controller):

    @http.route('/riders/samples/', auth='public', website=True)
    def display_samples(self, sortby=None, page=1, **kw):
        items_per_page = 20  # Number of samples per page
        searchbar_sortings = {
            'name': {'label': _('Sample'), 'order': 'sample_no desc'},
            'date': {'label': _('Sample Date'), 'order': 'pickup_date desc'},
        }
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']
        print(order)
        current_page = int(page)
        offset = (int(page) - 1) * items_per_page
        samples = http.request.env['sample.sample'].search([('state', 'in', ('pending', 'awaiting_pickup', 'in_progress', 'delivered'))], order=order, offset=offset, limit=items_per_page)
        total_samples = http.request.env['sample.sample'].search_count(
            [('state', 'in', ('pending', 'awaiting_pickup', 'in_progress', 'delivered'))])
        # Calculate total pages needed
        total_pages = int(math.ceil(total_samples / items_per_page))
        # updated_samples = []
        # for sample in samples:
        #     progress_percentage = self.get_progress_percentage(sample.state)
        #     updated_sample = {
        #         'sample': sample,
        #         'progress_percentage': progress_percentage,
        #     }
        #     updated_samples.append(updated_sample)

        return http.request.render('riders_sample_transport.portal_riders_samples', {
            'samples': samples,
            'page_name': 'sample',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'current_page': current_page,
            'total_pages': total_pages
        })



    @http.route('/riders/<model("sample.sample"):sample>/', auth='public', website=True, type='http')
    def display_sample_detail(self, sample):
        progress_percentage = self.get_progress_percentage(sample.state)
        sample.progress_percentage = progress_percentage
        return http.request.render('riders_sample_transport.sample_detail', {'sample': sample, 'page_name': 'sample'})

    def get_progress_percentage(self, state):
        if state == 'awaiting_pickup':
            return 10
        elif state == 'in_progress':
            return 50
        elif state == 'delivered':
            return 99
        # Add more conditions for other states if needed
        else:
            return 0



class RidersCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(RidersCustomerPortal, self)._prepare_home_portal_values(counters)
        values['count_samples'] = request.env['sample.sample'].search_count([('state', 'in', ('pending', 'awaiting_pickup',
                                                                                         'in_progress', 'delivered'))])

        return values
