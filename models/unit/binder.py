# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import odoo
from odoo.addons.odoo_magento2_ept.models.backend.connector import Binder
from odoo.addons.odoo_magento2_ept.models.backend.backend import magento


class MagentoBinder(Binder):
    """ Generic Binder for Magento """


@magento
class MagentoModelBinder(MagentoBinder):
    """
    Bindings are done directly on the binding model.

    Binding models are models called ``magento.{normal_model}``,
    like ``magento.res.partner`` or ``magento.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Magento ID, the ID of the Magento Backend and the additional
    fields belonging to the Magento instance.
    """
    _model_name = [
        'magento.website',
        'magento.store',
        'magento.storeview',
        'res.partner',
        'magento.res.partner.category',
        'magento.product.product',
        #'magento.stock.picking',
        'stock.picking',
        'magento.sale.order',
        'magento.sale.order.line',
        #'magento.account.invoice',
        'account.invoice',
        'magento.product.category',
        'magento.product.template',
    ]

    def to_openerp(self, external_id, unwrap=False, browse=False):
        """ Give the odoo ID for an external ID

        :param external_id: external ID for which we want the odoo ID
        :param unwrap: if True, returns the normal record (the one
                       inherits'ed), else return the binding record
        :param browse: if True, returns a recordset
        :return: a recordset of one record, depending on the value of unwrap,
                 or an empty recordset if no binding is found
        :rtype: recordset
        """
        bindings = self.model.with_context(active_test=False).search(
            [('magento_id', '=', str(external_id)),
             ('backend_id', '=', self.backend_record.id)]
        )
        if not bindings:
            return self.model.browse() if browse else None
        assert len(bindings) == 1, "Several records found: %s" % (bindings,)
        if unwrap:
            return bindings.erp_id if browse else bindings.erp_id.id
        else:
            return bindings if browse else bindings.id

    def to_backend(self, record_id, wrap=False):
        """ Give the external ID for an odoo ID

        :param record_id: odoo ID for which we want the external id
                          or a recordset with one record
        :param wrap: if False, record_id is the ID of the binding,
            if True, record_id is the ID of the normal record, the
            method will search the corresponding binding and returns
            the backend id of the binding
        :return: backend identifier of the record
        """
        record = self.model.browse()
        if isinstance(record_id, odoo.models.BaseModel):
            record_id.ensure_one()
            record = record_id
            record_id = record_id.id
        if wrap:
            binding = self.model.with_context(active_test=False).search(
                [('erp_id', '=', record_id),
                 ('backend_id', '=', self.backend_record.id),
                 ]
            )
            if binding:
                binding.ensure_one()
                return binding.magento_id
            else:
                return None
        if not record:
            record = self.model.browse(record_id)
        assert record
        return record.magento_id

    def bind(self, external_id, binding_id):
        """ Create the link between an external ID and an odoo ID and
        update the last synchronization date.

        :param external_id: External ID to bind
        :param binding_id: odoo ID to bind
        :type binding_id: int
        """
        # the external ID can be 0 on Magento! Prevent False values
        # like False, None, or "", but not 0.
        assert (external_id or external_id == 0) and binding_id, (
            "external_id or binding_id missing, "
            "got: %s, %s" % (external_id, binding_id)
        )
        # avoid to trigger the export when we modify the `magento_id`
        now_fmt = odoo.fields.Datetime.now()
        if not isinstance(binding_id, odoo.models.BaseModel):
            binding_id = self.model.browse(binding_id)
        binding_id.write(
            {'magento_id': str(external_id),
             'sync_date': now_fmt,
             })

    def unwrap_binding(self, binding_id, browse=False):
        """ For a binding record, gives the normal record.

        Example: when called with a ``magento.product.product`` id,
        it will return the corresponding ``product.product`` id.

        :param browse: when True, returns a browse_record instance
                       rather than an ID
        """
        if isinstance(binding_id, odoo.models.BaseModel):
            binding = binding_id
        else:
            binding = self.model.browse(binding_id)

        openerp_record = binding.erp_id
        if browse:
            return openerp_record
        return openerp_record.id

    def unwrap_model(self):
        """ For a binding model, gives the name of the normal model.

        Example: when called on a binder for ``magento.product.product``,
        it will return ``product.product``.

        This binder assumes that the normal model lays in ``erp_id`` since
        this is the field we use in the ``_inherits`` bindings.
        """
        try:
            column = self.model._fields['erp_id']
        except KeyError:
            raise ValueError('Cannot unwrap model %s, because it has '
                             'no erp_id field' % self.model._name)
        return column.comodel_name
