# -*- coding: utf-8 -*-
# from odoo import http


# class HrPayslipCustom(http.Controller):
#     @http.route('/hr_payslip_custom/hr_payslip_custom', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_payslip_custom/hr_payslip_custom/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_payslip_custom.listing', {
#             'root': '/hr_payslip_custom/hr_payslip_custom',
#             'objects': http.request.env['hr_payslip_custom.hr_payslip_custom'].search([]),
#         })

#     @http.route('/hr_payslip_custom/hr_payslip_custom/objects/<model("hr_payslip_custom.hr_payslip_custom"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_payslip_custom.object', {
#             'object': obj
#         })

