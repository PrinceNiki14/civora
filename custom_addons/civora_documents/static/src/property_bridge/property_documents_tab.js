import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { CivoraProperty360 } from "@civora_biens/properties/property_360";
import { DocumentsTab } from "@civora_documents/tab/documents_tab";

/**
 * Adaptateur : Property 360° passe `propertyId` aux contributions ;
 * on l'utilise pour instancier DocumentsTab avec resModel/resId.
 *
 * include_related=true → l'onglet affiche :
 *   - les documents directement rattachés au bien (ACD, titre foncier, plan,
 *     diagnostics, photos)
 *   - les documents des baux liés à ce bien (bail signé, EDL, quittances)
 * Résultat : vue consolidée de tout ce qui concerne le bien.
 */
export class PropertyDocumentsTab extends Component {
    static template = "civora_documents.PropertyDocumentsTab";
    static components = { DocumentsTab };
    static props = { propertyId: { type: [Number, Boolean] } };
}

// Contribution registry — l'onglet apparaît via le pattern déjà en place
// dans civora_biens (contribTabs mappés dans tabList).
registry.category("civora_property_360_tab").add("documents", {
    id: "documents",
    label: "Documents",
    sequence: 60,  // avant Occupation (70) et Finance (80) par convention
    Component: PropertyDocumentsTab,
});

/**
 * Patch le tabList de CivoraProperty360 pour retirer l'onglet "documents"
 * placeholder codé en dur — sinon on aurait 2 onglets Documents (statique + contrib).
 */
patch(CivoraProperty360.prototype, {
    get tabList() {
        const base = super.tabList;
        // Retirer les doublons "documents" — on garde uniquement notre contribution
        const seen = new Set();
        const result = [];
        for (const t of base) {
            if (t.id === "documents") {
                if (seen.has("documents")) continue;
                seen.add("documents");
            }
            result.push(t);
        }
        return result;
    },
});
