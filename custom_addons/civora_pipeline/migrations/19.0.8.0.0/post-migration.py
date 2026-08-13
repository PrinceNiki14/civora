# -*- coding: utf-8 -*-
"""
Migration civora_pipeline 19.0.8.0.0 : dates de suivi des opportunites.

Ajout des champs date_stage_updated / date_won / date_lost sur civora.opportunity.
Odoo cree automatiquement les colonnes en base ; ce script se contente de les
initialiser proprement pour les enregistrements existants :

  - date_stage_updated : au create_date (best-effort, on ne connait pas les
    changements d'etape passes).
  - date_won : au write_date des opportunites deja dans une etape gagnee.
  - date_lost : idem pour les etapes perdues.
"""


def migrate(cr, version):
    # date_stage_updated : create_date par defaut.
    cr.execute("""
        UPDATE civora_opportunity
           SET date_stage_updated = create_date
         WHERE date_stage_updated IS NULL
    """)

    # date_won : write_date pour les opps deja dans une etape gagnee.
    cr.execute("""
        UPDATE civora_opportunity o
           SET date_won = COALESCE(o.date_stage_updated, o.write_date, o.create_date)
          FROM civora_pipeline_stage s
         WHERE o.stage_id = s.id
           AND s.is_won = TRUE
           AND o.date_won IS NULL
    """)

    # date_lost : idem pour les etapes perdues.
    cr.execute("""
        UPDATE civora_opportunity o
           SET date_lost = COALESCE(o.date_stage_updated, o.write_date, o.create_date)
          FROM civora_pipeline_stage s
         WHERE o.stage_id = s.id
           AND s.is_lost = TRUE
           AND o.date_lost IS NULL
    """)
