import { Component } from "@odoo/owl";

/**
 * Composant de prévisualisation d'un document (PDF/image/fallback).
 */
export class DocumentPreview extends Component {
    static template = "civora_documents.DocumentPreview";
    static props = {
        attachmentId: { type: [Number, Boolean] },
        mimetype: { type: String, optional: true },
        name: { type: String, optional: true },
    };

    get isImage() {
        return this.props.mimetype && this.props.mimetype.startsWith("image/");
    }
    get isPdf() {
        return this.props.mimetype === "application/pdf";
    }
    get url() {
        return this.props.attachmentId ? `/web/content/${this.props.attachmentId}` : "";
    }
    get downloadUrl() {
        return this.props.attachmentId ? `/web/content/${this.props.attachmentId}?download=true` : "#";
    }
}
