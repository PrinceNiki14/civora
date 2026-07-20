from odoo import models


class QRCodePaymentWizard(models.TransientModel):
    _inherit = 'qr.code.payment.wizard'

    @staticmethod
    def _be_company_vat_communication(company):
        ''' Taken from https://finances.belgium.be/fr/communication-structuree
        '''
        vat = (company.vat or '').replace("BE", "")
        communication = ''
        if len(vat) == 10:
            number = int(vat)
            suffix = f"{number % 97 or 97:02}"
            communication = f"+++{vat[:3]}/{vat[3:7]}/{vat[7:]}{suffix}+++"
        return communication
