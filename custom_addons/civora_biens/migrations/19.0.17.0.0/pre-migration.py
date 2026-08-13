# -*- coding: utf-8 -*-
"""
Migration civora_biens 19.0.17.0.0 : reference automatique des biens.

Cette migration s'execute en PRE, avant la reprise du chargement du module :

  1. Ajoute la colonne reference_prefix sur civora_property_type (Odoo le fera
     automatiquement quand le module chargera, mais on s'assure ici du
     backfill idempotent).
  2. Pour chaque type sans prefix, genere une valeur depuis le nom (3 lettres
     ASCII majuscules).
  3. Aligne les prefixes des 6 types seed sur les valeurs canoniques
     (VIL / APP / STU / BUR / LOC / TER) - dans le respect des personnalisations
     eventuelles.
  4. Rien n'est fait sur les biens ici : la generation de reference pour les
     biens existants a lieu en POST (une fois que le nouveau modele est
     charge), car elle utilise ir.sequence qui a besoin de l'ORM.
"""
import re
import unicodedata


def _slugify_prefix(text, length=3):
    base = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
    base = re.sub(r'[^a-zA-Z]', '', base).upper()
    if not base:
        return 'REF'
    return base[:length].ljust(length, 'X')[:length]


CANONICAL_PREFIX_BY_CODE = {
    'villa': 'VIL',
    'appartement': 'APP',
    'studio': 'STU',
    'bureau': 'BUR',
    'local_commercial': 'LOC',
    'terrain': 'TER',
}


def migrate(cr, version):
    # 1. Verifier que la colonne existe (Odoo la cree via l'ORM au chargement,
    #    mais si elle n'existe pas encore on l'ajoute pour pouvoir remplir).
    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'civora_property_type' AND column_name = 'reference_prefix'
    """)
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE civora_property_type
              ADD COLUMN reference_prefix VARCHAR
        """)

    # 2. Pour les types seed connus, valeur canonique si prefix vide.
    for code, prefix in CANONICAL_PREFIX_BY_CODE.items():
        cr.execute("""
            UPDATE civora_property_type
               SET reference_prefix = %s
             WHERE code = %s
               AND (reference_prefix IS NULL OR reference_prefix = '')
        """, (prefix, code))

    # 3. Pour tous les autres types sans prefix, generer depuis le nom.
    #    Champ name traduit -> JSONB. On extrait la version en_US ou fr_FR.
    cr.execute("""
        SELECT id, name, code
          FROM civora_property_type
         WHERE reference_prefix IS NULL OR reference_prefix = ''
    """)
    rows = cr.fetchall()
    for type_id, name_json, code in rows:
        label = ''
        if isinstance(name_json, dict):
            label = name_json.get('fr_FR') or name_json.get('en_US') or next(iter(name_json.values()), '')
        else:
            label = str(name_json or '')
        prefix = _slugify_prefix(label or code or 'REF', 3)
        cr.execute("""
            UPDATE civora_property_type SET reference_prefix = %s WHERE id = %s
        """, (prefix, type_id))

    # 4. Enfin, on rend la colonne NOT NULL pour aligner avec la definition ORM.
    cr.execute("""
        ALTER TABLE civora_property_type
          ALTER COLUMN reference_prefix SET NOT NULL
    """)
