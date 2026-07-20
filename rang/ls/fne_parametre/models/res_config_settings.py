from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuration FNE'

    # Champs de configuration FNE
    fne_base_url = fields.Char(
        string='URL de base FNE',
        config_parameter='fne.base_url',
        default='http://54.247.95.108/ws',
        help="URL de base de l'API FNE (test ou production)"
    )

    fne_api_key = fields.Char(
        string='Clé API FNE',
        help="Clé d'authentification pour l'API FNE"
    )

    fne_default_establishment = fields.Char(
        string='Établissement par défaut',
        help="Nom de l'établissement par défaut"
    )

    fne_default_point_of_sale = fields.Char(
        string='Point de vente par défaut',
        help="Point de vente par défaut"
    )

    fne_default_commercial_message = fields.Text(
        string='Message commercial par défaut',
        help="Message commercial par défaut pour toutes les factures"
    )

    fne_default_footer_message = fields.Text(
        string='Message pied de page par défaut',
        help="Message de pied de page par défaut pour toutes les factures"
    )

    fne_default_seller_name = fields.Char(
        string='Nom vendeur par défaut',
        help="Nom du vendeur par défaut"
    )

    @api.model
    def get_values(self):
        """Récupération des valeurs de configuration"""
        res = super(ResConfigSettings, self).get_values()

        try:
            company_id = self.env.company.id

            # Récupération des paramètres spécifiques à la société
            res.update({
                'fne_api_key': self.env['ir.config_parameter'].sudo().get_param(
                    f'fne.api_key.{company_id}', ''
                ),
                'fne_default_establishment': self.env['ir.config_parameter'].sudo().get_param(
                    f'fne.default_establishment.{company_id}', ''
                ),
                'fne_default_point_of_sale': self.env['ir.config_parameter'].sudo().get_param(
                    f'fne.default_point_of_sale.{company_id}', ''
                ),
                'fne_default_commercial_message': self.env['ir.config_parameter'].sudo().get_param(
                    f'fne.default_commercial_message.{company_id}', ''
                ),
                'fne_default_footer_message': self.env['ir.config_parameter'].sudo().get_param(
                    f'fne.default_footer_message.{company_id}', ''
                ),
                'fne_default_seller_name': self.env['ir.config_parameter'].sudo().get_param(
                    f'fne.default_seller_name.{company_id}', ''
                ),
            })
        except Exception as e:
            _logger.error(f"Erreur lors de la récupération des paramètres FNE: {str(e)}")

        return res

    def set_values(self):
        """Sauvegarde des valeurs de configuration"""
        super(ResConfigSettings, self).set_values()

        try:
            company_id = self.env.company.id

            # Sauvegarde des paramètres spécifiques à la société
            self.env['ir.config_parameter'].sudo().set_param(
                f'fne.api_key.{company_id}', self.fne_api_key or ''
            )
            self.env['ir.config_parameter'].sudo().set_param(
                f'fne.default_establishment.{company_id}', self.fne_default_establishment or ''
            )
            self.env['ir.config_parameter'].sudo().set_param(
                f'fne.default_point_of_sale.{company_id}', self.fne_default_point_of_sale or ''
            )
            self.env['ir.config_parameter'].sudo().set_param(
                f'fne.default_commercial_message.{company_id}', self.fne_default_commercial_message or ''
            )
            self.env['ir.config_parameter'].sudo().set_param(
                f'fne.default_footer_message.{company_id}', self.fne_default_footer_message or ''
            )
            self.env['ir.config_parameter'].sudo().set_param(
                f'fne.default_seller_name.{company_id}', self.fne_default_seller_name or ''
            )

            _logger.info(f"Paramètres FNE sauvegardés pour la société {company_id}")

        except Exception as e:
            _logger.error(f"Erreur lors de la sauvegarde des paramètres FNE: {str(e)}")
            raise
