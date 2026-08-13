# -*- coding: utf-8 -*-
"""
Migration civora_pipeline 19.0.7.0.0 : etapes par societe.

Avant : les 6 etapes seed etaient globales (company_id NULL) et partagees.
Apres : chaque societe possede son propre jeu d'etapes (company_id NOT NULL).

Cette migration :
  1. Liste toutes les societes existantes.
  2. Pour chacune, cree les 6 etapes par defaut (Nouveau, Qualifie, Visite,
     Offre, Gagne, Perdu) si elles n'existent pas deja.
  3. Reaffecte chaque opportunite vers l'etape correspondante (par code) de
     sa propre societe.
  4. Supprime les seeds globales (company_id IS NULL) devenues inutiles.

On procede en SQL direct pour ignorer les regles de securite et pour eviter
la reentrance sur les contraintes ORM tant que la migration n'est pas achevee.

NB: le champ 'name' de civora.pipeline.stage est translate=True, donc stocke
    en JSONB : on doit fournir un objet {code_lang: valeur, ...}.
"""
import json


DEFAULT_STAGES = [
    # (code, name, sequence, is_won, is_lost, fold)
    ('nouveau', "Nouveau", 10, False, False, False),
    ('qualifie', "Qualifié", 20, False, False, False),
    ('visite', "Visite", 30, False, False, False),
    ('offre', "Offre", 40, False, False, False),
    ('gagne', "Gagné", 50, True, False, False),
    ('perdu', "Perdu", 60, False, True, True),
]


def _installed_langs(cr):
    """Retourne la liste des codes de langue actifs (au moins en_US)."""
    cr.execute("SELECT code FROM res_lang WHERE active = TRUE")
    codes = [row[0] for row in cr.fetchall()]
    if not codes:
        codes = ['en_US']
    if 'en_US' not in codes:
        # Odoo utilise en_US comme langue de reference technique.
        codes.append('en_US')
    return codes


def _jsonb_translate(text, lang_codes):
    """Construit la charge JSON pour un champ translate=True."""
    return json.dumps({code: text for code in lang_codes})


def migrate(cr, version):
    # 1. Recuperer toutes les societes.
    cr.execute("SELECT id FROM res_company ORDER BY id ASC")
    company_ids = [row[0] for row in cr.fetchall()]
    if not company_ids:
        return

    lang_codes = _installed_langs(cr)

    # 2. Pour chaque societe, s'assurer qu'elle possede les 6 etapes par defaut.
    for company_id in company_ids:
        cr.execute(
            "SELECT code FROM civora_pipeline_stage WHERE company_id = %s",
            (company_id,),
        )
        existing_codes = {row[0] for row in cr.fetchall()}
        for code, name, sequence, is_won, is_lost, fold in DEFAULT_STAGES:
            if code in existing_codes:
                continue
            name_json = _jsonb_translate(name, lang_codes)
            cr.execute(
                """
                INSERT INTO civora_pipeline_stage
                    (name, code, sequence, is_won, is_lost, fold, active,
                     company_id, create_uid, create_date, write_uid, write_date)
                VALUES (%s::jsonb, %s, %s, %s, %s, %s, TRUE,
                        %s, 1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC')
                """,
                (name_json, code, sequence, is_won, is_lost, fold, company_id),
            )

    # 3. Construire le mapping (ancien_stage_id global) -> code, puis reaffecter
    #    les opportunites vers l'etape (meme code) de leur societe.
    cr.execute(
        "SELECT id, code FROM civora_pipeline_stage WHERE company_id IS NULL"
    )
    global_stage_by_id = dict(cr.fetchall())

    if global_stage_by_id:
        global_ids = tuple(global_stage_by_id.keys())

        cr.execute(
            """
            SELECT o.id, o.company_id, o.stage_id
              FROM civora_opportunity o
             WHERE o.stage_id IN %s
            """,
            (global_ids,),
        )
        opp_rows = cr.fetchall()
        for opp_id, company_id, old_stage_id in opp_rows:
            code = global_stage_by_id.get(old_stage_id)
            if not code or not company_id:
                continue
            cr.execute(
                """
                SELECT id FROM civora_pipeline_stage
                 WHERE company_id = %s AND code = %s LIMIT 1
                """,
                (company_id, code),
            )
            row = cr.fetchone()
            if row:
                cr.execute(
                    "UPDATE civora_opportunity SET stage_id = %s WHERE id = %s",
                    (row[0], opp_id),
                )

        # Nettoyage : supprimer les references XML puis les seeds globales.
        cr.execute(
            """
            DELETE FROM ir_model_data
             WHERE model = 'civora.pipeline.stage'
               AND res_id IN %s
            """,
            (global_ids,),
        )
        cr.execute(
            "DELETE FROM civora_pipeline_stage WHERE id IN %s",
            (global_ids,),
        )
