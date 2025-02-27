# From from pytmlr

import os.path as osp, os
import pickle
import time
from os import remove
from pathlib import Path
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func, asc, desc, and_, extract, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from livermore import livermore_root
from livermore.misc import get_ny_time, get_readable_time


Base = declarative_base()
db_string_len = 128

class StockCandle(Base):
    __tablename__ = 'stock_candles'
    uuid = Column(String(db_string_len), primary_key=True)
    symbol = Column(String(20), nullable=False)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    timestamp = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    candle_type = Column(String(10), nullable=False)


DATABASE = livermore_root / "data" / "database"


class StockCandleDatabase:
    def __init__(self, database_name, database_folder=None, delete_old=False):
        super(StockCandleDatabase, self).__init__()
        if database_folder is None:
            database_folder = DATABASE
        os.makedirs(database_folder, exist_ok=True)
        database_path = database_folder / f"{database_name}.db"
        if delete_old:
            if osp.exists(database_path):
                print(f"Delete {database_name} database.")
                try:
                    remove(database_path)
                except OSError:
                    pass
        # engine = create_engine(f"sqlite:///{database_path}")
        # print(f"{database_name} database is stored at {database_path}")
        # engine = create_engine("postgresql://stock_candle:123456@localhost/stock_candle")
        engine = create_engine(f"duckdb:///{database_path}")
        Base.metadata.create_all(engine)
        Base.metadata.bind = engine
        self.session_maker = sessionmaker(bind=engine)

    def query_candles(self, symbol, start_time=None, end_time=None, candle_type="1m"):
        session = self.session_maker()
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = int(time.time() + 3600)
        try:
            candles = session.query(StockCandle).filter(
                StockCandle.symbol == symbol,
                StockCandle.candle_type == candle_type,
                StockCandle.timestamp >= start_time,
                StockCandle.timestamp <= end_time,
            ).order_by(asc(StockCandle.timestamp)).all()
            session.close()
            return candles
        except Exception as e:
            print(f"An error occurred while querying: {e}")
            return []
        finally:
            session.close()
    
    def query_the_latest_candle(self, symbol, num=100, candle_type="1m", market_time_only=True, last_time=None):
        MARKET_OPEN = dt_time(9, 30)
        MARKET_CLOSE = dt_time(16, 0)
        session = self.session_maker()
        
        # def in_ny_market_hours():
        #     ny_time = func.timezone("America/New_York", StockCandle.date)
        #     return and_(
        #         ny_time >= func.date_trunc("day", ny_time) + func.make_date(0, 9, 30),  # 9:30 AM
        #         ny_time < func.date_trunc("day", ny_time) + func.make_date(0, 16, 0),   # 4:00 PM
        #         extract("dow", ny_time).in_([1, 2, 3, 4, 5])  # Monday - Friday
        #     )
        ny_timezone = ZoneInfo('America/New_York')
        # ny_datetime = utc_datetime.astimezone(ny_timezone)
        
        try:
            if last_time is None:
                candles = session.query(StockCandle).filter(
                    StockCandle.symbol == symbol,
                    StockCandle.candle_type == candle_type,
                ).order_by(desc(StockCandle.timestamp))
            else:
                candles = session.query(StockCandle).filter(
                    StockCandle.symbol == symbol,
                    StockCandle.candle_type == candle_type,
                    StockCandle.timestamp <= last_time
                ).order_by(desc(StockCandle.timestamp))
            if num is not None:
                candles = candles.limit(num * 2)
                candles = candles.all()[:num]
            candles = candles[::-1]
            if market_time_only:
                candles = [candle for candle in candles if MARKET_OPEN <= get_ny_time(candle.timestamp).time() <= MARKET_CLOSE]
            session.close()
            return candles
        except Exception as e:
            print(f"An error occurred while querying the latest candle: {e}")
            return None
        finally:
            session.close()
    
    def get_min_max_timestamp(self, symbol, candle_type="1m"):
        session = self.session_maker()
        try:
            timestamp = session.query(func.min(StockCandle.timestamp), func.max(StockCandle.timestamp)).filter(
                StockCandle.symbol == symbol,
                StockCandle.candle_type == candle_type
            ).first()
            session.close()
            return timestamp
        except Exception as e:
            print(f"An error occurred while getting min/max timestamps: {e}")
            return None, None
        finally:
            session.close()
        
    def update_multiple_candles(self, symbol, candles, candle_type="1m"):
        if "t" not in candles or len(candles["t"]) == 0:
            return
        # candles is a dict of lists with keys: "t", "o", "h", "l", "c", "v"
        # st = time.time()
        timestamp_ranges = self.get_min_max_timestamp(symbol, candle_type)
        # print(time.time() - st)
        
        min_ts, max_ts = timestamp_ranges
        session = self.session_maker()
        
        candles.pop("s", None)
        indices = sorted(range(len(candles["t"])), key=lambda i: candles["t"][i])
        candles = {k: [candles[k][i] for i in indices] for k in candles}
        try:
            count = 0
            st_time, end_time = candles["t"][0], candles["t"][-1]
            for i in range(len(candles["t"])):
                if min_ts and max_ts and min_ts <= candles['t'][i] <= max_ts:
                    continue
                count += 1
                new_candle = StockCandle(
                    uuid=f"{symbol}-{candle_type}-{candles['t'][i]}",
                    symbol=symbol,
                    open_price=candles["o"][i],
                    high_price=candles["h"][i],
                    low_price=candles["l"][i],
                    close_price=candles["c"][i],
                    volume=candles["v"][i],
                    timestamp=int(candles["t"][i]),
                    date=get_ny_time(candles["t"][i]),
                    candle_type=candle_type
                )
                session.add(new_candle)
            session.commit()
            if count > 0:
                st_time = get_readable_time(st_time)
                end_time = get_readable_time(end_time)
                print(f"{count}/{len(candles['t'])} {candle_type} candles of {symbol} from {st_time} to {end_time} inserted successfully.")
        except Exception as e:
            session.rollback()
            print(f"An error occurred while updating multiple candles: {e}")
        session.close()

    def delete_candles(self, symbol=None, candle_type="30m"):
        session = self.session_maker()
        try:
            if symbol is None:
                candles_to_delete = session.query(StockCandle).filter(
                    StockCandle.candle_type == candle_type
                )
            else:
                candles_to_delete = session.query(StockCandle).filter(
                    StockCandle.symbol == symbol,
                    StockCandle.candle_type == candle_type
                )
            num_deleted = candles_to_delete.delete()
            session.commit()
            print(f"Successfully deleted {num_deleted} candles for {symbol} with candle type {candle_type}.")
        except Exception as e:
            session.rollback()
            print(f"An error occurred while deleting candles: {e}")
        session.close()

stock_candle_db = StockCandleDatabase("stock_candles")
