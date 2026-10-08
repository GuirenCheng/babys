# pip install pycrypto
# pip install alipay-sdk-python
# 买家账号：ltyavg2644@sandbox.com
# 登录和支付密码：111111



import logging
import os
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    filemode='a',)
logger = logging.getLogger('')


def _load_key(name):
    '''从环境变量读取密钥，\n 转义还原为真实换行'''
    v = os.environ.get(name, '')
    return v.replace('\\n', '\n') if v else ''


alipay_public_key_string = _load_key('ALIPAY_PUBLIC_KEY')
app_private_key_string = _load_key('ALIPAY_APP_PRIVATE_KEY')
alipay_client_config = AlipayClientConfig()
alipay_client_config.server_url = os.environ.get('ALIPAY_SERVER_URL', 'https://openapi.alipaydev.com/gateway.do')
alipay_client_config.app_id = os.environ.get('ALIPAY_APP_ID', '')
alipay_client_config.app_private_key = app_private_key_string
alipay_client_config.alipay_public_key = alipay_public_key_string
client = DefaultAlipayClient(alipay_client_config=alipay_client_config, logger=logger)


def get_pay(out_trade_no, total_amount, return_url):
    model = AlipayTradePagePayModel()
    model.out_trade_no = out_trade_no
    model.total_amount = str(total_amount)
    model.subject = "测试"
    model.body = "支付宝测试"
    model.product_code = "FAST_INSTANT_TRADE_PAY"

    request = AlipayTradePagePayRequest(biz_model=model)

    request.notify_url = return_url + '?t=' + out_trade_no
    request.return_url = return_url + '?t=' + out_trade_no
    response = client.page_execute(request, http_method="GET")
    return response
