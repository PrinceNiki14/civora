from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging
from odoo.modules import get_module_resource
import base64

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = "Facture avec certification FNE"

    # =========================================================================
    # CHAMPS FNE
    # =========================================================================

    fne_certified_icon = fields.Html(
        string="Certification",
        compute='_compute_fne_certified_icon',
        store=False
    )

    fne_certified = fields.Boolean(
        string='Certifié FNE',
        default=False,
        help="Indique si la facture est certifiée auprès de la FNE"
    )
    fne_reference = fields.Char(
        string='Référence FNE',
        readonly=True,
        help="Numéro de référence généré par la FNE"
    )
    fne_token = fields.Char(
        string='Token FNE',
        readonly=True,
        help="Token de vérification FNE (pour QR code)"
    )
    fne_qr_url = fields.Char(
        string='URL QR Code',
        readonly=True,
        help="URL du QR code de vérification"
    )
    fne_balance_sticker = fields.Integer(
        string='Balance Stickers',
        readonly=True,
        help="Nombre de stickers restants"
    )
    fne_warning = fields.Boolean(
        string='Alerte Stock Stickers',
        default=False,
        help="Alerte sur le stock de stickers"
    )

    fne_template = fields.Selection([
        ('B2B', 'Business to Business - Client entreprise avec NCC'),
        ('B2C', 'Business to Consumer - Client particulier'),
        ('B2G', 'Business to Government - Client gouvernemental'),
        ('B2F', 'Business to Foreign - Client international')
    ], string='Template FNE', default='B2C', required=True)

    fne_client_ncc = fields.Char(
        string='NCC Client',
        help="Numéro de Compte Contribuable du client (obligatoire pour B2B)"
    )
    
    fne_point_of_sale = fields.Char(
        string='Point de Vente',
        help="Identifiant du point de vente"
    )

    fne_establishment = fields.Char(
        string='Établissement',
        help="Nom de l'établissement"
    )

    fne_seller_name = fields.Char(
        string='Nom Vendeur',
        help="Nom du vendeur/commercial"
    )

    fne_commercial_message = fields.Text(
        string='Message Commercial',
        help="Message commercial à afficher"
    )

    fne_footer_message = fields.Text(
        string='Message Pied de Page',
        help="Message personnel en pied de facture"
    )

    fne_is_rne = fields.Boolean(
        string='Lié à un Reçu',
        default=False,
        help="Indique si la facture est liée à un reçu"
    )
    fne_rne_number = fields.Char(
        string='Numéro RNE',
        help="Numéro du reçu (obligatoire si lié à un reçu)"
    )

    fne_response_data = fields.Json(
        string='Données Réponse FNE',
        readonly=True,
        help="Réponse complète de l'API FNE"
    )

    fne_payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('check', 'Chèque'),
        ('mobile-money', 'Mobile Money'),
        ('transfer', 'Virement bancaire'),
        ('deferred', 'À terme')
    ], string='Mode de Paiement FNE', default='cash')

    fne_qr_code_image = fields.Binary(
        string='QR Code Image',
        readonly=True,
        help="Image du QR code de vérification FNE"
    )

    fne_qr_code_data = fields.Text(
        string='QR Code Data',
        readonly=True,
        help="Données encodées dans le QR code (base64)"
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================

    @api.depends('fne_certified')
    def _compute_fne_certified_icon(self):
        """Calculer l'icône de certification FNE avec logo personnalisé"""
        for record in self:
            if record.fne_certified:
                record.fne_certified_icon = '''
                    <img src="/fne_sale_invoice_certification/static/description/icon.jpg" 
                         style="width: 55px; height: 55px;" 
                         title="Certifié FNE"/>
                '''
            else:
                record.fne_certified_icon = ''

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================

    @api.onchange('fne_template', 'partner_id')
    def _onchange_fne_template_b2b(self):
        """Auto-remplir le NCC quand template B2B est sélectionné"""
        if self.fne_template == 'B2B' and self.partner_id:
            if hasattr(self.partner_id, 'ncc') and self.partner_id.ncc:
                self.fne_client_ncc = self.partner_id.ncc
            else:
                return {
                    'warning': {
                        'title': 'Attention',
                        'message': 'Le NCC n\'est pas renseigné pour ce contact.'
                    }
                }

    @api.onchange('company_id')
    def _onchange_company_load_fne_defaults(self):
        """Charger les valeurs par défaut FNE quand la société change"""
        if self.company_id:
            self._load_fne_defaults()

    # =========================================================================
    # CREATE / WRITE METHODS
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Charger les valeurs par défaut FNE à la création"""
        records = super().create(vals_list)
        for record in records:
            if record.move_type == 'out_invoice':
                record._load_fne_defaults()
        return records

    def write(self, vals):
        """Recharger les valeurs par défaut si la société change"""
        result = super().write(vals)
        if 'company_id' in vals:
            for record in self:
                if record.move_type == 'out_invoice':
                    record._load_fne_defaults()
        return result

    # =========================================================================
    # HELPER METHODS FOR CONFIG
    # =========================================================================

    def _load_fne_defaults(self):
        """Charger les valeurs par défaut depuis les paramètres FNE"""
        self.ensure_one()
        
        if not self.company_id:
            return
            
        company_id = self.company_id.id
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Charger uniquement si les champs sont vides
        if not self.fne_point_of_sale:
            self.fne_point_of_sale = ICP.get_param(f'fne.default_point_of_sale.{company_id}', '')
        
        if not self.fne_establishment:
            self.fne_establishment = ICP.get_param(f'fne.default_establishment.{company_id}', '')
        
        if not self.fne_seller_name:
            self.fne_seller_name = ICP.get_param(f'fne.default_seller_name.{company_id}', '')
        
        if not self.fne_commercial_message:
            self.fne_commercial_message = ICP.get_param(f'fne.default_commercial_message.{company_id}', '')
        
        if not self.fne_footer_message:
            self.fne_footer_message = ICP.get_param(f'fne.default_footer_message.{company_id}', '')

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    @api.constrains('fne_is_rne', 'fne_rne_number')
    def _check_fne_rne(self):
        """Vérifier que le numéro RNE est renseigné si lié à un reçu"""
        for record in self:
            if record.fne_is_rne and not record.fne_rne_number:
                raise ValidationError(
                    "Le numéro RNE est obligatoire si la facture est liée à un reçu."
                )

    # =========================================================================
    # ACTION METHODS
    # =========================================================================

    def action_certify_fne(self):
        """Action pour certifier la facture auprès de la FNE"""
        self.ensure_one()
        
        # Charger les valeurs par défaut avant certification
        self._load_fne_defaults()
        
        self._check_fne_prerequisites()

        try:
            fne_data = self._prepare_fne_data()
            response = self._call_fne_certification_api(fne_data)
            self._process_fne_response(response)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Certification FNE',
                    'message': f'Facture certifiée avec succès. Référence FNE: {self.fne_reference}',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except Exception as e:
            _logger.error(f"Erreur certification FNE pour facture {self.name}: {str(e)}")
            raise UserError(f"Erreur lors de la certification FNE: {str(e)}")

    def action_download_fne_pdf(self):
        """Télécharger la facture certifiée FNE via l'URL stockée"""
        if self.fne_qr_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.fne_qr_url,
                'target': 'new',
            }
        else:
            raise UserError("Aucune URL de téléchargement FNE disponible pour cette facture.")

    def action_view_fne_qr_code(self):
        """Afficher le QR code de vérification"""
        if not self.fne_qr_url:
            raise UserError("Aucun QR code disponible pour cette facture.")

        return {
            'type': 'ir.actions.act_url',
            'url': self.fne_qr_url,
            'target': 'new',
        }

    def action_debug_lines(self):
        """Action pour déboguer les lignes depuis l'interface"""
        self.debug_invoice_lines_for_report()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Debug terminé',
                'message': f'Vérifiez les logs pour les détails des lignes de la facture {self.name}',
                'type': 'info',
            }
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def get_banner_image(self):
        """Retourne l'image banner en base64"""
        img_path = get_module_resource('fne_sale_invoice_certification', 'static', 'description', 'cdilogo.jpg')
        if img_path:
            with open(img_path, 'rb') as img_file:
                return base64.b64encode(img_file.read())
        return False

    def _check_fne_prerequisites(self):
        """Vérifier les prérequis avant certification"""
        if self.move_type != 'out_invoice':
            raise UserError("Seules les factures de vente peuvent être certifiées.")

        if self.state != 'posted':
            raise UserError("La facture doit être validée avant certification.")

        if self.fne_certified:
            raise UserError("Cette facture est déjà certifiée auprès de la FNE.")

        if not self.invoice_line_ids:
            raise UserError("La facture doit contenir au moins une ligne.")

    def _prepare_fne_data(self):
        """Préparer les données au format FNE"""
        items = self._prepare_fne_items()

        if not items:
            _logger.warning(f"Aucun item trouvé pour la facture {self.name}")
        else:
            _logger.info(f"Facture {self.name}: {len(items)} items préparés")

        data = {
            "invoiceType": "sale",
            "paymentMethod": self._get_fne_payment_method(),
            "template": self.fne_template,
            "isRne": self.fne_is_rne,
            "clientCompanyName": self.partner_id.name or "",
            "clientPhone": self.partner_id.phone or "",
            "clientEmail": self.partner_id.email or "",
            "pointOfSale": self.fne_point_of_sale or "",
            "establishment": self.fne_establishment or "",
            "commercialMessage": self.fne_commercial_message or "",
            "footer": self.fne_footer_message or "",
            "foreignCurrency": "",
            "foreignCurrencyRate": 0,
            "items": items,
            "customTaxes": [],
            "discount": 0
        }

        if self.fne_client_ncc:
            data["clientNcc"] = self.fne_client_ncc

        if self.fne_seller_name:
            data["clientSellerName"] = self.fne_seller_name

        if self.fne_is_rne and self.fne_rne_number:
            data["rne"] = self.fne_rne_number

        _logger.info(f"Données FNE préparées pour facture {self.name}: {len(data.get('items', []))} items")

        return data

    def _prepare_fne_items(self):
        """Préparer les lignes de facture pour FNE"""
        items = []

        valid_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note') and l.price_unit != 0
        )

        _logger.info(f"Facture {self.name}: {len(self.invoice_line_ids)} lignes totales, {len(valid_lines)} lignes valides")

        for line in valid_lines:
            taxes = self._get_fne_taxes(line)

            item = {
                "taxes": taxes,
                "customTaxes": [],
                "reference": self._get_item_reference(line),
                "description": self._get_item_description(line),
                "quantity": float(line.quantity),
                "amount": float(line.price_unit),
                "discount": float(line.discount),
                "measurementUnit": self._get_item_unit(line)
            }

            items.append(item)
            _logger.info(f"Item ajouté: {item['reference']} - {item['description']} - Qté: {item['quantity']}")

        _logger.info(f"Total items préparés pour facture {self.name}: {len(items)}")
        return items

    def _get_item_reference(self, line):
        """Obtenir la référence de l'item"""
        if line.product_id and line.product_id.default_code:
            return line.product_id.default_code
        elif line.product_id:
            return line.product_id.name[:20]
        else:
            return f"LIBRE_{line.id}"

    def _get_item_description(self, line):
        """Obtenir la description de l'item"""
        if line.name:
            return line.name
        elif line.product_id:
            return line.product_id.name
        else:
            return "Article libre"

    def _get_item_unit(self, line):
        """Obtenir l'unité de mesure"""
        if line.product_uom_id:
            return line.product_uom_id.name
        else:
            return "pcs"

    def _get_fne_taxes(self, line):
        """Obtenir les taxes FNE pour une ligne"""
        taxes = []
        for tax in line.tax_ids:
            if tax.amount == 18:
                taxes.append("TVA")
            elif tax.amount == 9:
                taxes.append("TVAB")
            elif tax.amount == 0:
                taxes.append("TVAC")
            else:
                taxes.append("TVA")

        return taxes or ["TVAC"]

    def _get_fne_payment_method(self):
        """Mapper le mode de paiement Odoo vers FNE"""
        return self.fne_payment_method or 'cash'

    def _call_fne_certification_api(self, data):
        """Appel à l'API de certification FNE"""
        company_id = self.company_id.id

        base_url = self.env['ir.config_parameter'].sudo().get_param('fne.base_url', 'http://54.247.95.108/ws')
        api_key = self.env['ir.config_parameter'].sudo().get_param(f'fne.api_key.{company_id}')

        if not api_key:
            raise UserError(
                f"Clé API FNE non configurée pour la société {self.company_id.name}.\n\n"
                f"Veuillez configurer les paramètres FNE dans:\n"
                f"Paramètres → FNE - Facture Normalisée Électronique"
            )

        url = f"{base_url}/external/invoices/sign"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        _logger.info(f"Envoi données FNE pour facture {self.name} (Société: {self.company_id.name})")
        _logger.debug(f"Données: {json.dumps(data, indent=2)}")

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code not in [200, 201]:
            error_msg = f"Erreur API FNE (Code {response.status_code})"
            try:
                error_data = response.json()
                error_msg += f": {error_data.get('message', 'Erreur inconnue')}"
            except:
                error_msg += f": {response.text}"

            raise UserError(error_msg)

        return response.json()

    def _process_fne_response(self, response):
        """Traiter la réponse de l'API FNE"""
        qr_url = response.get('token')

        qr_image = False
        if qr_url:
            qr_image = self._generate_qr_code(qr_url)

        self.write({
            'fne_certified': True,
            'fne_reference': response.get('reference'),
            'fne_token': response.get('token'),
            'fne_qr_url': qr_url,
            'fne_qr_code_image': qr_image,
            'fne_qr_code_data': qr_url,
            'fne_balance_sticker': response.get('balance_sticker', 0),
            'fne_warning': response.get('warning', False),
            'fne_response_data': response
        })

        self._process_fne_items_ids(response)

        _logger.info(f"Facture {self.name} certifiée FNE avec succès. Référence: {self.fne_reference}")

    def _generate_qr_code(self, url):
        """Générer un QR code à partir d'une URL"""
        try:
            import qrcode
            from io import BytesIO

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()

            return qr_image_base64

        except ImportError:
            _logger.warning("Module qrcode non installé. Installez-le avec: pip install qrcode[pil]")
            return False
        except Exception as e:
            _logger.error(f"Erreur lors de la génération du QR code: {str(e)}")
            return False

    def _process_fne_items_ids(self, response):
        """Récupérer et associer les IDs d'articles FNE aux lignes Odoo"""
        invoice_data = response.get('invoice', {})
        fne_items = invoice_data.get('items', [])

        if not fne_items:
            _logger.warning(f"Aucun item trouvé dans la réponse FNE pour la facture {self.name}")
            return

        valid_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note') and l.price_unit != 0
        )

        _logger.info(f"Facture {self.name}: {len(valid_lines)} lignes Odoo, {len(fne_items)} items FNE")

        self._map_fne_items_to_odoo_lines(valid_lines, fne_items)

    def _map_fne_items_to_odoo_lines(self, valid_lines, fne_items):
        """Mapper les articles FNE avec les lignes Odoo"""
        for i, odoo_line in enumerate(valid_lines):
            fne_item = self._find_fne_item_by_reference(odoo_line, fne_items)

            if not fne_item and i < len(fne_items):
                fne_item = fne_items[i]
                _logger.info(f"Correspondance par position pour ligne {odoo_line.id}")

            if fne_item:
                fne_item_id = fne_item.get('id')
                if fne_item_id:
                    odoo_line.write({'fne_item_id': fne_item_id})
                    _logger.info(
                        f"Ligne {odoo_line.id} - Produit: {odoo_line.product_id.name if odoo_line.product_id else 'Libre'} "
                        f"→ ID FNE: {fne_item_id}"
                    )
                else:
                    _logger.warning(f"Aucun ID trouvé dans l'item FNE: {fne_item}")
            else:
                _logger.warning(f"Aucun item FNE correspondant trouvé pour la ligne {odoo_line.id}")

    def _find_fne_item_by_reference(self, odoo_line, fne_items):
        """Trouver l'article FNE correspondant par référence"""
        odoo_reference = self._get_item_reference(odoo_line)

        for fne_item in fne_items:
            fne_reference = fne_item.get('reference', '')
            if fne_reference and fne_reference == odoo_reference:
                _logger.info(f"Correspondance trouvée par référence: {odoo_reference}")
                return fne_item

        odoo_description = self._get_item_description(odoo_line)
        for fne_item in fne_items:
            fne_description = fne_item.get('description', '')
            if fne_description and fne_description == odoo_description:
                _logger.info(f"Correspondance trouvée par description: {odoo_description}")
                return fne_item

        return None

    # =========================================================================
    # DEBUG METHODS
    # =========================================================================

    def debug_invoice_lines_for_report(self):
        """Méthode de débogage pour vérifier les lignes de facture"""
        _logger.info(f"=== DEBUG LIGNES FACTURE {self.name} ===")

        all_lines = self.invoice_line_ids
        _logger.info(f"Total lignes: {len(all_lines)}")

        for i, line in enumerate(all_lines):
            _logger.info(f"""
            Ligne {i + 1}:
            - ID: {line.id}
            - Nom: '{line.name}'
            - Display type: '{line.display_type}'
            - Produit: {line.product_id.name if line.product_id else 'AUCUN'}
            - Code produit: {line.product_id.default_code if line.product_id else 'AUCUN'}
            - Prix unitaire: {line.price_unit}
            - Quantité: {line.quantity}
            - Sous-total: {line.price_subtotal}
            - Taxes: {[tax.name for tax in line.tax_ids]}
            """)

        product_lines = all_lines.filtered(lambda l: l.display_type == 'product')
        section_lines = all_lines.filtered(lambda l: l.display_type == 'line_section')
        note_lines = all_lines.filtered(lambda l: l.display_type == 'line_note')
        no_display_type = all_lines.filtered(lambda l: not l.display_type)

        _logger.info(f"""
        STATISTIQUES FILTRAGE:
        - Total lignes: {len(all_lines)}
        - Lignes produit (display_type='product'): {len(product_lines)}
        - Lignes section (display_type='line_section'): {len(section_lines)}
        - Lignes note (display_type='line_note'): {len(note_lines)}
        - Lignes sans display_type: {len(no_display_type)}
        """)

        return True

    def debug_fne_items_mapping(self):
        """Debug pour vérifier les correspondances FNE"""
        if not self.fne_response_data:
            _logger.info("Aucune réponse FNE disponible")
            return

        invoice_data = self.fne_response_data.get('invoice', {})
        fne_items = invoice_data.get('items', [])

        _logger.info(f"=== DEBUG CORRESPONDANCES FNE - Facture {self.name} ===")

        valid_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note') and l.price_unit != 0
        )

        _logger.info(f"Lignes Odoo valides: {len(valid_lines)}")
        _logger.info(f"Items FNE reçus: {len(fne_items)}")

        for i, line in enumerate(valid_lines):
            _logger.info(f"""
            Ligne Odoo {i + 1}:
            - ID: {line.id}
            - Référence: {self._get_item_reference(line)}
            - Description: {self._get_item_description(line)}
            - ID FNE stocké: {line.fne_item_id or 'AUCUN'}
            """)

        for i, item in enumerate(fne_items):
            _logger.info(f"""
            Item FNE {i + 1}:
            - ID: {item.get('id')}
            - Référence: {item.get('reference')}
            - Description: {item.get('description')}
            - Quantité: {item.get('quantity')}
            """)

        return True
