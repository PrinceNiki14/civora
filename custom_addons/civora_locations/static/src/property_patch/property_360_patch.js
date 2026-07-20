import { patch } from "@web/core/utils/patch";
import { CivoraProperty360 } from "@civora_biens/properties/property_360";

/**
 * Enrichissement de la fiche Bien 360 par le module Locations.
 *
 * Sur un immeuble, le "Revenu locatif cumulé" et le loyer affiché sur chaque
 * carte d'unité proviennent desormais des BAUX ACTIFS reels (civora.lease),
 * et non plus du champ theorique monthly_revenue.
 *
 * Ce patch n'est charge que si civora_locations est installe : les champs
 * building_lease_revenue / active_lease_rent existent donc toujours ici.
 */
patch(CivoraProperty360.prototype, {
    async load() {
        await super.load();
        const rec = this.state.record;
        if (!rec || !rec.is_building) {
            return;
        }
        try {
            const [b] = await this.orm.read(
                "civora.property", [this.propertyId],
                [
                    "building_lease_revenue", "building_units_leased",
                    "building_collected", "building_expected",
                    "building_collection_rate", "building_arrears",
                ]
            );
            rec.building_lease_revenue = b.building_lease_revenue || 0;
            rec.building_units_leased = b.building_units_leased || 0;
            rec.building_collected = b.building_collected || 0;
            rec.building_expected = b.building_expected || 0;
            rec.building_collection_rate = b.building_collection_rate || 0;
            rec.building_arrears = b.building_arrears || 0;

            // Enrichit chaque unite avec le loyer de son bail actif.
            const unitIds = this.state.units.map((u) => u.id);
            if (unitIds.length) {
                const rows = await this.orm.read(
                    "civora.property", unitIds, ["active_lease_rent"]
                );
                const rentById = {};
                for (const r of rows) {
                    rentById[r.id] = r.active_lease_rent || 0;
                }
                // Reassignation pour garantir la reactivite OWL.
                this.state.units = this.state.units.map((u) => ({
                    ...u,
                    active_lease_rent: rentById[u.id] || 0,
                }));
            }
        } catch (e) {
            // civora_locations absent ou champs indisponibles : on retombe
            // silencieusement sur le comportement theorique de civora_biens.
        }
    },

    get buildingStats() {
        const stats = super.buildingStats;
        const rec = this.state.record || {};
        if (rec.building_lease_revenue !== undefined && rec.building_lease_revenue !== null) {
            // Conserve la valeur theorique a titre de reference, puis bascule
            // l'indicateur affiche sur le revenu locatif reel.
            stats.theoreticalRevenue = stats.monthlyRevenue;
            stats.monthlyRevenue = rec.building_lease_revenue;
            stats.leasedUnits = rec.building_units_leased || 0;
            stats.collected = rec.building_collected || 0;
            stats.expected = rec.building_expected || 0;
            stats.collectionRate = rec.building_collection_rate || 0;
            stats.arrears = rec.building_arrears || 0;
            stats.hasLeaseData = true;
        }
        return stats;
    },

    unitPriceLabel(u) {
        // Une unite sous bail actif affiche son loyer reel contractuel.
        if (u && u.active_lease_rent > 0) {
            return this.fmtMoney(u.active_lease_rent) + " /mois";
        }
        return super.unitPriceLabel(u);
    },
});
