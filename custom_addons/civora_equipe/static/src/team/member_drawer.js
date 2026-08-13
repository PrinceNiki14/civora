/** @odoo-module **/
// NOTE : ce fichier porte le nom historique « member_drawer » mais
// contient desormais la MODALE centree du formulaire membre, alignee
// sur le front CIVORA. Le nom de fichier est conserve pour ne pas
// casser les bundles d'assets deja publies.
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CivoraDrawer } from "@civora_core/components/civora_drawer";

// Bureaux CIVORA proposes par defaut ; la liste est completee par les bureaux
// deja utilises par l'equipe, et reste ouverte via « Autre bureau… ».
const DEFAULT_OFFICES = ["Plateau HQ", "Cocody", "Riviera", "Marcory", "Bassam"];

const PRESENCES = [
    { id: "present", label: "Présent" },
    { id: "en_visite", label: "En visite" },
    { id: "conge", label: "Congé" },
    { id: "teletravail", label: "Télétravail" },
];

const FIELDS = [
    "name", "role_id", "job_title", "department", "location", "email", "phone",
    "presence", "status", "hire_date", "sales_target", "fixed_salary",
    "quarterly_bonus", "bio", "user_id",
];

/**
 * Modale « Ajouter / Modifier un membre », alignee sur le formulaire du front
 * CIVORA. Le collaborateur existe independamment d'un compte Odoo : la case
 * « Creer un acces CIVORA » declenche la creation du compte cote serveur.
 */
export class MemberDialog extends Component {
    static template = "civora_equipe.MemberDialog";
    static components = { CivoraDrawer };
    static props = {
        memberId: { type: [Number, Boolean], optional: true },
        onClose: Function,
        onSaved: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.presences = PRESENCES;

        this.state = useState({
            saving: false,
            roles: [],
            offices: [...DEFAULT_OFFICES],
            customOffice: false,
            createAccess: true,
            values: {
                name: "",
                role_id: 0,
                job_title: "",
                location: "Plateau HQ",
                email: "",
                phone: "",
                presence: "present",
                hire_year: new Date().getFullYear(),
                sales_target: 0,
                fixed_salary: 0,
                quarterly_bonus: 0,
            },
        });

        onWillStart(async () => {
            const [roles, used] = await Promise.all([
                this.orm.searchRead("civora.agent.role", [["active", "=", true]],
                    ["name"], { order: "sequence, name" }),
                this.orm.searchRead("civora.team.member", [], ["location"], { limit: 200 }),
            ]);
            this.state.roles = roles;
            const extra = [...new Set(used.map((m) => m.location).filter(Boolean))]
                .filter((o) => !DEFAULT_OFFICES.includes(o));
            this.state.offices = [...DEFAULT_OFFICES, ...extra];
            if (this.props.memberId) {
                await this.loadMember(this.props.memberId);
            }
        });
    }

    get isEdit() {
        return !!this.props.memberId;
    }
    get title() {
        return this.isEdit ? "Modifier le membre" : "Ajouter un membre";
    }

    async loadMember(id) {
        const [rec] = await this.orm.read("civora.team.member", [id], FIELDS);
        if (!rec) return;
        const v = this.state.values;
        v.name = rec.name || "";
        v.role_id = rec.role_id ? rec.role_id[0] : 0;
        v.job_title = rec.job_title || "";
        v.location = rec.location || "Plateau HQ";
        v.email = rec.email || "";
        v.phone = rec.phone || "";
        v.presence = rec.presence || "present";
        v.hire_year = rec.hire_date ? Number(String(rec.hire_date).slice(0, 4)) : "";
        v.sales_target = rec.sales_target || 0;
        v.fixed_salary = rec.fixed_salary || 0;
        v.quarterly_bonus = rec.quarterly_bonus || 0;
        this.state.createAccess = false;
        this.hasAccess = !!rec.user_id;
        if (v.location && !this.state.offices.includes(v.location)) {
            this.state.offices.push(v.location);
        }
    }

    /** Vrai si le poste `r` est celui du membre (comparaison souple id/chaine). */
    isRole(r) {
        return `${this.state.values.role_id}` === `${r.id}`;
    }

    setField(key, ev) {
        const el = ev.target;
        this.state.values[key] = el.type === "number"
            ? (el.value === "" ? 0 : Number(el.value))
            : el.value;
    }
    onOfficeChange(ev) {
        if (ev.target.value === "__autre__") {
            this.state.customOffice = true;
            this.state.values.location = "";
        } else {
            this.state.customOffice = false;
            this.state.values.location = ev.target.value;
        }
    }
    toggleAccess(ev) {
        this.state.createAccess = ev.target.checked;
    }

    async save() {
        if (this.state.saving) return;
        const v = this.state.values;
        if (!(v.name || "").trim()) {
            this.notification.add("Le nom complet est obligatoire.", { type: "warning" });
            return;
        }
        if (this.state.createAccess && !(v.email || "").trim()) {
            this.notification.add(
                "L'email professionnel est nécessaire pour créer un accès CIVORA.",
                { type: "warning" }
            );
            return;
        }
        this.state.saving = true;
        try {
            const vals = {
                name: v.name.trim(),
                role_id: v.role_id ? Number(v.role_id) : false,
                job_title: v.job_title || false,
                location: v.location || false,
                email: v.email || false,
                phone: v.phone || false,
                presence: v.presence,
                sales_target: v.sales_target,
                fixed_salary: v.fixed_salary,
                quarterly_bonus: v.quarterly_bonus,
                hire_date: v.hire_year ? `${v.hire_year}-01-01` : false,
            };
            let memberId = this.props.memberId;
            if (memberId) {
                await this.orm.write("civora.team.member", [memberId], vals);
            } else {
                const created = await this.orm.create("civora.team.member", [vals]);
                memberId = Array.isArray(created) ? created[0] : created;
            }

            if (this.state.createAccess) {
                // La creation du compte ne doit jamais faire echouer
                // l'enregistrement du collaborateur : le membre existe
                // independamment de son acces CIVORA.
                let res;
                try {
                    res = await this.orm.call(
                        "civora.team.member", "action_create_user_access", [[memberId]]
                    );
                } catch (accessError) {
                    res = {
                        error:
                            "Membre enregistré, mais la création de l'accès CIVORA a échoué : "
                            + ((accessError && accessError.data && accessError.data.message)
                               || accessError.message || accessError),
                    };
                }
                if (res.error) {
                    this.notification.add(res.error, { type: "warning" });
                } else if (res.created) {
                    this.notification.add(
                        `Accès CIVORA créé pour ${res.login}.`
                        + (res.invite_url ? " Lien d'invitation copié dans le presse-papier." : ""),
                        { type: "success" }
                    );
                    if (res.invite_url) {
                        try { await navigator.clipboard.writeText(res.invite_url); } catch { /* ignore */ }
                    }
                } else if (res.message) {
                    this.notification.add(res.message, { type: "info" });
                }
            }

            this.notification.add(
                this.isEdit ? "Membre mis à jour" : "Membre ajouté", { type: "success" }
            );
            this.props.onSaved();
        } catch (e) {
            this.notification.add("Enregistrement impossible : " + (e.message || e),
                { type: "danger" });
            throw e;
        } finally {
            this.state.saving = false;
        }
    }
}
