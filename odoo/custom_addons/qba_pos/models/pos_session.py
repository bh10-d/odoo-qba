# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = "pos.session"

    def _load_pos_data_models(self, config_id):
        models_list = super()._load_pos_data_models(config_id)
        if "pos.custom.product.history" not in models_list:
            models_list.append("pos.custom.product.history")
        return models_list

