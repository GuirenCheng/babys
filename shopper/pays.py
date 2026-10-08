# pip install pycryptodome
# pip install python-alipay-sdk

import os
from alipay import AliPay
import time


def _load_key(name):
    '''从环境变量读取密钥，\n 转义还原为真实换行'''
    v = os.environ.get(name, '')
    return v.replace('\\n', '\n') if v else ''


alipay_public_key_string = _load_key('ALIPAY_PUBLIC_KEY')
app_private_key_string = _load_key('ALIPAY_APP_PRIVATE_KEY')


def get_pay(out_trade_no, total_amount, return_url):
    # 实例化支付应用
    alipay = AliPay(
        appid=os.environ.get('ALIPAY_APP_ID', ''),
        app_notify_url=None,
        app_private_key_string=app_private_key_string,
        alipay_public_key_string=alipay_public_key_string,
        sign_type="RSA2"
    )
    # 发起支付请求
    order_string = alipay.api_alipay_trade_page_pay(
        # 订单号，每次发送请求都不能一样
        out_trade_no=out_trade_no,
        # 支付金额
        total_amount=str(total_amount),
        # 交易信息
        subject="测试",
        return_url=return_url + '?t=' + out_trade_no,
        notify_url=return_url + '?t=' + out_trade_no
    )
    return 'https://openapi.alipaydev.com/gateway.do?' + order_string
