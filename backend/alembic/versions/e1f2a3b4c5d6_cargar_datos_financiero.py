"""cargar datos reales de compras, cheques y deuda financiera (financiero)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-15T22:00:00.000000

"""
import datetime
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROVEEDORES = [
    {'nombre': 'MC CAIN ARGENTINA SA', 'plazo_dias': 28, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'BOGS S.A.', 'plazo_dias': 14, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'ACEITERA GENERAL DEHEZA S A', 'plazo_dias': 14, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'NIZA S.A.', 'plazo_dias': 21, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'TREMBLAY S.R.L', 'plazo_dias': 28, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'ICEDREAM SRL', 'plazo_dias': 14, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'MOLINO CAÑUELAS SOCIEDAD ANONI', 'plazo_dias': 28, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'DORADA SA', 'plazo_dias': 14, 'forma_pago_habitual': 'cta_cte', 'confirmado': True},
    {'nombre': 'QUICKFOOD SA', 'plazo_dias': None, 'forma_pago_habitual': 'cheque', 'confirmado': True},
    {'nombre': 'FRONERI ARG. SA', 'plazo_dias': None, 'forma_pago_habitual': 'cta_cte', 'confirmado': False},
]

COMPRAS = [
    {'fecha_compra': datetime.date(2026, 8, 1), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'FCA450000036735', 'monto': 12950273.0, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 1)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500101339', 'monto': 14517953.06, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152956', 'monto': 1997583.82, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152957', 'monto': 31480307.35, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152958', 'monto': 2502378.63, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152959', 'monto': 26470862.2, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152960', 'monto': 4098364.2, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152961', 'monto': 17847414.26, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 3), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800152962', 'monto': 11743753.28, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 3)},
    {'fecha_compra': datetime.date(2026, 8, 5), 'proveedor_nombre': 'DORADA SA', 'comprobante_numero': 'FCA100000000111', 'monto': 5764399.34, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 5)},
    {'fecha_compra': datetime.date(2026, 8, 5), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'NRA000500053909', 'monto': -1750129.07, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 5)},
    {'fecha_compra': datetime.date(2026, 8, 7), 'proveedor_nombre': 'TREMBLAY S.R.L', 'comprobante_numero': 'FCA001700084380', 'monto': 961065.5, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 7)},
    {'fecha_compra': datetime.date(2026, 8, 9), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'FCA450000036809', 'monto': 19469009.900000002, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 9)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500101603', 'monto': 11294342.03, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500101604', 'monto': 8239979.350000001, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153322', 'monto': 17996536.27, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153323', 'monto': 5950750.350000001, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153324', 'monto': 21131889.98, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153325', 'monto': 8979684.46, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 10), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153326', 'monto': 32848156.28, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 10)},
    {'fecha_compra': datetime.date(2026, 8, 11), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000177', 'monto': 6117648.850000001, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 11)},
    {'fecha_compra': datetime.date(2026, 8, 11), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000188', 'monto': 692930.1900000001, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 11)},
    {'fecha_compra': datetime.date(2026, 8, 11), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NRA450000021057', 'monto': -13317182.67, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 11)},
    {'fecha_compra': datetime.date(2026, 8, 11), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NRA450000021058', 'monto': -19176408.46, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 11)},
    {'fecha_compra': datetime.date(2026, 8, 13), 'proveedor_nombre': 'DORADA SA', 'comprobante_numero': 'FCA200000000132', 'monto': 3664986.34, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 13)},
    {'fecha_compra': datetime.date(2026, 8, 13), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'NRA000500054127', 'monto': -2443448.58, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 13)},
    {'fecha_compra': datetime.date(2026, 8, 14), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA301400001571', 'monto': 11794255.39, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 14)},
    {'fecha_compra': datetime.date(2026, 8, 15), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'NRA620600000261', 'monto': -2453644.49, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 15)},
    {'fecha_compra': datetime.date(2026, 8, 17), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'FCA450000036903', 'monto': 31708630.830000002, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 17)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500101896', 'monto': 9712793.22, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500101897', 'monto': 5249402.0, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153810', 'monto': 14308266.450000001, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153811', 'monto': 14083624.22, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153812', 'monto': 15822967.88, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153813', 'monto': 6817927.09, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153814', 'monto': 16504607.46, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800153815', 'monto': 4012280.04, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 18), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA301400001624', 'monto': 2732944.81, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 18)},
    {'fecha_compra': datetime.date(2026, 8, 19), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'NRA300800018795', 'monto': -3726.4500000000003, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 19)},
    {'fecha_compra': datetime.date(2026, 8, 20), 'proveedor_nombre': 'MOLINO CAÑUELAS SOCIEDAD ANONI', 'comprobante_numero': 'FCA128800007270', 'monto': 1129674.72, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 20)},
    {'fecha_compra': datetime.date(2026, 8, 20), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'NRA000500054329', 'monto': -1990986.58, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 20)},
    {'fecha_compra': datetime.date(2026, 8, 21), 'proveedor_nombre': 'FRONERI ARG. SA', 'comprobante_numero': 'FCA000100146112', 'monto': 6229841.11, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 21)},
    {'fecha_compra': datetime.date(2026, 8, 22), 'proveedor_nombre': 'ICEDREAM SRL', 'comprobante_numero': 'FCA000301013234', 'monto': 1632956.71, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 22)},
    {'fecha_compra': datetime.date(2026, 8, 23), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'FCA450000036993', 'monto': 31096914.57, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 23)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500102122', 'monto': 9698635.15, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500102123', 'monto': 8498299.74, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154180', 'monto': 14660158.56, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154181', 'monto': 1876783.98, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154182', 'monto': 10887931.88, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154183', 'monto': 22580075.81, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154184', 'monto': 10623386.33, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154185', 'monto': 11565555.22, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154186', 'monto': 6581250.0, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154187', 'monto': 3013473.29, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154188', 'monto': 3071135.1099999994, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 24), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154189', 'monto': 2310965.85, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 24)},
    {'fecha_compra': datetime.date(2026, 8, 25), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000240', 'monto': 6180952.05, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 25)},
    {'fecha_compra': datetime.date(2026, 8, 27), 'proveedor_nombre': 'FRONERI ARG. SA', 'comprobante_numero': 'NRA000100038442', 'monto': -213585.85, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 27)},
    {'fecha_compra': datetime.date(2026, 8, 28), 'proveedor_nombre': 'TREMBLAY S.R.L', 'comprobante_numero': 'FCA000700143360', 'monto': 3293966.71, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 28)},
    {'fecha_compra': datetime.date(2026, 8, 28), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000249', 'monto': 3642537.08, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 28)},
    {'fecha_compra': datetime.date(2026, 8, 29), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'NRA620600000315', 'monto': -3737582.74, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 29)},
    {'fecha_compra': datetime.date(2026, 8, 30), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'FCA450000037120', 'monto': 16498745.39, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 30)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500102409', 'monto': 5463801.94, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500102411', 'monto': 7659618.29, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154587', 'monto': 25108778.080000002, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154588', 'monto': 7349706.65, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154589', 'monto': 31331665.32, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154590', 'monto': 7491128.55, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154591', 'monto': 1532057.68, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154592', 'monto': 6581250.0, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154593', 'monto': 4779454.68, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154594', 'monto': 15244239.41, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154595', 'monto': 6581250.0, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154596', 'monto': 1959248.27, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000255', 'monto': 6916949.140000001, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'ACEITERA GENERAL DEHEZA S A', 'comprobante_numero': 'FCA722000000159', 'monto': 7152573.59, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'NRA000500054691', 'monto': -2301207.43, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'NRA000500054692', 'monto': -1783028.74, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'NRA000500054817', 'monto': -2353366.93, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'NRA300500000227', 'monto': -31436.9, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'NRA300500000228', 'monto': -297643.46, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'NRA301400008609', 'monto': -30391989.740000002, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'NRA301400008627', 'monto': -2123359.2600000002, 'forma_pago': 'cheque', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'NRA620600000326', 'monto': -2331779.44, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 8, 31), 'proveedor_nombre': 'ACEITERA GENERAL DEHEZA S A', 'comprobante_numero': 'NRA720600000242', 'monto': -1037123.18, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 31)},
    {'fecha_compra': datetime.date(2026, 9, 3), 'proveedor_nombre': 'DORADA SA', 'comprobante_numero': 'FCA100000000459', 'monto': 5252305.55, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 3), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NRA450000021285', 'monto': -35634.26, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 5), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'FCA450000037186', 'monto': 18258539.41, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500102632', 'monto': 9457727.89, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'BOGS S.A.', 'comprobante_numero': 'FCA000500102633', 'monto': 8516857.95, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'DORADA SA', 'comprobante_numero': 'FCA200000000377', 'monto': 5737876.8, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'DORADA SA', 'comprobante_numero': 'FCA200000000378', 'monto': 2111661.56, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154863', 'monto': 5509764.99, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154864', 'monto': 6063920.5, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154865', 'monto': 27637156.96, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154866', 'monto': 8783500.34, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154867', 'monto': 19722813.06, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154868', 'monto': 553653.03, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 7), 'proveedor_nombre': 'QUICKFOOD SA', 'comprobante_numero': 'FCA300800154869', 'monto': 6581250.0, 'forma_pago': 'cheque', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 8), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000298', 'monto': 1094662.54, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 8), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'FCA621700000299', 'monto': 729775.03, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 8), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NRA450000021372', 'monto': -10907280.66, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 8), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NRA450000021373', 'monto': -15391850.38, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 9), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NRA450000021471', 'monto': -2512821.72, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 9, 12), 'proveedor_nombre': 'NIZA S.A.', 'comprobante_numero': 'NRA620600000372', 'monto': -770277.54, 'forma_pago': 'cta_cte', 'fecha_pago_real': None},
    {'fecha_compra': datetime.date(2026, 8, 9), 'proveedor_nombre': 'MC CAIN ARGENTINA SA', 'comprobante_numero': 'NC ajuste deuda financiera', 'monto': -29000000.0, 'forma_pago': 'cta_cte', 'fecha_pago_real': datetime.date(2026, 8, 9)},
]

CHEQUES = [
    {'numero': '06965247', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 14811135.37, 'fecha_pago': datetime.date(2026, 9, 23), 'estado': 'pendiente'},
    {'numero': '06965248', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 15762846.45, 'fecha_pago': datetime.date(2026, 9, 23), 'estado': 'pendiente'},
    {'numero': '14451553', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 19417897.2, 'fecha_pago': datetime.date(2026, 9, 30), 'estado': 'pendiente'},
    {'numero': '14451552', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 2272045.6, 'fecha_pago': datetime.date(2026, 9, 30), 'estado': 'pendiente'},
    {'numero': '14451551', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 8742317.88, 'fecha_pago': datetime.date(2026, 9, 30), 'estado': 'pendiente'},
    {'numero': '14451557', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 11199717.75, 'fecha_pago': datetime.date(2026, 10, 7), 'estado': 'pendiente'},
    {'numero': '14451556', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 31501548.65, 'fecha_pago': datetime.date(2026, 9, 23), 'estado': 'pendiente'},
    {'numero': '14451559', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 6600000.0, 'fecha_pago': datetime.date(2026, 10, 7), 'estado': 'pendiente'},
    {'numero': '14451558', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 859834.3, 'fecha_pago': datetime.date(2026, 10, 7), 'estado': 'pendiente'},
    {'numero': '14451560', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 24690958.18, 'fecha_pago': datetime.date(2026, 9, 23), 'estado': 'pendiente'},
    {'numero': '14451555', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 42915380.3, 'fecha_pago': datetime.date(2026, 9, 23), 'estado': 'anulado'},
    {'numero': '14451562', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 19243608.45, 'fecha_pago': datetime.date(2026, 10, 14), 'estado': 'pendiente'},
    {'numero': '14451565', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 35309433.25, 'fecha_pago': datetime.date(2026, 9, 30), 'estado': 'pendiente'},
    {'numero': '14451564', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 2203973.85, 'fecha_pago': datetime.date(2026, 10, 14), 'estado': 'pendiente'},
    {'numero': '14451563', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 53503074.95, 'fecha_pago': datetime.date(2026, 9, 30), 'estado': 'pendiente'},
    {'numero': '14451561', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 19179728.75, 'fecha_pago': datetime.date(2026, 10, 14), 'estado': 'pendiente'},
    {'numero': '06965229', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 26266506.6, 'fecha_pago': datetime.date(2026, 8, 11), 'estado': 'pagado'},
    {'numero': '06965230', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 10622315.79, 'fecha_pago': datetime.date(2026, 8, 11), 'estado': 'pagado'},
    {'numero': '06965242', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 12081396.45, 'fecha_pago': datetime.date(2026, 9, 15), 'estado': 'pendiente'},
    {'numero': '06965225', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 118382538.54, 'fecha_pago': datetime.date(2026, 8, 14), 'estado': 'pagado'},
    {'numero': '06965235', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 45468099.91, 'fecha_pago': datetime.date(2026, 8, 18), 'estado': 'pagado'},
    {'numero': '06965228', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 10402236.0, 'fecha_pago': datetime.date(2026, 8, 19), 'estado': 'pagado'},
    {'numero': '06965232', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 30335829.0, 'fecha_pago': datetime.date(2026, 8, 19), 'estado': 'pagado'},
    {'numero': '06965239', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 35205905.02, 'fecha_pago': datetime.date(2026, 8, 25), 'estado': 'pagado'},
    {'numero': '06965240', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 21131889.42, 'fecha_pago': datetime.date(2026, 8, 25), 'estado': 'pagado'},
    {'numero': '06965233', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 6600742.83, 'fecha_pago': datetime.date(2026, 9, 1), 'estado': 'pagado'},
    {'numero': '06965244', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 67675755.93, 'fecha_pago': datetime.date(2026, 9, 1), 'estado': 'pagado'},
    {'numero': '14451554', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 39550944.62, 'fecha_pago': datetime.date(2026, 9, 16), 'estado': 'pendiente'},
    {'numero': '06965236', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 19750068.0, 'fecha_pago': datetime.date(2026, 9, 8), 'estado': 'pagado'},
    {'numero': '06965237', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 6583356.0, 'fecha_pago': datetime.date(2026, 9, 8), 'estado': 'pagado'},
    {'numero': '06965238', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 8979684.46, 'fecha_pago': datetime.date(2026, 9, 8), 'estado': 'pagado'},
    {'numero': '06965246', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 59798495.78, 'fecha_pago': datetime.date(2026, 9, 9), 'estado': 'pagado'},
    {'numero': '06965227', 'proveedor_nombre': 'QUICKFOOD SA', 'monto': 47975674.97, 'fecha_pago': datetime.date(2026, 8, 5), 'estado': 'pagado'},
]

CUOTAS_BANCARIAS = [
    {'banco': 'ICBC', 'nro_cuota': '5/24', 'monto': 16485314.93, 'fecha_vencimiento': datetime.date(2026, 8, 20)},
    {'banco': 'Supervielle', 'nro_cuota': '11/12', 'monto': 14717423.68, 'fecha_vencimiento': datetime.date(2026, 8, 20)},
    {'banco': 'Supervielle', 'nro_cuota': '8/12', 'monto': 9022000.0, 'fecha_vencimiento': datetime.date(2026, 8, 20)},
    {'banco': 'Supervielle', 'nro_cuota': '7/36', 'monto': 12847648.0, 'fecha_vencimiento': datetime.date(2026, 8, 20)},
    {'banco': 'ICBC', 'nro_cuota': '8/24', 'monto': 4838326.43, 'fecha_vencimiento': datetime.date(2026, 8, 26)},
    {'banco': 'Santander', 'nro_cuota': '8/12', 'monto': 4150000.0, 'fecha_vencimiento': datetime.date(2026, 8, 29)},
    {'banco': 'ICBC', 'nro_cuota': '6/24', 'monto': 16485314.93, 'fecha_vencimiento': datetime.date(2026, 9, 20)},
    {'banco': 'Supervielle', 'nro_cuota': '12/12', 'monto': 14717423.68, 'fecha_vencimiento': datetime.date(2026, 9, 20)},
    {'banco': 'Supervielle', 'nro_cuota': '9/12', 'monto': 9022000.0, 'fecha_vencimiento': datetime.date(2026, 9, 20)},
    {'banco': 'Supervielle', 'nro_cuota': '8/36', 'monto': 12847648.0, 'fecha_vencimiento': datetime.date(2026, 9, 20)},
    {'banco': 'ICBC', 'nro_cuota': '9/24', 'monto': 4838326.43, 'fecha_vencimiento': datetime.date(2026, 9, 26)},
    {'banco': 'Santander', 'nro_cuota': '9/12', 'monto': 4150000.0, 'fecha_vencimiento': datetime.date(2026, 9, 29)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '1/12', 'monto': 25904080.0, 'fecha_vencimiento': datetime.date(2026, 8, 18)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '2/12', 'monto': 24440800.0, 'fecha_vencimiento': datetime.date(2026, 9, 17)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '3/12', 'monto': 24253200.0, 'fecha_vencimiento': datetime.date(2026, 10, 19)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '4/12', 'monto': 22977520.0, 'fecha_vencimiento': datetime.date(2026, 11, 16)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '5/12', 'monto': 22752400.0, 'fecha_vencimiento': datetime.date(2026, 12, 16)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '6/12', 'monto': 22189600.0, 'fecha_vencimiento': datetime.date(2027, 1, 15)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '7/12', 'monto': 21739360.0, 'fecha_vencimiento': datetime.date(2027, 2, 15)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '8/12', 'monto': 20970200.0, 'fecha_vencimiento': datetime.date(2027, 3, 16)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '9/12', 'monto': 20501200.0, 'fecha_vencimiento': datetime.date(2027, 4, 15)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '10/12', 'monto': 20050960.0, 'fecha_vencimiento': datetime.date(2027, 5, 17)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '11/12', 'monto': 19300560.0, 'fecha_vencimiento': datetime.date(2027, 6, 14)},
    {'banco': 'Banco Nacion - Prestamo 40413964-00 (Agente Fciero C/T)', 'nro_cuota': '12/12', 'monto': 18812800.0, 'fecha_vencimiento': datetime.date(2027, 7, 14)},
]

CREDITO_TOTAL_DISPONIBLE = 181250837.0


def upgrade() -> None:
    conn = op.get_bind()

    financiero_proveedores = sa.table(
        'financiero_proveedores',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('nombre', sa.String),
        sa.column('plazo_dias', sa.Integer),
        sa.column('forma_pago_habitual', sa.String),
        sa.column('confirmado', sa.Boolean),
    )
    financiero_compras = sa.table(
        'financiero_compras',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('fecha_compra', sa.Date),
        sa.column('proveedor_nombre', sa.String),
        sa.column('comprobante_numero', sa.String),
        sa.column('monto', sa.Numeric),
        sa.column('forma_pago', sa.String),
        sa.column('fecha_pago_real', sa.Date),
    )
    financiero_cheques = sa.table(
        'financiero_cheques',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('numero', sa.String),
        sa.column('proveedor_nombre', sa.String),
        sa.column('monto', sa.Numeric),
        sa.column('fecha_pago', sa.Date),
        sa.column('estado', sa.String),
    )
    financiero_cuotas_bancarias = sa.table(
        'financiero_cuotas_bancarias',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('banco', sa.String),
        sa.column('nro_cuota', sa.String),
        sa.column('monto', sa.Numeric),
        sa.column('fecha_vencimiento', sa.Date),
    )

    op.bulk_insert(
        financiero_proveedores,
        [{**p, "id": uuid.uuid4()} for p in PROVEEDORES],
    )
    op.bulk_insert(
        financiero_compras,
        [{**c, "id": uuid.uuid4()} for c in COMPRAS],
    )
    op.bulk_insert(
        financiero_cheques,
        [{**c, "id": uuid.uuid4()} for c in CHEQUES],
    )
    op.bulk_insert(
        financiero_cuotas_bancarias,
        [{**c, "id": uuid.uuid4()} for c in CUOTAS_BANCARIAS],
    )

    # Línea de Crédito Nación disponible (el "colchón" que usa el motor de
    # cashflow) -- upsert sobre el singleton de parámetros.
    existe = conn.execute(sa.text("SELECT id FROM financiero_parametros LIMIT 1")).scalar_one_or_none()
    if existe is None:
        conn.execute(
            sa.text(
                "INSERT INTO financiero_parametros (id, credito_total_disponible) "
                "VALUES (:id, :credito)"
            ),
            {"id": uuid.uuid4(), "credito": CREDITO_TOTAL_DISPONIBLE},
        )
    else:
        conn.execute(
            sa.text("UPDATE financiero_parametros SET credito_total_disponible = :credito WHERE id = :id"),
            {"id": existe, "credito": CREDITO_TOTAL_DISPONIBLE},
        )


def downgrade() -> None:
    conn = op.get_bind()
    # Comparar montos redondeados a 2 decimales: la columna es NUMERIC(14,2)
    # y algunos montos parseados desde los .xls traen ruido de punto
    # flotante (ej. 8239979.350000001) que no matchea igual sin redondeo.
    for c in COMPRAS:
        conn.execute(
            sa.text(
                "DELETE FROM financiero_compras WHERE fecha_compra = :fecha_compra "
                "AND proveedor_nombre = :proveedor_nombre AND comprobante_numero IS NOT DISTINCT FROM :comprobante_numero "
                "AND round(monto, 2) = round(CAST(:monto AS numeric), 2)"
            ),
            {
                "fecha_compra": c["fecha_compra"],
                "proveedor_nombre": c["proveedor_nombre"],
                "comprobante_numero": c["comprobante_numero"],
                "monto": c["monto"],
            },
        )
    for c in CHEQUES:
        conn.execute(
            sa.text(
                "DELETE FROM financiero_cheques WHERE numero IS NOT DISTINCT FROM :numero "
                "AND fecha_pago = :fecha_pago AND round(monto, 2) = round(CAST(:monto AS numeric), 2)"
            ),
            {"numero": c["numero"], "fecha_pago": c["fecha_pago"], "monto": c["monto"]},
        )
    for c in CUOTAS_BANCARIAS:
        conn.execute(
            sa.text(
                "DELETE FROM financiero_cuotas_bancarias WHERE banco = :banco "
                "AND nro_cuota IS NOT DISTINCT FROM :nro_cuota AND fecha_vencimiento = :fecha_vencimiento "
                "AND round(monto, 2) = round(CAST(:monto AS numeric), 2)"
            ),
            {
                "banco": c["banco"],
                "nro_cuota": c["nro_cuota"],
                "fecha_vencimiento": c["fecha_vencimiento"],
                "monto": c["monto"],
            },
        )
    conn.execute(
        sa.text("DELETE FROM financiero_proveedores WHERE nombre = ANY(:nombres)"),
        {"nombres": [p["nombre"] for p in PROVEEDORES]},
    )
