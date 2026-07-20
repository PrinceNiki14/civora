from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class AccountMoveRefund(models.Model):
    _inherit = 'account.move'
    _description = "Avoir avec certification FNE"

    # =========================================================================
    # CHAMPS SPÉCIFIQUES AVOIRS FNE (SÉPARÉS DES FACTURES NORMALES)
    # =========================================================================

    fne_refund_certified = fields.Boolean(
        string='Avoir Certifié FNE',
        default=False,
        help="Indique si cet avoir est certifié auprès de la FNE"
    )

    fne_refund_reference = fields.Char(
        string='Référence Avoir FNE',
        readonly=True,
        help="Numéro de référence de l'avoir généré par la FNE"
    )

    fne_refund_token = fields.Char(
        string='Token Avoir FNE',
        readonly=True,
        help="Token de vérification FNE pour l'avoir"
    )

    fne_refund_qr_url = fields.Char(
        string='URL QR Code Avoir',
        readonly=True,
        help="URL du QR code de vérification de l'avoir"
    )

    fne_refund_balance_sticker = fields.Integer(
        string='Balance Stickers Avoir',
        readonly=True,
        help="Nombre de stickers restants après certification avoir"
    )

    fne_refund_warning = fields.Boolean(
        string='Alerte Stock Stickers Avoir',
        default=False,
        help="Alerte sur le stock de stickers pour l'avoir"
    )

    fne_refund_response_data = fields.Json(
        string='Données Réponse Avoir FNE',
        readonly=True,
        help="Réponse complète de l'API FNE pour l'avoir"
    )

    # Champs de relation et calculs
    fne_is_refund_eligible = fields.Boolean(
        string='Éligible Certification Avoir FNE',
        compute='_compute_fne_refund_eligible',
        store=True,
        help="Indique si cet avoir peut être certifié FNE"
    )

    fne_original_invoice_id = fields.Many2one(
        'account.move',
        string='Facture Originale FNE',
        compute='_compute_fne_original_invoice',
        store=True,
        help="Facture originale certifiée FNE"
    )

    fne_original_fne_id = fields.Char(
        string='ID FNE Facture Originale',
        compute='_compute_fne_original_fne_id',
        store=True,
        help="ID de la facture originale dans le système FNE"
    )

    fne_refund_items_count = fields.Integer(
        string='Nombre d\'articles avec ID FNE',
        compute='_compute_fne_refund_items_count',
        help="Nombre d'articles de l'avoir ayant un ID FNE correspondant"
    )

    # =========================================================================
    # MÉTHODES COMPUTED - ADAPTÉES ODOO 17
    # =========================================================================

    @api.depends('move_type', 'reversed_entry_id')
    def _compute_fne_refund_eligible(self):
        """Déterminer si l'avoir est éligible à la certification FNE"""
        for record in self:
            if record.move_type != 'out_refund':
                record.fne_is_refund_eligible = False
                continue

            # Chercher la facture originale
            original_invoice = None
            if hasattr(record, 'reversed_entry_id') and record.reversed_entry_id:
                original_invoice = record.reversed_entry_id

            # Vérifier si la facture originale est certifiée FNE
            original_certified = bool(
                original_invoice and
                hasattr(original_invoice, 'fne_certified') and
                original_invoice.fne_certified
            )

            record.fne_is_refund_eligible = original_certified

    @api.depends('reversed_entry_id')
    def _compute_fne_original_invoice(self):
        """Récupérer la facture originale"""
        for record in self:
            if (hasattr(record, 'reversed_entry_id') and
                    record.reversed_entry_id and
                    record.move_type == 'out_refund'):
                record.fne_original_invoice_id = record.reversed_entry_id
            else:
                record.fne_original_invoice_id = False

    @api.depends('fne_original_invoice_id', 'fne_original_invoice_id.fne_response_data')
    def _compute_fne_original_fne_id(self):
        """Récupérer l'ID FNE de la facture originale"""
        for record in self:
            if (record.fne_original_invoice_id and
                    hasattr(record.fne_original_invoice_id, 'fne_response_data') and
                    record.fne_original_invoice_id.fne_response_data):

                invoice_data = record.fne_original_invoice_id.fne_response_data.get('invoice', {})
                record.fne_original_fne_id = invoice_data.get('id', '')
            else:
                record.fne_original_fne_id = ''

    @api.depends('invoice_line_ids', 'fne_original_invoice_id')
    def _compute_fne_refund_items_count(self):
        """Compter les articles avec ID FNE correspondant"""
        for record in self:
            count = 0
            if record.fne_original_invoice_id and record.move_type == 'out_refund':
                for refund_line in record.invoice_line_ids.filtered(
                        lambda l: l.display_type not in ('line_section', 'line_note')
                ):
                    original_line = record._find_original_line_for_refund(
                        refund_line, record.fne_original_invoice_id
                    )
                    if original_line and hasattr(original_line, 'fne_item_id') and original_line.fne_item_id:
                        count += 1

            record.fne_refund_items_count = count

    # =========================================================================
    # MÉTHODES PRINCIPALES
    # =========================================================================

    def action_certify_fne_refund(self):
        """Certifier l'avoir auprès de la FNE"""
        self.ensure_one()

        _logger.info(f"=== DÉBUT CERTIFICATION AVOIR {self.name} ===")
        _logger.info(f"Type: {self.move_type}")
        _logger.info(f"État: {self.state}")
        _logger.info(f"Éligible: {self.fne_is_refund_eligible}")
        _logger.info(f"Déjà certifié (avoir): {self.fne_refund_certified}")
        _logger.info(f"Déjà certifié (général): {getattr(self, 'fne_certified', False)}")

        # Vérifications préalables
        self._check_fne_refund_prerequisites()

        try:
            # Préparation des données
            refund_data = self._prepare_fne_refund_data()

            # Appel API
            response = self._call_fne_refund_api(refund_data)

            # Traitement de la réponse
            self._process_fne_refund_response(response)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Certification Avoir FNE',
                    'message': f'Avoir certifié avec succès!\nRéférence FNE: {self.fne_refund_reference}',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Erreur certification avoir FNE {self.name}: {str(e)}")
            raise UserError(f"Erreur lors de la certification de l'avoir FNE:\n{str(e)}")

    def _check_fne_refund_prerequisites(self):
        """Vérifications avant certification"""
        _logger.info(f"=== VÉRIFICATIONS PRÉREQUIS AVOIR {self.name} ===")

        if self.move_type != 'out_refund':
            raise UserError("Seuls les avoirs peuvent être certifiés avec cette méthode.")

        if not self.fne_is_refund_eligible:
            raise UserError(
                "Cet avoir n'est pas éligible à la certification FNE.\n"
                "Vérifiez qu'il s'agit bien d'un avoir lié à une facture certifiée FNE."
            )

        if self.state != 'posted':
            raise UserError("L'avoir doit être validé avant certification.")

        if self.fne_refund_certified:
            raise UserError("Cet avoir est déjà certifié auprès de la FNE.")

        if not self.fne_original_fne_id:
            raise UserError("Impossible de récupérer l'ID FNE de la facture originale.")

        if self.fne_refund_items_count == 0:
            raise UserError(
                "Aucun article de cet avoir ne correspond aux articles de la facture originale certifiée FNE."
            )

        _logger.info("✅ Toutes les vérifications sont OK")

    def _prepare_fne_refund_data(self):
        """Préparer les données pour l'API FNE"""
        items = []

        for refund_line in self.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note') and l.quantity != 0
        ):
            # Trouver la ligne correspondante dans la facture originale
            original_line = self._find_original_line_for_refund(
                refund_line, self.fne_original_invoice_id
            )

            if original_line and hasattr(original_line, 'fne_item_id') and original_line.fne_item_id:
                items.append({
                    "id": original_line.fne_item_id,
                    "quantity": abs(float(refund_line.quantity))  # Quantité positive
                })

                _logger.info(
                    f"Article avoir ajouté: {refund_line.name} "
                    f"(ID FNE: {original_line.fne_item_id}, Qté: {abs(refund_line.quantity)})"
                )
            else:
                _logger.warning(
                    f"Ligne avoir ignorée (pas d'ID FNE): {refund_line.name}"
                )

        if not items:
            raise UserError("Aucun article avec ID FNE trouvé pour cet avoir.")

        _logger.info(f"Données avoir préparées: {len(items)} articles")
        return {"items": items}

    def _find_original_line_for_refund(self, refund_line, original_invoice):
        """Trouver la ligne originale correspondant à une ligne d'avoir"""

        if not original_invoice:
            return None

        # Méthode 1: Correspondance par produit (plus fiable)
        if refund_line.product_id:
            for orig_line in original_invoice.invoice_line_ids:
                if (orig_line.product_id == refund_line.product_id and
                        hasattr(orig_line, 'fne_item_id') and orig_line.fne_item_id):
                    return orig_line

        # Méthode 2: Correspondance par nom/description
        for orig_line in original_invoice.invoice_line_ids:
            if (orig_line.name == refund_line.name and
                    hasattr(orig_line, 'fne_item_id') and orig_line.fne_item_id):
                return orig_line

        return None

    def _call_fne_refund_api(self, data):
        """Appel à l'API de certification d'avoir FNE"""
        company_id = self.company_id.id

        # Récupération des paramètres
        base_url = self.env['ir.config_parameter'].sudo().get_param('fne.base_url', 'http://54.247.95.108/ws')
        api_key = self.env['ir.config_parameter'].sudo().get_param(f'fne.api_key.{company_id}')

        if not api_key:
            raise UserError(
                f"Clé API FNE non configurée pour la société {self.company_id.name}.\n"
                f"Veuillez configurer les paramètres FNE dans:\n"
                f"Paramètres → FNE - Facture Normalisée Électronique"
            )

        # Construction de l'URL avec l'ID de la facture originale
        url = f"{base_url}/external/invoices/{self.fne_original_fne_id}/refund"

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        _logger.info(
            f"Appel API avoir FNE pour {self.name}:\n"
            f"URL: {url}\n"
            f"Données: {json.dumps(data, indent=2)}"
        )

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code not in [200, 201]:
            error_msg = f"Erreur API FNE (Code {response.status_code})"
            try:
                error_data = response.json()
                error_msg += f":\n{error_data.get('message', 'Erreur inconnue')}"
                if 'errors' in error_data:
                    error_msg += f"\nDétails: {error_data['errors']}"
            except:
                error_msg += f":\n{response.text}"

            raise UserError(error_msg)

        return response.json()

    def _process_fne_refund_response(self, response):
        """Traiter la réponse de l'API - CHAMPS SPÉCIFIQUES AVOIRS"""

        self.write({
            'fne_refund_certified': True,
            'fne_refund_reference': response.get('reference'),
            'fne_refund_token': response.get('token'),
            'fne_refund_qr_url': response.get('token'),
            'fne_refund_balance_sticker': response.get('balance_sticker', 0),
            'fne_refund_warning': response.get('warning', False),
            'fne_refund_response_data': response
        })

        _logger.info(
            f"Avoir {self.name} certifié FNE avec succès.\n"
            f"Référence: {self.fne_refund_reference}"
        )

    # =========================================================================
    # ACTIONS UTILISATEUR
    # =========================================================================

    def action_download_fne_refund_pdf(self):
        """Télécharger la facture d'avoir certifiée FNE"""
        if self.fne_refund_qr_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.fne_refund_qr_url,
                'target': 'new',
            }
        else:
            raise UserError("Aucune URL de téléchargement FNE disponible pour cet avoir.")

    def action_view_fne_refund_qr_code(self):
        """Afficher le QR code de vérification de l'avoir"""
        if not self.fne_refund_qr_url:
            raise UserError("Aucun QR code disponible pour cet avoir.")

        return {
            'type': 'ir.actions.act_url',
            'url': self.fne_refund_qr_url,
            'target': 'new',
        }

    # =========================================================================
    # MÉTHODES DE DEBUG
    # =========================================================================

    def debug_fne_refund_status(self):
        """Debug du statut de l'avoir"""
        _logger.info(f"=== DEBUG STATUT AVOIR {self.name} ===")
        _logger.info(f"Type: {self.move_type}")
        _logger.info(f"État: {self.state}")
        _logger.info(f"Éligible FNE: {self.fne_is_refund_eligible}")
        _logger.info(f"Certifié avoir FNE: {self.fne_refund_certified}")
        _logger.info(f"Certifié général: {getattr(self, 'fne_certified', 'N/A')}")
        _logger.info(
            f"Facture originale: {self.fne_original_invoice_id.name if self.fne_original_invoice_id else 'Aucune'}")
        _logger.info(f"ID FNE original: {self.fne_original_fne_id}")
        _logger.info(f"Articles avec ID FNE: {self.fne_refund_items_count}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Debug Avoir FNE',
                'message': f'Infos debug affichées dans les logs.\nÉligible: {self.fne_is_refund_eligible}\nCertifié: {self.fne_refund_certified}',
                'type': 'info',
            }
        }
