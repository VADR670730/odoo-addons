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

import netsvc
import time
from datetime import datetime
from tools.translate import _

from osv import osv
from osv import fields

class mrp_production_product_line(osv.osv):
    _inherit = 'mrp.production.product.line'
    
    _columns = {
        'location_id': fields.many2one('stock.location', 'Location'),
    }
mrp_production_product_line()

class mrp_production(osv.osv):

    _inherit = 'mrp.production'
    
    _columns = {
        'qty_per_lot': fields.float('Qty per Lot', states={'draft':[('readonly',False)]}),
    }
    
    def onchange_product_qty(self, cr, uid, ids, qty, context=None):
        res = {}
        lot_list = {}
        if qty:
            res = {
                'qty_per_lot': qty
            }
        return {'value': res}
    
    def create_lot(self, cr, uid, ids, product_id, production_id, context=None):
        egg_qty = 0
        date = ''
        product_obj = self.pool.get('product.product')
        picking_obj = self.pool.get('stock.picking')
        company_obj = self.pool.get('res.company')
        product = product_obj.browse(cr, uid, product_id)
        company_id = company_obj._company_default_get(cr, uid, 'mrp.routing', context=context)
        company = company_obj.browse(cr, uid, company_id)
        production = self.pool.get('mrp.production').browse(cr, uid, production_id)
        name = self.pool.get('ir.sequence').get(cr, uid, product.lot_sequence.code)
        if not name:
            raise osv.except_osv(_('Lot error'), _('%s needs production lot ! \
                            \nNo lot found for this product!') % (product.name))
        else:
            date = time.strptime(production.date_planned[:10], '%Y-%m-%d')
            name = name.replace('AAMMDD_', time.strftime('%y%m%d', date))
       
        ############# DESARROLLO A MEDIDA PARA IBERHUEVO ###############################
        lot_obj = self.pool.get('stock.production.lot')
        location = None
        cat_chicken_ids = []
        if product.lot_sequence.code == 'stock.production.lot.palet':
            picking_id = picking_obj.search(cr, uid, [('production_id', '=', production.id)])[0]
            for move in picking_obj.browse(cr, uid, picking_id).move_lines:
                if move.product_id.product_tmpl_id.categ_id in company.cat_egg_ids:  
                    location = move.location_id
                    egg_qty = move.product_qty
                    name = name.replace('FF', move.product_id.code[3:5])
            if not location:
                raise osv.except_osv(_('Lot error'), _('Impossible to find chicken location !'))
            for cat_chicken in company.cat_chicken_ids:
                cat_chicken_ids.append(cat_chicken.id)
            lot_list = self.get_lotlist(cr, uid, [('product_id.product_tmpl_id.categ_id', 'in', cat_chicken_ids), ('location_id', '=', location.id)], context)
            if not lot_list:
                raise osv.except_osv(_('Lot error'), _('Impossible to find chicken lots !'))
            for lot_id in lot_list.keys():
                lot = lot_obj.browse(cr, uid, int(lot_id))
                name = name.replace('LL_', lot.name[len(lot.name)-2:])
                if not lot.explotation:
                    raise osv.except_osv(_('Lot error'), _('%s %s needs to set explotation type !') % (lot.prefix,lot.name))
                name = name.replace('T_', lot.explotation.name)    
                if not lot.color:
                    raise osv.except_osv(_('Lot error'), _('%s %s needs to set color !') % (lot.prefix,lot.name))
                name = name.replace('C_', lot.color.name)
            name = name.replace('GGGNN_', location.name[0:5])
            
        elif product.lot_sequence.code == 'stock.production.lot.pienso':
            name = name.replace('OP', production.name.replace('/', ''))
            name = name.replace('REF', product.code)
            name = name.replace('GGGNNSS', production.location_dest_id.name)
            name = name[0:name.find('-')]
        ############# DESARROLLO A MEDIDA PARA IBERHUEVO ###############################
        
        if egg_qty > 0:
            egg_qty = egg_qty / production.product_qty
        
        data = {
            'name': name,
            'product_id': product.id,
            'egg_qty': egg_qty,
        }
        return self.pool.get('stock.production.lot').create(cr, uid, data)
    
    def get_lotlist(self, cr, uid, args, context=None):
        lot_list = {}
        ids = False
        decimal_obj = self.pool.get('decimal.precision')
        decimal_ids = decimal_obj.search(cr, uid, [('name', '=', 'Product UoM')])
        digits = 2
        for decimal_id in decimal_ids:
            digits = decimal_obj.browse(cr, uid, decimal_id).digits
        
        inventory_obj = self.pool.get('report.stock.inventory')
        if args:
            ids = inventory_obj.search(cr, uid, args)
        else:
            return {}
        for inventory in inventory_obj.browse(cr, uid, ids):
            if inventory.prodlot_id and inventory.state == 'done':
                if str(inventory.prodlot_id.id) in lot_list:
                    lot_list[str(inventory.prodlot_id.id)] += inventory.product_qty
                else:
                    lot_list.update({str(inventory.prodlot_id.id): inventory.product_qty})
            if inventory.prodlot_id and inventory.state == 'assigned' and inventory.product_qty < 0:
                if str(inventory.prodlot_id.id) in lot_list:
                    lot_list[str(inventory.prodlot_id.id)] += inventory.product_qty
                else:
                    lot_list.update({str(inventory.prodlot_id.id): inventory.product_qty})
                    
        if lot_list:
            for lot_id in lot_list.keys():
                lot_value = round(lot_list[lot_id], digits)
                if lot_value == 0.0:
                    del lot_list[lot_id]
                
        return lot_list
 
    def get_lot_auto(self, cr, uid, product_id, location_id, qty, context=None):
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        decimal_obj = self.pool.get('decimal.precision')
        decimal_ids = decimal_obj.search(cr, uid, [('name', '=', 'Product UoM')])
        digits = 2
        for decimal_id in decimal_ids:
            digits = decimal_obj.browse(cr, uid, decimal_id).digits
        lot_list = {}
        res = {}
        
        lot_list = self.get_lotlist(cr, uid, [('product_id', '=', product_id), ('location_id', '=', location_id)], context)
       
        if not lot_list:
            if product.track_production:
                raise osv.except_osv(_('Stock error'), _('%s needs production lots ! \
                            \nNo lot founded for this product!') % (product.name))
            return False
        
        qty = round(qty, digits)
        while qty > 0.0:
            cur_lot = 0.0
            if not lot_list and qty > 0.0:
                raise osv.except_osv(_('Stock error'), _('There is no enough stock for %s ! \
                            \n%s %s(s) missing!') % (product.name, round(qty,3), product.uom_id.name))
            elif product.lot_type_in == 'lifo':
                cur_lot = self.lifo_lot(cr, uid, lot_list, qty, context)
            elif product.lot_type_in == 'fifo':
                cur_lot = self.fifo_lot(cr, uid, lot_list, qty, context)
            
            lot_value = round(lot_list[cur_lot], digits)
            
            if lot_value <= qty:
                qty -= lot_value
                res.update({cur_lot: lot_value})
                del lot_list[cur_lot]
            else:
                res.update({cur_lot: qty})
                qty = 0.0
              
        if res:   
            for lot_id in res.keys():
                if res[lot_id] == 0:
                    del res[lot_id]
        
        return res
    
    def fifo_lot(self, cr, uid, lot_list, qty, context):
        lot_obj = self.pool.get('stock.production.lot')
        fifo_lot = False
        for lot_id in lot_list.keys():
            cur_lot = lot_obj.browse(cr, uid, int(lot_id))
            if not fifo_lot and (lot_list[lot_id] > 0):
                fifo_lot = cur_lot
            elif fifo_lot and cur_lot.date < fifo_lot.date and (lot_list[lot_id] > 0):
                fifo_lot = cur_lot
        if not fifo_lot:
            lot_names = ''
            for lot_id in lot_list.keys():
                lot = lot_obj.browse(cr, uid, int(lot_id))
                lot_names = lot_names + _('\tLot: '+ lot.name + ' Product: ' + lot.product_id.name + '\n')
            raise osv.except_osv(_('Lot error'), _('None of these lot is a valid lot. Please check them before restarting the process: \n%s'
                                                   % (lot_names)))
        return str(fifo_lot.id)
    
    def lifo_lot(self, cr, uid, lot_list, qty, context):
        lot_obj = self.pool.get('stock.production.lot')
        lifo_lot = False
        for lot_id in lot_list.keys():
            cur_lot = lot_obj.browse(cr, uid, int(lot_id))
            if not lifo_lot and (lot_list[lot_id] > 0):
                lifo_lot = cur_lot
            elif lifo_lot and cur_lot.date > lifo_lot.date and (lot_list[lot_id] > 0):
                lifo_lot = cur_lot
        if not lifo_lot:
            lot_names = ''
            for lot_id in lot_list.keys():
                lot = lot_obj.browse(cr, uid, int(lot_id))
                lot_names = lot_names + _('\tLot: '+ lot.name + ' Product: ' + lot.product_id.name + '\n')
            raise osv.except_osv(_('Lot error'), _('None of these lot is a valid lot. Please check them before restarting the process: \n%s'
                                                   % (lot_names)))
        return str(lifo_lot.id)
    
    def action_confirm(self, cr, uid, ids):
        """ Confirms production order.
        @return: Newly generated picking Id.
        """
        picking_id = False
        proc_ids = []
        res_final_id = []
        seq_obj = self.pool.get('ir.sequence')
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        wf_service = netsvc.LocalService("workflow")
        for production in self.browse(cr, uid, ids):
            if not production.product_lines:
                self.action_compute(cr, uid, [production.id])
                production = self.browse(cr, uid, [production.id])[0]
            routing_loc = None
            pick_type = 'internal'
            address_id = False
            if production.bom_id.routing_id and production.bom_id.routing_id.location_id:
                routing_loc = production.bom_id.routing_id.location_id
                if routing_loc.usage <> 'internal':
                    pick_type = 'out'
                address_id = routing_loc.address_id and routing_loc.address_id.id or False
                routing_loc = routing_loc.id
            source = production.product_id.product_tmpl_id.property_stock_production.id
            pick_name = seq_obj.get(cr, uid, 'stock.picking.' + pick_type)
            picking_id = pick_obj.create(cr, uid, {
                'name': pick_name,
                'origin': (production.origin or '').split(':')[0] + ':' + production.name,
                'type': pick_type,
                'move_type': 'one',
                'state': 'auto',
                'address_id': address_id,
                'auto_picking': self._get_auto_picking(cr, uid, production),
                'production_id': production.id,
                'company_id': production.company_id.id,
            })
            moves = []
            for line in production.product_lines:
                move_id = False
                newdate = production.date_planned
                if line.product_id.type in ('product', 'consu'):
                    if line.product_id.track_production and line.product_id.lot_type_in != 'manual':
                        lot_list = self.get_lot_auto(cr, uid, line.product_id.id, production.location_src_id.id, line.product_qty)
                        for lot_id in lot_list.keys():
                            value_dest = {
                                'name':'PROD:' + production.name,
                                'date': production.date_planned,
                                'product_id': line.product_id.id,
                                'product_qty': lot_list[lot_id],
                                'product_uom': line.product_uom.id,
                                'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                                'product_uos': line.product_uos and line.product_uos.id or False,
                                'location_id': routing_loc or production.location_src_id.id,
                                'location_dest_id': source,
                                'move_dest_id': res_final_id,
                                'state': 'waiting',
                                'company_id': production.company_id.id,
                            }
                            if lot_id:
                                value_dest.update({'prodlot_id': lot_id})
                            res_dest_id = move_obj.create(cr, uid, value_dest)
                            moves.append(res_dest_id)
                            value_move = {
                                'name':'PROD:' + production.name,
                                'picking_id':picking_id,
                                'product_id': line.product_id.id,
                                'product_qty': lot_list[lot_id],
                                'product_uom': line.product_uom.id,
                                'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                                'product_uos': line.product_uos and line.product_uos.id or False,
                                'date': newdate,
                                'move_dest_id': res_dest_id,
                                'location_id':  line.location_id and line.location_id.id or production.location_src_id.id,
                                'location_dest_id': routing_loc or production.location_src_id.id,
                                'state': 'confirmed',
                                'company_id': production.company_id.id,
                            }
                            if lot_id:
                                value_move.update({'prodlot_id': lot_id})
                            move_id = move_obj.create(cr, uid, value_move)
                            proc_id = proc_obj.create(cr, uid, {
                                'name': (production.origin or '').split(':')[0] + ':' + production.name,
                                'origin': (production.origin or '').split(':')[0] + ':' + production.name,
                                'date_planned': newdate,
                                'product_id': line.product_id.id,
                                'product_qty': line.product_qty,
                                'product_uom': line.product_uom.id,
                                'product_uos_qty': line.product_uos and line.product_qty or False,
                                'product_uos': line.product_uos and line.product_uos.id or False,
                                'location_id': production.location_src_id.id,
                                'procure_method': line.product_id.procure_method,
                                'move_id': move_id,
                                'company_id': production.company_id.id,
                            })
                            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
                            proc_ids.append(proc_id)
                    else:
                        value_dest = {
                            'name':'PROD:' + production.name,
                            'date': production.date_planned,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'product_uom': line.product_uom.id,
                            'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                            'product_uos': line.product_uos and line.product_uos.id or False,
                            'location_id': routing_loc or production.location_src_id.id,
                            'location_dest_id': source,
                            'move_dest_id': res_final_id,
                            'state': 'waiting',
                            'company_id': production.company_id.id,
                        }
                        res_dest_id = move_obj.create(cr, uid, value_dest)
                        moves.append(res_dest_id)
                        value_move = {
                            'name':'PROD:' + production.name,
                            'picking_id':picking_id,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'product_uom': line.product_uom.id,
                            'product_uos_qty': line.product_uos and line.product_uos_qty or False,
                            'product_uos': line.product_uos and line.product_uos.id or False,
                            'date': newdate,
                            'move_dest_id': res_dest_id,
                            'location_id': line.location_id and line.location_id.id or production.location_src_id.id,
                            'location_dest_id': routing_loc or production.location_src_id.id,
                            'state': 'confirmed',
                            'company_id': production.company_id.id,
                        }
                        move_id = move_obj.create(cr, uid, value_move)
                        proc_id = proc_obj.create(cr, uid, {
                            'name': (production.origin or '').split(':')[0] + ':' + production.name,
                            'origin': (production.origin or '').split(':')[0] + ':' + production.name,
                            'date_planned': newdate,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'product_uom': line.product_uom.id,
                            'product_uos_qty': line.product_uos and line.product_qty or False,
                            'product_uos': line.product_uos and line.product_uos.id or False,
                            'location_id': production.location_src_id.id,
                            'procure_method': line.product_id.procure_method,
                            'move_id': move_id,
                            'company_id': production.company_id.id,
                        })
                        wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
                        proc_ids.append(proc_id)
                self.write(cr, uid, [production.id], {'picking_id': picking_id, 'move_lines': [(6,0,moves)], 'state':'confirmed'})
            if production.product_id.track_production and production.product_id.lot_type_out == 'auto':
                qty = production.product_qty/production.qty_per_lot
                while qty != 0:
                    final_lot = self.create_lot(cr, uid, ids, production.product_id.id, production.id)
                    data = {
                        'name':'PROD:' + production.name,
                        'date': production.date_planned,
                        'product_id': production.product_id.id,
                        'product_qty': production.qty_per_lot,
                        'product_uom': production.product_uom.id,
                        'prodlot_id': final_lot,
                        'product_uos_qty': production.product_uos and production.product_uos_qty or False,
                        'product_uos': production.product_uos and production.product_uos.id or False,
                        'location_id': source,
                        'location_dest_id': production.location_dest_id.id,
                        'move_dest_id': production.move_prod_id.id,
                        'state': 'waiting',
                        'company_id': production.company_id.id,
                    }
                    res_final_id.append(move_obj.create(cr, uid, data))
                    qty -= 1
                seq_obj.write(cr, uid,  production.product_id.lot_sequence.id, {'number_next': 1})
            else:
                data = {
                    'name':'PROD:' + production.name,
                    'date': production.date_planned,
                    'product_id': production.product_id.id,
                    'product_qty': production.product_qty,
                    'product_uom': production.product_uom.id,
                    'product_uos_qty': production.product_uos and production.product_uos_qty or False,
                    'product_uos': production.product_uos and production.product_uos.id or False,
                    'location_id': source,
                    'location_dest_id': production.location_dest_id.id,
                    'move_dest_id': production.move_prod_id.id,
                    'state': 'waiting',
                    'company_id': production.company_id.id,
                }
                res_final_id.append(move_obj.create(cr, uid, data))
            self.write(cr, uid, [production.id], {'move_created_ids': [(6, 0, res_final_id)]})
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            message = _("Manufacturing order '%s' is scheduled for the %s.") % (
                production.name,
                datetime.strptime(production.date_planned,'%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y'),
            )
            self.log(cr, uid, production.id, message)
        return picking_id
    
mrp_production()