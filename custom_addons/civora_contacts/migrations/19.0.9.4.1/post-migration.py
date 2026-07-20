# -*- coding: utf-8 -*-
"""
Migration cloisonnement multi-societe des contacts CIVORA.

Contrairement au post_init_hook (qui ne s'execute qu'a l'INSTALLATION), ce
script de migration s'execute lors d'une mise a jour (-u) des lors que la
version du module progresse. Il rattache a la societe principale tous les
contacts/acquereurs CIVORA restes sans societe (company_id vide), afin qu'ils
redeviennent visibles apres l'activation de la regle de cloisonnement.

On procede en SQL direct pour ne pas etre gene par la regle de securite
elle-meme (qui masque justement les enregistrements a company_id vide).
"""


def migrate(cr, version):
    # Societe principale = la plus ancienne (id le plus petit).
    cr.execute("SELECT id FROM res_company ORDER BY id ASC LIMIT 1")
    row = cr.fetchone()
    if not row:
        return
    main_company_id = row[0]

    # Contacts CIVORA sans societe : flag civora_is_contact OU au moins un role
    # CIVORA (acquereur, proprietaire, locataire...).
    cr.execute(
        """
        UPDATE res_partner
           SET company_id = %s
         WHERE company_id IS NULL
           AND (
                civora_is_contact = TRUE
                OR id IN (SELECT partner_id FROM civora_partner_role_rel)
           )
        """,
        (main_company_id,),
    )
