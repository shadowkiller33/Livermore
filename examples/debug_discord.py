from mmengine import dump, load

from livermore.misc import get_readable_time, get_ny_time, time_to_seconds, get_last_time, process_database_results, plot_stock_candles, plot_multiple_stock_candles
from livermore.stock_candle_database import stock_candle_db
from livermore.signal_utils import compute_vegas_channel_and_signal
from livermore import livermore_root


def check_channel_ids():
    data = load(str(livermore_root / 'data/discord_channels.json'))
    content = """SEMI_CONDUCTOR=1333613478685970554
CRYPTO=1333613521891495998
BIG_TECH=1333613598450384987
AI_SOFTWARE=1333613642431594527
SPY_QQQ_IWM=1333613691110821888
FINANCE=1333613735604125737
BIO_MED=1333613812309557319
VOL=1333613896623198298
TLT_TMF=1333614021915574304
ENERGY=1333614121886683207
SPACE=1335393219491528736
ROBO=1335519046291947542
SOCIAL=1335519117079351337
DEFENSE=1335519181931679834
NUCLEAR=1335519259971031050
SMALL_AI=1335393054563237938
SHORT_EFT=1335393145739018240
FOOD=1333614367979077705
DRONE=1335519455475662848
SPORTS=1335519528355893258
FASHION=1335519593002958921
TRAVEL=1335519666705141840
AUTO_DRIVE=1335519725287112725
CN=1335519802265047161"""
    for key, item in data.items():
        print(key, item)
        assert f"{key}={item}" in content
