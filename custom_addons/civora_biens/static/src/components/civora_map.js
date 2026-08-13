import { Component, onMounted, onWillUnmount, onWillUpdateProps, useRef } from "@odoo/owl";

// Coordonnees par defaut : centre d'Abidjan (Plateau).
const DEFAULT_CENTER = { lat: 5.3599, lng: -4.0083 };
const DEFAULT_ZOOM_EMPTY = 11;
const DEFAULT_ZOOM_MARKED = 15;

// L (Leaflet) est expose comme global une fois leaflet.js charge par Odoo
// (declare dans les assets_backend + assets_frontend du module).

/**
 * Carte Leaflet + OpenStreetMap.
 *
 * Props :
 *   latitude       : nombre ou 0/false si non defini
 *   longitude      : nombre ou 0/false si non defini
 *   interactive    : booleen — si true, clic pose/deplace le marqueur, marqueur
 *                    draggable ; si false, lecture seule.
 *   height         : hauteur CSS ("180px", "350px"...). Defaut 240px.
 *   zoom           : niveau de zoom initial ; sinon 11 si pas de marqueur, 15 sinon.
 *   onPositionChange : callback (lat, lng) => void, appele au clic / drag en mode
 *                    interactif.
 *
 * NB: le composant reste stable si les props lat/lng changent depuis l'exterieur
 *     (ex: parsing d'URL) — on met a jour le marqueur et le centre sans detruire
 *     la carte.
 */
export class CivoraMap extends Component {
    static template = "civora_biens.CivoraMap";
    static props = {
        latitude: { type: [Number, Boolean], optional: true },
        longitude: { type: [Number, Boolean], optional: true },
        interactive: { type: Boolean, optional: true },
        height: { type: String, optional: true },
        zoom: { type: Number, optional: true },
        onPositionChange: { type: Function, optional: true },
    };
    static defaultProps = {
        latitude: 0,
        longitude: 0,
        interactive: false,
        height: "240px",
        zoom: 0,
    };

    setup() {
        this.mapRef = useRef("map");
        this.map = null;
        this.marker = null;
        onMounted(() => this.initMap());
        onWillUpdateProps((next) => this.syncFromProps(next));
        onWillUnmount(() => this.cleanup());
    }

    hasPosition(lat, lng) {
        const la = Number(lat), lo = Number(lng);
        return Number.isFinite(la) && Number.isFinite(lo) && (la !== 0 || lo !== 0);
    }

    initMap() {
        // Attendre que Leaflet soit disponible (assets Odoo peut charger le CSS
        // avant le JS ; on protege par une pette relance courte).
        if (typeof window.L === "undefined") {
            setTimeout(() => this.initMap(), 60);
            return;
        }
        const el = this.mapRef.el;
        if (!el || this.map) return;

        // Chemin des icones marker : sert depuis le module.
        window.L.Icon.Default.imagePath = "/civora_biens/static/lib/leaflet/images/";

        const has = this.hasPosition(this.props.latitude, this.props.longitude);
        const center = has
            ? [Number(this.props.latitude), Number(this.props.longitude)]
            : [DEFAULT_CENTER.lat, DEFAULT_CENTER.lng];
        const zoom = this.props.zoom || (has ? DEFAULT_ZOOM_MARKED : DEFAULT_ZOOM_EMPTY);

        this.map = window.L.map(el, {
            zoomControl: true,
            scrollWheelZoom: this.props.interactive,
            dragging: true,
            attributionControl: true,
        }).setView(center, zoom);

        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a>",
            maxZoom: 19,
        }).addTo(this.map);

        if (has) this.putMarker(center[0], center[1]);
        if (this.props.interactive) {
            this.map.on("click", (e) => this.onMapClick(e));
        }

        // Fix Leaflet quand la carte est cachee au mount (drawer/modal) :
        // on force un invalidateSize apres coup pour eviter les tuiles grises.
        setTimeout(() => { if (this.map) this.map.invalidateSize(); }, 120);
    }

    putMarker(lat, lng) {
        if (!this.map || !window.L) return;
        if (this.marker) {
            this.marker.setLatLng([lat, lng]);
            return;
        }
        this.marker = window.L.marker([lat, lng], {
            draggable: this.props.interactive,
        }).addTo(this.map);
        if (this.props.interactive) {
            this.marker.on("dragend", (e) => {
                const { lat: la, lng: lo } = e.target.getLatLng();
                if (this.props.onPositionChange) this.props.onPositionChange(la, lo);
            });
        }
    }

    removeMarker() {
        if (this.marker && this.map) {
            this.map.removeLayer(this.marker);
            this.marker = null;
        }
    }

    onMapClick(e) {
        const { lat, lng } = e.latlng;
        this.putMarker(lat, lng);
        if (this.props.onPositionChange) this.props.onPositionChange(lat, lng);
    }

    syncFromProps(next) {
        // Ajustement quand le parent change les coordonnees (ex: geolocate,
        // parsing d'URL, effacement).
        if (!this.map) return;
        const has = this.hasPosition(next.latitude, next.longitude);
        if (has) {
            const la = Number(next.latitude), lo = Number(next.longitude);
            this.putMarker(la, lo);
            // Recentre uniquement si le point est hors vue visible.
            const bounds = this.map.getBounds();
            const point = window.L.latLng(la, lo);
            if (!bounds.contains(point)) {
                this.map.setView([la, lo], DEFAULT_ZOOM_MARKED);
            }
        } else {
            this.removeMarker();
        }
    }

    cleanup() {
        if (this.map) {
            this.map.remove();
            this.map = null;
            this.marker = null;
        }
    }
}
