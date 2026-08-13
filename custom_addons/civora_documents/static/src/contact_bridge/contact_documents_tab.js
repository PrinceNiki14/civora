import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DocumentsTab } from "@civora_documents/tab/documents_tab";

/**
 * Onglet Documents pour la fiche Contact 360°.
 * Wrapper minimal : injecte contactId dans DocumentsTab.
 *
 * includeRelated=true → l'onglet affiche pour un propriétaire :
 *   - ses documents personnels (mandat, pièce d'identité, RIB…)
 *   - les documents des biens dont il est propriétaire
 *   - les documents des baux de ses biens
 *
 * Pour un locataire :
 *   - ses documents personnels
 *   - les baux/quittances où il figure
 *   - les documents des biens qu'il loue
 */
export class ContactDocumentsTab extends Component {
    static template = "civora_documents.ContactDocumentsTab";
    static components = { DocumentsTab };
    static props = { contactId: { type: [Number, Boolean] } };
}

registry.category("civora_contact_360_tab").add("documents", {
    id: "documents",
    label: "Documents",
    sequence: 80,
    Component: ContactDocumentsTab,
});
