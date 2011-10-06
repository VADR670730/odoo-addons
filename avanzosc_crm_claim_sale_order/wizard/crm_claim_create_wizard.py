# -*- encoding: utf-8 -*-
##############################################################################
#
#    Avanzosc - Avanced Open Source Consulting
#    Copyright (C) 2011 - 2012 Avanzosc <http://www.avanzosc.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
from osv import osv
from osv import fields

class crm_claim_create_wizard(osv.osv_memory):
    _name = 'crm.claim.create.wizard'
    _description = 'Wizard to create a  claim from sale order'
 
    _columns = {
        'name':fields.char('Claim Subject', size=64, required=True),
        'claim_date':fields.datetime('Claim Date'),
        'section_id':fields.many2one('crm.case.section', 'Sales Team'),
    }
    
crm_claim_create_wizard()
