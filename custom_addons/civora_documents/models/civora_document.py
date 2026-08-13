# -*- coding: utf-8 -*-
from odoo import api, fields, models


# Typologie alignée sur le front CIVORA + spécificités ivoiriennes (ACD, titre foncier)
CIVORA_DOCUMENT_TYPE = [
    ('bail',           "Bail"),
    ('mandat',         "Mandat"),
    ('contrat',        "Contrat"),
    ('edl',            "État des lieux"),
    ('facture',        "Facture"),
    ('quittance',      "Quittance"),
    ('reporting',      "Reporting"),
    ('diagnostic',     "Diagnostic"),
    ('acd',            "ACD (Attestation Concession Définitive)"),
    ('titre_foncier',  "Titre foncier"),
    ('plan_cadastral', "Plan cadastral / architectural"),
    ('cert_propriete', "Certificat de propriété"),
    ('photo',          "Photo"),
    ('media',          "Média"),
    ('autre',          "Autre"),
]

# 6 dossiers canoniques (folder slugs alignés front)
CIVORA_DOCUMENT_FOLDER = [
    ('baux_contrats',             "Baux & contrats"),
    ('factures',                  "Factures"),
    ('documents_proprietaires',   "Documents propriétaires"),
    ('documents_locataires',      "Documents locataires"),
    ('documents_biens',           "Documents biens"),
    ('medias_photos',             "Médias & photos"),
]

# Mapping type → dossier par défaut (heuristique)
TYPE_TO_FOLDER_DEFAULT = {
    'bail':           'baux_contrats',
    'mandat':         'baux_contrats',
    'contrat':        'baux_contrats',
    'edl':            'baux_contrats',
    'facture':        'factures',
    'quittance':      'factures',
    'reporting':      'documents_proprietaires',
    'diagnostic':     'documents_biens',
    'acd':            'documents_biens',
    'titre_foncier':  'documents_biens',
    'plan_cadastral': 'documents_biens',
    'cert_propriete': 'documents_biens',
    'photo':          'medias_photos',
    'media':          'medias_photos',
    'autre':          'documents_biens',
}

CIVORA_DOCUMENT_CONFIDENTIALITY = [
    ('publique',       "Publique"),
    ('interne',        "Interne"),
    ('confidentielle', "Confidentielle"),
    ('restreinte',     "Restreinte"),
]

CIVORA_DOCUMENT_SOURCE = [
    ('manual',    "Upload manuel"),
    ('system',    "Généré par le système"),
    ('email',     "Reçu par email"),
    ('api',       "API externe"),
    ('migration', "Migration"),
]

CIVORA_DOCUMENT_STATE = [
    ('draft',      "À classer"),
    ('classified', "Classé"),
    ('validated',  "Validé"),
    ('archived',   "Archivé"),
]


class CivoraDocument(models.Model):
    """Document CIVORA — noyau de la GED transversale (v2).

    Chaque document est un enregistrement portant :
    - un fichier binaire (via ir.attachment natif Odoo)
    - une typologie CIVORA + un dossier canonique
    - un lien polymorphe vers l'entité métier (bail, contact, bien, ...)
    - des relations explicites vers Bien / Contact (raccourcis navigation)
    - des tags libres
    - un état de classification + confidentialité
    - versioning, signataires, journal d'audit (modèles enfants)
    """
    _name = 'civora.document'
    _description = "Document CIVORA"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_uploaded desc, id desc'
    _rec_name = 'name'
    _check_company_auto = True

    # ---- Identité ----
    name = fields.Char(
        string="Nom du document", required=True, tracking=True,
    )
    reference = fields.Char(
        string="Référence", copy=False, index=True, tracking=True,
        default=lambda self: self._default_reference(),
    )
    company_id = fields.Many2one(
        'res.company', string="Société",
        required=True, default=lambda self: self.env.company,
        index=True,
    )
    summary = fields.Text(
        string="Résumé",
        help="Résumé du contenu — sera rempli par l'OCR/IA dans une version ultérieure.",
    )

    # ---- Fichier ----
    attachment_id = fields.Many2one(
        'ir.attachment', string="Pièce jointe",
        required=True, ondelete='cascade',
    )
    file_size = fields.Integer(
        related='attachment_id.file_size', store=True, readonly=True,
        string="Taille (octets)",
    )
    mimetype = fields.Char(
        related='attachment_id.mimetype', store=True, readonly=True,
        string="Type MIME",
    )
    file_extension = fields.Char(
        string="Extension", compute='_compute_file_extension', store=True,
    )

    # ---- Typologie & dossier ----
    document_type = fields.Selection(
        CIVORA_DOCUMENT_TYPE, string="Type",
        default='autre', required=True, tracking=True, index=True,
    )
    folder = fields.Selection(
        CIVORA_DOCUMENT_FOLDER, string="Dossier",
        required=True, index=True, tracking=True,
        compute='_compute_folder_default', store=True, readonly=False,
        help="Dossier canonique où ranger le document. Déduit du type mais surchargeable.",
    )
    source = fields.Selection(
        CIVORA_DOCUMENT_SOURCE, string="Source",
        default='manual', required=True, tracking=True,
    )
    state = fields.Selection(
        CIVORA_DOCUMENT_STATE, string="Statut",
        default='classified', required=True, tracking=True,
    )
    confidentiality = fields.Selection(
        CIVORA_DOCUMENT_CONFIDENTIALITY, string="Confidentialité",
        default='interne', required=True, tracking=True,
    )

    # ---- Lien polymorphe vers entité métier ----
    res_model = fields.Char(
        string="Modèle lié", index=True, tracking=True,
    )
    res_id = fields.Integer(
        string="ID entité liée", index=True, tracking=True,
    )
    res_display = fields.Char(
        string="Entité liée", compute='_compute_res_display', store=True,
    )

    # ---- Liens explicites Bien / Contact (raccourcis navigation) ----
    linked_property_id = fields.Many2one(
        'civora.property', string="Bien concerné",
        index=True, ondelete='set null', tracking=True,
        help="Lien direct vers un bien — permet la navigation croisée depuis la fiche bien.",
    )
    linked_contact_id = fields.Many2one(
        'res.partner', string="Contact concerné",
        index=True, ondelete='set null', tracking=True,
        help="Lien direct vers un contact — permet la navigation croisée depuis la fiche contact.",
    )
    # Champs computed dérivés du bien pour navigation propriétaire ↔ locataire
    property_owner_id = fields.Many2one(
        'res.partner', string="Propriétaire (via bien)",
        related='linked_property_id.owner_id', store=True, readonly=True, index=True,
    )
    property_tenant_id = fields.Many2one(
        'res.partner', string="Locataire (via bien)",
        related='linked_property_id.tenant_id', store=True, readonly=True, index=True,
    )

    # ---- Métadonnées ----
    tag_ids = fields.Many2many(
        'civora.document.tag', string="Tags",
    )
    amount = fields.Monetary(
        string="Montant",
        currency_field='currency_id',
        help="Utilisé pour les factures et quittances.",
    )
    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        default=lambda self: self.env.company.currency_id,
    )
    date_uploaded = fields.Datetime(
        string="Date d'upload",
        default=fields.Datetime.now, required=True, readonly=True,
    )
    uploaded_by = fields.Many2one(
        'res.users', string="Uploadé par",
        default=lambda self: self.env.user, required=True, readonly=True,
    )
    author = fields.Char(
        string="Auteur",
        help="Auteur du document — peut différer de l'uploader (ex: document reçu).",
    )
    description = fields.Text(string="Description")

    # ---- Versioning ----
    version_number = fields.Integer(
        string="Numéro de version", default=1, readonly=True,
    )
    version_label = fields.Char(
        string="Version", compute='_compute_version_label', store=True,
    )
    version_ids = fields.One2many(
        'civora.document.version', 'document_id', string="Versions",
    )
    version_count = fields.Integer(
        compute='_compute_version_count', string="Nombre de versions",
    )

    # ---- Signataires ----
    signer_ids = fields.One2many(
        'civora.document.signer', 'document_id', string="Signataires",
    )
    signer_count = fields.Integer(
        compute='_compute_signer_counts', string="Nombre de signataires",
    )
    signer_signed_count = fields.Integer(
        compute='_compute_signer_counts', string="Signataires ayant signé",
    )
    signer_pending_count = fields.Integer(
        compute='_compute_signer_counts', string="Signataires en attente",
    )
    is_fully_signed = fields.Boolean(
        compute='_compute_signer_counts', string="Signé complet", store=True,
    )

    # ---- Audit / statistiques ----
    audit_ids = fields.One2many(
        'civora.document.audit', 'document_id', string="Journal d'audit",
    )
    views_count = fields.Integer(string="Consultations", default=0)
    downloads_count = fields.Integer(string="Téléchargements", default=0)

    # ══════════════════════════════════════════════════════════════════
    # Defaults & computes
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def _default_reference(self):
        seq = self.env['ir.sequence'].next_by_code('civora.document')
        return seq or "/"

    @api.depends('mimetype', 'name')
    def _compute_file_extension(self):
        for doc in self:
            ext = ""
            if doc.name and "." in doc.name:
                ext = doc.name.rsplit(".", 1)[-1].lower()
            elif doc.mimetype:
                mm = doc.mimetype
                if 'pdf' in mm: ext = "pdf"
                elif 'jpeg' in mm or 'jpg' in mm: ext = "jpg"
                elif 'png' in mm: ext = "png"
                elif 'word' in mm: ext = "docx"
                elif 'excel' in mm or 'spreadsheet' in mm: ext = "xlsx"
            doc.file_extension = ext

    @api.depends('res_model', 'res_id')
    def _compute_res_display(self):
        for doc in self:
            if doc.res_model and doc.res_id:
                try:
                    rec = self.env[doc.res_model].browse(doc.res_id)
                    doc.res_display = rec.display_name or "" if rec.exists() else ""
                except Exception:
                    doc.res_display = ""
            else:
                doc.res_display = ""

    @api.depends('document_type')
    def _compute_folder_default(self):
        for doc in self:
            if not doc.folder:
                doc.folder = TYPE_TO_FOLDER_DEFAULT.get(doc.document_type, 'documents_biens')

    @api.depends('version_number')
    def _compute_version_label(self):
        for doc in self:
            doc.version_label = "v%d" % (doc.version_number or 1)

    def _compute_version_count(self):
        for doc in self:
            doc.version_count = len(doc.version_ids)

    @api.depends('signer_ids', 'signer_ids.state')
    def _compute_signer_counts(self):
        for doc in self:
            all_signers = doc.signer_ids
            signed = all_signers.filtered(lambda s: s.state == 'signed')
            doc.signer_count = len(all_signers)
            doc.signer_signed_count = len(signed)
            doc.signer_pending_count = len(all_signers) - len(signed)
            doc.is_fully_signed = bool(all_signers) and len(signed) == len(all_signers)

    # ══════════════════════════════════════════════════════════════════
    # Create / Write / Unlink
    # ══════════════════════════════════════════════════════════════════
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == "/":
                vals['reference'] = self._default_reference()
            if not vals.get('name') and vals.get('attachment_id'):
                att = self.env['ir.attachment'].browse(vals['attachment_id'])
                if att.exists():
                    vals['name'] = att.name or "Document"
            # Fallback folder : si pas fourni, dériver du document_type via mapping.
            # Sécurité en plus du compute au cas où le compute ne se déclencherait pas.
            if not vals.get('folder'):
                doc_type = vals.get('document_type') or 'autre'
                vals['folder'] = TYPE_TO_FOLDER_DEFAULT.get(doc_type, 'documents_biens')
        docs = super().create(vals_list)
        # Sync res_model/res_id sur l'attachment
        for doc in docs:
            if doc.attachment_id and doc.res_model and doc.res_id:
                doc.attachment_id.sudo().write({
                    'res_model': doc.res_model,
                    'res_id': doc.res_id,
                })
            # Créer la version initiale
            self.env['civora.document.version'].sudo().create({
                'document_id': doc.id,
                'version_number': 1,
                'attachment_id': doc.attachment_id.id,
                'change_note': "Création initiale",
                'author_id': doc.uploaded_by.id,
            })
            # Log audit création
            self.env['civora.document.audit'].sudo().create({
                'document_id': doc.id,
                'action': 'create',
                'user_id': self.env.user.id,
                'detail': "Document créé — classification : %s" % (
                    dict(CIVORA_DOCUMENT_TYPE).get(doc.document_type, doc.document_type)
                ),
            })
        return docs

    def write(self, vals):
        res = super().write(vals)
        if 'res_model' in vals or 'res_id' in vals:
            for doc in self:
                if doc.attachment_id:
                    doc.attachment_id.sudo().write({
                        'res_model': doc.res_model or False,
                        'res_id': doc.res_id or 0,
                    })
        # Log audit changement de statut
        if 'state' in vals:
            for doc in self:
                self.env['civora.document.audit'].sudo().create({
                    'document_id': doc.id,
                    'action': 'state_change',
                    'user_id': self.env.user.id,
                    'detail': "Statut → %s" % dict(CIVORA_DOCUMENT_STATE).get(doc.state, doc.state),
                })
        return res

    def unlink(self):
        attachments = self.mapped('attachment_id')
        res = super().unlink()
        attachments.sudo().unlink()
        return res

    # ══════════════════════════════════════════════════════════════════
    # RPC — Upload et gestion
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def upload_document(self, vals):
        """Crée un document CIVORA à partir d'un fichier encodé base64."""
        if not vals.get('file_data'):
            from odoo.exceptions import UserError
            raise UserError("Aucun fichier fourni.")
        att_vals = {
            'name': vals.get('name') or "Document",
            'datas': vals['file_data'],
            'type': 'binary',
        }
        if vals.get('mimetype'):
            att_vals['mimetype'] = vals['mimetype']
        attachment = self.env['ir.attachment'].sudo().create(att_vals)
        doc_type = vals.get('document_type') or 'autre'
        doc_vals = {
            'name': vals.get('name') or "Document",
            'attachment_id': attachment.id,
            'document_type': doc_type,
            'source': vals.get('source') or 'manual',
            'state': 'classified' if doc_type != 'autre' else 'draft',
            'description': vals.get('description') or "",
            'confidentiality': vals.get('confidentiality') or 'interne',
            'author': vals.get('author') or "",
        }
        if vals.get('folder'):
            doc_vals['folder'] = vals['folder']
        if vals.get('res_model') and vals.get('res_id'):
            doc_vals['res_model'] = vals['res_model']
            doc_vals['res_id'] = int(vals['res_id'])
            # AUTO-POPULATE des liens explicites depuis le contexte de l'entité :
            # ça garantit qu'un document lié à un bail sera trouvable
            # depuis la fiche bien, propriétaire, locataire — pas seulement le bail.
            if vals['res_model'] == 'civora.lease':
                Lease = self.env.get('civora.lease')
                if Lease is not None:
                    lease = Lease.browse(int(vals['res_id']))
                    if lease.exists():
                        if lease.property_id and not vals.get('linked_property_id'):
                            doc_vals['linked_property_id'] = lease.property_id.id
                        if lease.tenant_id and not vals.get('linked_contact_id'):
                            doc_vals['linked_contact_id'] = lease.tenant_id.id
            elif vals['res_model'] == 'civora.property':
                if not vals.get('linked_property_id'):
                    doc_vals['linked_property_id'] = int(vals['res_id'])
            elif vals['res_model'] == 'res.partner':
                if not vals.get('linked_contact_id'):
                    doc_vals['linked_contact_id'] = int(vals['res_id'])
        if vals.get('linked_property_id'):
            doc_vals['linked_property_id'] = vals['linked_property_id']
        if vals.get('linked_contact_id'):
            doc_vals['linked_contact_id'] = vals['linked_contact_id']
        if vals.get('amount'):
            doc_vals['amount'] = vals['amount']
        if vals.get('tag_ids'):
            doc_vals['tag_ids'] = [(6, 0, vals['tag_ids'])]
        doc = self.create(doc_vals)
        return doc.id

    @api.model
    def upload_new_version(self, document_id, vals):
        """Remplace la pièce jointe d'un document existant par une nouvelle
        version — l'ancienne reste accessible via version_ids.
        """
        doc = self.browse(document_id)
        if not doc.exists():
            from odoo.exceptions import UserError
            raise UserError("Document introuvable.")
        if not vals.get('file_data'):
            from odoo.exceptions import UserError
            raise UserError("Aucun fichier fourni.")
        # Créer un nouvel attachment
        att_vals = {
            'name': vals.get('name') or doc.name,
            'datas': vals['file_data'],
            'type': 'binary',
            'res_model': doc.res_model or False,
            'res_id': doc.res_id or 0,
        }
        if vals.get('mimetype'):
            att_vals['mimetype'] = vals['mimetype']
        new_att = self.env['ir.attachment'].sudo().create(att_vals)
        # Bump version + créer entrée versioning avec l'ancien attachment
        old_att_id = doc.attachment_id.id
        old_version = doc.version_number or 1
        new_version = old_version + 1
        doc.write({
            'attachment_id': new_att.id,
            'version_number': new_version,
        })
        # La version courante est la nouvelle — on log l'ancienne comme historique
        self.env['civora.document.version'].sudo().create({
            'document_id': doc.id,
            'version_number': new_version,
            'attachment_id': new_att.id,
            'change_note': vals.get('change_note') or "Nouvelle version",
            'author_id': self.env.user.id,
        })
        # Audit
        self.env['civora.document.audit'].sudo().create({
            'document_id': doc.id,
            'action': 'new_version',
            'user_id': self.env.user.id,
            'detail': "Version v%d créée" % new_version,
        })
        return doc.id

    # ══════════════════════════════════════════════════════════════════
    # RPC — Recherche
    # ══════════════════════════════════════════════════════════════════
    @api.model
    def search_documents(self, domain=None, limit=500, offset=0):
        """Recherche paginée avec tous les champs UI en un seul appel."""
        domain = domain or []
        docs = self.search(domain, limit=limit, offset=offset)
        return {
            'documents': [self._serialize(d) for d in docs],
            'total': self.search_count(domain),
        }

    def _serialize(self, doc):
        type_labels = dict(CIVORA_DOCUMENT_TYPE)
        state_labels = dict(CIVORA_DOCUMENT_STATE)
        folder_labels = dict(CIVORA_DOCUMENT_FOLDER)
        conf_labels = dict(CIVORA_DOCUMENT_CONFIDENTIALITY)
        return {
            'id': doc.id,
            'name': doc.name,
            'reference': doc.reference,
            'document_type': doc.document_type,
            'document_type_label': type_labels.get(doc.document_type, ""),
            'folder': doc.folder,
            'folder_label': folder_labels.get(doc.folder, ""),
            'state': doc.state,
            'state_label': state_labels.get(doc.state, ""),
            'confidentiality': doc.confidentiality,
            'confidentiality_label': conf_labels.get(doc.confidentiality, ""),
            'res_model': doc.res_model or "",
            'res_id': doc.res_id or 0,
            'res_display': doc.res_display or "",
            'linked_property_id': doc.linked_property_id.id if doc.linked_property_id else False,
            'linked_property_name': doc.linked_property_id.display_name if doc.linked_property_id else "",
            'linked_contact_id': doc.linked_contact_id.id if doc.linked_contact_id else False,
            'linked_contact_name': doc.linked_contact_id.display_name if doc.linked_contact_id else "",
            'property_owner_id': doc.property_owner_id.id if doc.property_owner_id else False,
            'property_owner_name': doc.property_owner_id.display_name if doc.property_owner_id else "",
            'property_tenant_id': doc.property_tenant_id.id if doc.property_tenant_id else False,
            'property_tenant_name': doc.property_tenant_id.display_name if doc.property_tenant_id else "",
            'file_size': doc.file_size or 0,
            'file_extension': doc.file_extension or "",
            'mimetype': doc.mimetype or "",
            'date_uploaded': str(doc.date_uploaded) if doc.date_uploaded else "",
            'uploaded_by': doc.uploaded_by.name if doc.uploaded_by else "",
            'author': doc.author or "",
            'attachment_id': doc.attachment_id.id if doc.attachment_id else False,
            'description': doc.description or "",
            'summary': doc.summary or "",
            'amount': doc.amount or 0.0,
            'version_label': doc.version_label,
            'version_number': doc.version_number,
            'signer_count': doc.signer_count,
            'signer_signed_count': doc.signer_signed_count,
            'is_fully_signed': doc.is_fully_signed,
            'views_count': doc.views_count,
            'downloads_count': doc.downloads_count,
            'tag_ids': [
                {'id': t.id, 'name': t.name, 'color': t.color}
                for t in doc.tag_ids
            ],
        }

    @api.model
    def get_library_kpis(self):
        """KPIs de l'écran bibliothèque : totaux, ce mois, signatures en attente, taille."""
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        total = self.search_count([])
        this_month = self.search_count([('date_uploaded', '>=', month_start)])
        classified_count = self.search_count([('state', 'in', ('classified', 'validated'))])
        classified_pct = int(classified_count / total * 100) if total else 0
        # Signatures en attente
        pending_sigs = self.env['civora.document.signer'].search_count([
            ('state', '=', 'pending'),
        ])
        all_docs = self.search([])
        total_size = sum(all_docs.mapped('file_size'))
        return {
            'total': total,
            'this_month': this_month,
            'classified_pct': classified_pct,
            'pending_signatures': pending_sigs,
            'total_size': total_size,
            'total_size_fmt': self._fmt_size(total_size),
        }

    @api.model
    def get_folders_summary(self):
        """Compte le nombre de documents par dossier canonique."""
        folder_labels = dict(CIVORA_DOCUMENT_FOLDER)
        result = []
        for slug, label in CIVORA_DOCUMENT_FOLDER:
            count = self.search_count([('folder', '=', slug)])
            result.append({
                'slug': slug,
                'name': label,
                'count': count,
            })
        return result

    @api.model
    def _fmt_size(self, n):
        n = int(n or 0)
        if n >= 1024**3:
            return "%.1f Go" % (n / 1024**3)
        if n >= 1024**2:
            return "%.1f Mo" % (n / 1024**2)
        if n >= 1024:
            return "%.1f Ko" % (n / 1024)
        return "%d o" % n

    @api.model
    def get_documents_for_entity(self, res_model, res_id, include_related=False):
        """Documents attachés à une entité métier — utilisé par les onglets 360°.

        Si include_related=True :
          - Sur res.partner : docs des baux du partner + docs des biens dont il est owner/tenant
          - Sur civora.property : docs des baux du bien
          - Sur civora.lease : docs du bien + du locataire + du propriétaire
        """
        if not res_model or not res_id:
            return {'documents': [], 'total': 0}
        # Domaine base : lien direct polymorphe OU linked_property_id / linked_contact_id
        sub_domains = []
        # Match polymorphe direct
        sub_domains.append([('res_model', '=', res_model), ('res_id', '=', res_id)])
        # Match linked_property_id ou linked_contact_id
        if res_model == 'civora.property':
            sub_domains.append([('linked_property_id', '=', res_id)])
        elif res_model == 'res.partner':
            sub_domains.append([('linked_contact_id', '=', res_id)])
        # Extensions "related"
        if include_related:
            if res_model == 'res.partner':
                # Baux du partner (comme locataire OU propriétaire)
                Lease = self.env.get('civora.lease')
                if Lease is not None:
                    lease_ids = Lease.search([
                        '|', ('tenant_id', '=', res_id),
                        ('owner_id', '=', res_id),
                    ]).ids
                    if lease_ids:
                        sub_domains.append([
                            ('res_model', '=', 'civora.lease'),
                            ('res_id', 'in', lease_ids),
                        ])
                # Biens dont il est owner ou tenant
                Property = self.env.get('civora.property')
                if Property is not None:
                    property_ids = Property.search([
                        '|', ('owner_id', '=', res_id),
                        ('tenant_id', '=', res_id),
                    ]).ids
                    if property_ids:
                        sub_domains.append([('linked_property_id', 'in', property_ids)])
                        sub_domains.append([
                            ('res_model', '=', 'civora.property'),
                            ('res_id', 'in', property_ids),
                        ])
                    # Baux liés à ces biens (propriétaire)
                    if property_ids and Lease is not None:
                        via_prop_leases = Lease.search([('property_id', 'in', property_ids)]).ids
                        if via_prop_leases:
                            sub_domains.append([
                                ('res_model', '=', 'civora.lease'),
                                ('res_id', 'in', via_prop_leases),
                            ])
            elif res_model == 'civora.property':
                Lease = self.env.get('civora.lease')
                if Lease is not None:
                    lease_ids = Lease.search([('property_id', '=', res_id)]).ids
                    if lease_ids:
                        sub_domains.append([
                            ('res_model', '=', 'civora.lease'),
                            ('res_id', 'in', lease_ids),
                        ])
            elif res_model == 'civora.lease':
                Lease = self.env.get('civora.lease')
                if Lease is not None:
                    lease = Lease.browse(res_id)
                    if lease.exists():
                        if lease.property_id:
                            sub_domains.append([('linked_property_id', '=', lease.property_id.id)])
                        if lease.tenant_id:
                            sub_domains.append([('linked_contact_id', '=', lease.tenant_id.id)])
                        if lease.owner_id:
                            sub_domains.append([('linked_contact_id', '=', lease.owner_id.id)])

        # Filtrer les sous-domaines vides pour éviter les erreurs
        sub_domains = [sd for sd in sub_domains if sd]
        if not sub_domains:
            return {'documents': [], 'total': 0}

        # Combiner tous les sous-domaines avec OR en notation polish Odoo.
        #
        # Un domaine Odoo utilise la notation polonaise préfixée : les
        # opérateurs | (OR) et & (AND) sont BINAIRES et précèdent leurs
        # opérandes. Par défaut, les leaves sont AND-jointes implicitement,
        # MAIS dès qu'on introduit des | explicites, il faut aussi expliciter
        # les & pour les sous-domaines multi-leaves.
        #
        # Ex : sous-domaine A = [('res_model','=','civora.lease'),('res_id','=',5)]
        # → 2 leaves reliées par AND → en polish notation explicite :
        #    ['&', ('res_model','=','civora.lease'), ('res_id','=',5)]
        #
        # Pour combiner 3 sous-domaines A, B, C en OR :
        #    ['|', '|', <A_polish>, <B_polish>, <C_polish>]
        def _to_polish(sd):
            """Convertit un sous-domaine (liste de leaves AND-implicites) en
            notation polish explicite en préfixant les & nécessaires.
            """
            leaves = [x for x in sd if x != '&' and x != '|' and x != '!']
            # On garde les opérateurs déjà présents dans sd
            n_leaves = len(leaves)
            n_and = n_leaves - 1
            # Reconstruit : n_and fois "&" puis toutes les leaves
            return ['&'] * n_and + leaves

        if len(sub_domains) == 1:
            final_domain = sub_domains[0]
        else:
            n_or = len(sub_domains) - 1
            final_domain = ['|'] * n_or
            for sd in sub_domains:
                final_domain += _to_polish(sd)
        return self.search_documents(domain=final_domain, limit=500)

    @api.model
    def get_folder_documents(self, folder_slug):
        """Documents d'un dossier canonique donné."""
        return self.search_documents(
            domain=[('folder', '=', folder_slug)],
            limit=500,
        )

    @api.model
    def get_folder_documents_grouped(self, folder_slug, group_by='property'):
        """Documents d'un dossier canonique, groupés par entité.

        group_by :
          - 'property'        : par bien
          - 'owner'           : par propriétaire
          - 'tenant'          : par locataire
          - 'owner_property'  : hiérarchique propriétaire → bien
          - 'month'           : par mois d'upload

        Retourne :
        {
            'groups': [
                {
                    'id': 'property_5',
                    'entity_type': 'property',
                    'entity_id': 5,
                    'entity_name': 'Villa Cocody',
                    'entity_secondary': 'Propriétaire : Aké Brigitte',  # optionnel
                    'count': 3,
                    'documents': [<serialized>],
                    'subgroups': [<subgroup>],  # présent uniquement pour owner_property
                },
                ...
            ],
            'ungrouped': [<serialized>],   # docs sans lien pertinent
            'total': 42,
        }
        """
        docs = self.search([('folder', '=', folder_slug)])
        # Résoudre le bien effectif pour chaque doc (le doc peut pointer
        # directement un bien via linked_property_id, ou indirectement via un
        # bail via res_model=civora.lease).
        Lease = self.env.get('civora.lease')
        resolved = []
        for d in docs:
            property_id = d.linked_property_id.id if d.linked_property_id else False
            tenant_id = False
            owner_id = False
            # Cas doc lié à un bail : remonter au bien et aux acteurs
            if not property_id and d.res_model == 'civora.lease' and d.res_id and Lease is not None:
                lease = Lease.browse(d.res_id)
                if lease.exists():
                    if lease.property_id:
                        property_id = lease.property_id.id
                    if lease.tenant_id:
                        tenant_id = lease.tenant_id.id
                    if lease.owner_id:
                        owner_id = lease.owner_id.id
            # Compléter avec les liens explicites
            if not tenant_id and d.property_tenant_id:
                tenant_id = d.property_tenant_id.id
            if not owner_id and d.property_owner_id:
                owner_id = d.property_owner_id.id
            # Contact direct (peut être propriétaire OU locataire selon contexte)
            contact_id = d.linked_contact_id.id if d.linked_contact_id else False
            resolved.append({
                'doc': d,
                'property_id': property_id,
                'tenant_id': tenant_id,
                'owner_id': owner_id,
                'contact_id': contact_id,
            })

        Property = self.env.get('civora.property')
        Partner = self.env['res.partner']

        def _property_info(pid):
            if not pid or Property is None:
                return None
            p = Property.browse(pid)
            if not p.exists():
                return None
            owner_name = p.owner_id.display_name if p.owner_id else ""
            return {
                'entity_type': 'property',
                'entity_id': p.id,
                'entity_name': p.display_name,
                'entity_secondary': ("Propriétaire : " + owner_name) if owner_name else "",
            }

        def _partner_info(pid, role_label=""):
            if not pid:
                return None
            partner = Partner.browse(pid)
            if not partner.exists():
                return None
            return {
                'entity_type': 'partner',
                'entity_id': partner.id,
                'entity_name': partner.display_name,
                'entity_secondary': role_label,
            }

        def _month_info(d):
            if not d.date_uploaded:
                return None
            dt = d.date_uploaded
            key = "%d-%02d" % (dt.year, dt.month)
            months = ["janvier", "février", "mars", "avril", "mai", "juin",
                      "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            return {
                'entity_type': 'month',
                'entity_id': key,
                'entity_name': "%s %d" % (months[dt.month - 1], dt.year),
                'entity_secondary': "",
                '_sort_key': key,
            }

        groups_map = {}
        ungrouped = []

        # ---- Groupement hiérarchique owner_property : 2 niveaux ----
        if group_by == 'owner_property':
            # Structure : owner_id → { info, biens: { property_id → { info, docs } } }
            owner_map = {}
            for r in resolved:
                pid = r['property_id']
                if not pid:
                    ungrouped.append(r['doc'])
                    continue
                # Chercher l'owner via le bien
                oid = None
                if Property is not None:
                    p = Property.browse(pid)
                    if p.exists() and p.owner_id:
                        oid = p.owner_id.id
                if not oid:
                    ungrouped.append(r['doc'])
                    continue
                if oid not in owner_map:
                    owner_info = _partner_info(oid, "Propriétaire")
                    if not owner_info:
                        ungrouped.append(r['doc'])
                        continue
                    owner_map[oid] = {
                        'info': owner_info,
                        'biens': {},
                        'count': 0,
                    }
                if pid not in owner_map[oid]['biens']:
                    pinfo = _property_info(pid)
                    if not pinfo:
                        ungrouped.append(r['doc'])
                        continue
                    owner_map[oid]['biens'][pid] = {
                        'info': pinfo, 'docs': [],
                    }
                owner_map[oid]['biens'][pid]['docs'].append(r['doc'])
                owner_map[oid]['count'] += 1

            groups = []
            for oid, data in sorted(owner_map.items(), key=lambda kv: kv[1]['info']['entity_name'].lower()):
                subgroups = []
                for pid, pdata in sorted(data['biens'].items(), key=lambda kv: kv[1]['info']['entity_name'].lower()):
                    subgroups.append({
                        'id': 'property_%d' % pid,
                        'entity_type': 'property',
                        'entity_id': pid,
                        'entity_name': pdata['info']['entity_name'],
                        'entity_secondary': "",
                        'count': len(pdata['docs']),
                        'documents': [self._serialize(x) for x in pdata['docs']],
                    })
                groups.append({
                    'id': 'owner_%d' % oid,
                    'entity_type': 'partner',
                    'entity_id': oid,
                    'entity_name': data['info']['entity_name'],
                    'entity_secondary': "Propriétaire",
                    'count': data['count'],
                    'documents': [],  # vide car hiérarchique
                    'subgroups': subgroups,
                })
            return {
                'groups': groups,
                'ungrouped': [self._serialize(d) for d in ungrouped],
                'total': len(docs),
                'group_by': group_by,
            }

        # ---- Groupements simples 1 niveau ----
        for r in resolved:
            d = r['doc']
            key = None
            info = None
            sort_key = None

            if group_by == 'property':
                if r['property_id']:
                    info = _property_info(r['property_id'])
                    key = 'property_%d' % r['property_id']
            elif group_by == 'owner':
                # Priorité au propriétaire du bien ; sinon contact direct
                target_id = r['owner_id'] or (r['contact_id'] if not r['tenant_id'] else None)
                if target_id:
                    info = _partner_info(target_id, "Propriétaire")
                    key = 'partner_%d' % target_id
            elif group_by == 'tenant':
                target_id = r['tenant_id'] or (r['contact_id'] if not r['owner_id'] else None)
                if target_id:
                    info = _partner_info(target_id, "Locataire")
                    key = 'partner_%d' % target_id
            elif group_by == 'month':
                minfo = _month_info(d)
                if minfo:
                    info = minfo
                    key = 'month_' + minfo['entity_id']
                    sort_key = minfo['_sort_key']

            if key is None or info is None:
                ungrouped.append(d)
                continue

            if key not in groups_map:
                groups_map[key] = {
                    'id': key,
                    'entity_type': info['entity_type'],
                    'entity_id': info['entity_id'],
                    'entity_name': info['entity_name'],
                    'entity_secondary': info.get('entity_secondary', ""),
                    'count': 0,
                    'documents': [],
                    '_sort_key': sort_key,
                }
            groups_map[key]['documents'].append(d)
            groups_map[key]['count'] += 1

        # Tri
        if group_by == 'month':
            # Tri chronologique inverse (plus récent en premier)
            groups_list = sorted(
                groups_map.values(),
                key=lambda g: g.get('_sort_key') or "",
                reverse=True,
            )
        else:
            groups_list = sorted(
                groups_map.values(),
                key=lambda g: (g['entity_name'] or "").lower(),
            )

        # Sérialiser les documents et nettoyer les champs internes
        for g in groups_list:
            g['documents'] = [self._serialize(x) for x in g['documents']]
            g.pop('_sort_key', None)

        return {
            'groups': groups_list,
            'ungrouped': [self._serialize(d) for d in ungrouped],
            'total': len(docs),
            'group_by': group_by,
        }

    @api.model
    def get_tags(self):
        tags = self.env['civora.document.tag'].search([])
        return [{'id': t.id, 'name': t.name, 'color': t.color} for t in tags]

    @api.model
    def create_tag(self, name):
        name = (name or "").strip()
        if not name:
            return False
        tag = self.env['civora.document.tag'].search([('name', '=', name)], limit=1)
        if not tag:
            tag = self.env['civora.document.tag'].create({'name': name})
        return {'id': tag.id, 'name': tag.name, 'color': tag.color}

    # ---- Actions state ----
    def action_classify(self, document_type=None):
        for doc in self:
            vals = {'state': 'classified' if doc.state == 'draft' else doc.state}
            if document_type:
                vals['document_type'] = document_type
            doc.write(vals)
        return True

    def action_validate(self):
        for doc in self:
            doc.state = 'validated'
        return True

    def action_archive(self):
        for doc in self:
            doc.state = 'archived'
        return True

    def action_set_draft(self):
        for doc in self:
            doc.state = 'draft'
        return True

    # ---- Audit hooks ----
    @api.model
    def log_view(self, document_id):
        """Enregistrer une consultation."""
        doc = self.browse(document_id)
        if doc.exists():
            doc.sudo().views_count = (doc.views_count or 0) + 1
            self.env['civora.document.audit'].sudo().create({
                'document_id': doc.id,
                'action': 'view',
                'user_id': self.env.user.id,
                'detail': "Aperçu du document",
            })
        return True

    @api.model
    def log_download(self, document_id):
        doc = self.browse(document_id)
        if doc.exists():
            doc.sudo().downloads_count = (doc.downloads_count or 0) + 1
            self.env['civora.document.audit'].sudo().create({
                'document_id': doc.id,
                'action': 'download',
                'user_id': self.env.user.id,
                'detail': "Téléchargement",
            })
        return True

    @api.model
    def get_audit_events(self, document_id, limit=100):
        """Récupère les événements d'audit d'un document, formatés pour l'UI."""
        events = self.env['civora.document.audit'].search(
            [('document_id', '=', document_id)],
            order='date desc, id desc', limit=limit,
        )
        action_labels = dict(
            self.env['civora.document.audit']._fields['action'].selection
        )
        return [{
            'id': e.id,
            'action': e.action,
            'action_label': action_labels.get(e.action, e.action),
            'user_name': e.user_id.name if e.user_id else "Système",
            'detail': e.detail or "",
            'date': str(e.date) if e.date else "",
        } for e in events]

    @api.model
    def get_versions(self, document_id):
        """Historique des versions d'un document."""
        versions = self.env['civora.document.version'].search(
            [('document_id', '=', document_id)],
            order='version_number desc, id desc',
        )
        return [{
            'id': v.id,
            'version_number': v.version_number,
            'version_label': "v%d" % v.version_number,
            'change_note': v.change_note or "",
            'author_name': v.author_id.name if v.author_id else "—",
            'date': str(v.date_created) if v.date_created else "",
            'attachment_id': v.attachment_id.id if v.attachment_id else False,
            'is_current': v.document_id.version_number == v.version_number,
        } for v in versions]

    @api.model
    def get_signers(self, document_id):
        """Signataires d'un document avec leur état."""
        signers = self.env['civora.document.signer'].search(
            [('document_id', '=', document_id)],
            order='sequence, id',
        )
        state_labels = dict(
            self.env['civora.document.signer']._fields['state'].selection
        )
        role_labels = dict(
            self.env['civora.document.signer']._fields['role'].selection
        )
        return [{
            'id': s.id,
            'name': s.name,
            'email': s.email or "",
            'role': s.role,
            'role_label': role_labels.get(s.role, s.role),
            'state': s.state,
            'state_label': state_labels.get(s.state, s.state),
            'date_signed': str(s.date_signed) if s.date_signed else "",
            'sequence': s.sequence,
        } for s in signers]

    @api.model
    def add_signer(self, document_id, vals):
        """Ajoute un signataire à un document."""
        vals['document_id'] = document_id
        signer = self.env['civora.document.signer'].create(vals)
        self.env['civora.document.audit'].sudo().create({
            'document_id': document_id,
            'action': 'sign_request',
            'user_id': self.env.user.id,
            'detail': "Invitation à signer envoyée : %s (%s)" % (vals.get('name', '—'), vals.get('role', '—')),
        })
        return signer.id
