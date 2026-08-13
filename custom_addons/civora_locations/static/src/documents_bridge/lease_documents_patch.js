import { patch } from "@web/core/utils/patch";
import { CivoraLease360 } from "@civora_locations/lease_detail/lease_360";
import { DocumentsTab } from "@civora_documents/tab/documents_tab";

/**
 * Ajoute l'onglet "Documents" dans le Bail 360° via patch.
 * Utilise le composant réutilisable civora_documents/tab/documents_tab.
 * L'onglet est inséré entre "Contrat" et "Incidents & Relances".
 */
patch(CivoraLease360, {
    components: {
        ...CivoraLease360.components,
        DocumentsTab,
    },
});

// Patch de l'instance : injection de l'onglet dans tabList
patch(CivoraLease360.prototype, {
    get tabList() {
        // On copie la liste parente pour ne pas la muter
        const base = super.tabList;
        // Insérer "documents" juste avant "incidents"
        const documentsTab = { id: "documents", label: "Documents" };
        const idx = base.findIndex((t) => t.id === "incidents");
        if (idx >= 0) {
            const result = base.slice();
            result.splice(idx, 0, documentsTab);
            return result;
        }
        return [...base, documentsTab];
    },
});
