// =====================================================================
// CIVORA Documents — constantes partagées (types, dossiers, helpers)
// =====================================================================

export const DOC_TYPE_META = {
    bail:           { label: "Bail",             variant: "info",    icon: "fa-file-text-o" },
    mandat:         { label: "Mandat",           variant: "info",    icon: "fa-file-text-o" },
    contrat:        { label: "Contrat",          variant: "info",    icon: "fa-file-text-o" },
    edl:            { label: "EDL",              variant: "warning", icon: "fa-clipboard" },
    facture:        { label: "Facture",          variant: "success", icon: "fa-file-text-o" },
    quittance:      { label: "Quittance",        variant: "success", icon: "fa-file-text-o" },
    reporting:      { label: "Reporting",        variant: "neutral", icon: "fa-bar-chart" },
    diagnostic:     { label: "Diagnostic",       variant: "warning", icon: "fa-stethoscope" },
    acd:            { label: "ACD",              variant: "success", icon: "fa-certificate" },
    titre_foncier:  { label: "Titre foncier",    variant: "success", icon: "fa-certificate" },
    plan_cadastral: { label: "Plan cadastral",   variant: "info",    icon: "fa-map-o" },
    cert_propriete: { label: "Cert. propriété",  variant: "success", icon: "fa-certificate" },
    photo:          { label: "Photo",            variant: "neutral", icon: "fa-camera" },
    media:          { label: "Média",            variant: "neutral", icon: "fa-photo" },
    autre:          { label: "Autre",            variant: "neutral", icon: "fa-file-o" },
};

export const STATE_META = {
    draft:      { label: "À classer",  variant: "warning" },
    classified: { label: "Classé",     variant: "info" },
    validated:  { label: "Validé",     variant: "success" },
    archived:   { label: "Archivé",    variant: "neutral" },
};

export const CONFIDENTIALITY_META = {
    publique:       { label: "Publique",       variant: "success" },
    interne:        { label: "Interne",        variant: "info" },
    confidentielle: { label: "Confidentielle", variant: "warning" },
    restreinte:     { label: "Restreinte",     variant: "danger" },
};

export const FOLDER_META = {
    baux_contrats: {
        name: "Baux & contrats",
        icon: "fa-file-signature",
        color: "accent",
        description: "Baux, mandats, contrats de gestion, états des lieux",
    },
    factures: {
        name: "Factures",
        icon: "fa-file-text",
        color: "info",
        description: "Factures et quittances",
    },
    documents_proprietaires: {
        name: "Documents propriétaires",
        icon: "fa-user-circle-o",
        color: "primary",
        description: "Mandats et reportings pour les propriétaires",
    },
    documents_locataires: {
        name: "Documents locataires",
        icon: "fa-users",
        color: "success",
        description: "Baux, quittances et documents locataires",
    },
    documents_biens: {
        name: "Documents biens",
        icon: "fa-building-o",
        color: "warning",
        description: "Diagnostics, plans, titres fonciers, photos",
    },
    medias_photos: {
        name: "Médias & photos",
        icon: "fa-photo",
        color: "neutral",
        description: "Photos et médias divers",
    },
};

export const EXT_ICONS = {
    pdf:  "fa-file-pdf-o",
    jpg:  "fa-file-image-o",
    jpeg: "fa-file-image-o",
    png:  "fa-file-image-o",
    gif:  "fa-file-image-o",
    doc:  "fa-file-word-o",
    docx: "fa-file-word-o",
    xls:  "fa-file-excel-o",
    xlsx: "fa-file-excel-o",
    ppt:  "fa-file-powerpoint-o",
    pptx: "fa-file-powerpoint-o",
    zip:  "fa-file-archive-o",
    txt:  "fa-file-text-o",
};

// ---- Helpers ----
export function fmtSize(n) {
    n = Number(n || 0);
    if (n >= 1024**3) return (n / 1024**3).toFixed(1).replace(".", ",") + " Go";
    if (n >= 1024**2) return (n / 1024**2).toFixed(1).replace(".", ",") + " Mo";
    if (n >= 1024) return (n / 1024).toFixed(0) + " Ko";
    return n + " o";
}

export function fmtDate(d) {
    if (!d) return "—";
    const dt = new Date(d);
    if (isNaN(dt)) return d;
    const dd = String(dt.getDate()).padStart(2, "0");
    const mm = String(dt.getMonth() + 1).padStart(2, "0");
    const yy = dt.getFullYear();
    return `${dd}/${mm}/${yy}`;
}

export function fmtDateTime(d) {
    if (!d) return "—";
    const dt = new Date(d);
    if (isNaN(dt)) return d;
    const dd = String(dt.getDate()).padStart(2, "0");
    const mm = String(dt.getMonth() + 1).padStart(2, "0");
    const yy = dt.getFullYear();
    const h = String(dt.getHours()).padStart(2, "0");
    const min = String(dt.getMinutes()).padStart(2, "0");
    return `${dd}/${mm}/${yy} ${h}:${min}`;
}

export function fileIcon(fileExtension) {
    return "fa " + (EXT_ICONS[(fileExtension || "").toLowerCase()] || "fa-file-o");
}

export function downloadUrl(attachmentId) {
    return attachmentId ? `/web/content/${attachmentId}?download=true` : "#";
}
