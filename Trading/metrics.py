def ref(arr, i, n=1):
    """
    模拟 REF(X, n) - 取序列 X 往前 n 根的数据。
    arr: 已计算好的某个序列(list)
    i:   当前正在计算到的 bar 的下标
    n:   往前多少根
    """
    if i - n < 0:
        return None
    else:
        return arr[i - n]

def barslast(condition_arr, i):
    """
    模拟 BARSLAST(cond) - 从当前 i 往前追溯，
    找到最近一次 cond=True 的位置距离。
    若没找到，就返回一个较大数(表示相隔很远)。
    """
    for dist in range(0, i+1):
        idx = i - dist
        if idx < 0:
            break
        if condition_arr[idx]:
            return dist
    return i + 1  # 如果从没找到满足 cond 的，就返回 i+1

def llv(values, i, length):
    """
    模拟 LLV(X,N) - 最近 N 根(含当前i)内, X 的最小值。
    如果 i 不够长，就只在 0~i 范围计算。
    """
    start = max(0, i - length + 1)
    return min(values[start : i+1])

def hhv(values, i, length):
    """ 模拟 HHV(X,N) - 最近 N 根内的最大值 """
    start = max(0, i - length + 1)
    return max(values[start : i+1])

def count(condition_arr, i, length):
    """
    模拟 COUNT(cond, N) - 最近 N 根内, cond=True 的次数
    """
    start = max(0, i - length + 1)
    return sum(condition_arr[start : i+1])



def ema_calc(values, period):
    """
    计算一条序列 values 的 period 周期 EMA，返回一个等长列表
    """
    alpha = 2.0 / (period + 1.0)
    ema_list = []
    for i, price in enumerate(values):
        if i == 0:
            # 初始化：第一个值可以直接使用 price
            ema_list.append(price)
        else:
            ema_list.append(alpha * price + (1 - alpha) * ema_list[i - 1])
    return ema_list

def compute_macd(close_list, s=12, p=26, m=9):
    short_ema = ema_calc(close_list, s)
    long_ema  = ema_calc(close_list, p)
    diff = [s_ - l_ for (s_, l_) in zip(short_ema, long_ema)]
    dea  = ema_calc(diff, m)
    macd = [2*(d_ - e_) for (d_, e_) in zip(diff, dea)]
    return diff, dea, macd



def calc_buy_sell_signals(kline_data, s=12, p=26, m=9):
    """
    传入K线数据 (至少要包含收盘价),
    逐条计算脚本中的所有逻辑，并在满足条件时记录 BUY / SELL 信号。

    返回值:
      signals: 一个列表, [(index, 'BUY'), (index, 'SELL'), ...]
               表示在第几根 K线上出现买卖信号
    """
    # === 1. 提取收盘价 ===
    close_list = [k[1] for k in kline_data]  # 假定 k[1] 是收盘价

    length = len(close_list)
    if length == 0:
        return []

    # === 2. 先计算 MACD 相关 ===
    diff, dea, macd = compute_macd(close_list, s, p, m)

    # === 3. 需要的中间布尔条件(翻红翻绿) ===
    cond_flip_to_neg = [False]*length  # (REF(MACD,1) >= 0) AND (MACD < 0)
    cond_flip_to_pos = [False]*length  # (REF(MACD,1) <= 0) AND (MACD > 0)

    for i in range(length):
        prev_macd = ref(macd, i, 1)
        curr_macd = macd[i]
        if prev_macd is not None:
            if (prev_macd >= 0) and (curr_macd < 0):
                cond_flip_to_neg[i] = True
            if (prev_macd <= 0) and (curr_macd > 0):
                cond_flip_to_pos[i] = True

    # === 4. 准备存储脚本里的所有变量 ===
    N1_array = [0]*length  # BARSLAST( cond_flip_to_neg )
    MM1_array = [0]*length # BARSLAST( cond_flip_to_pos )

    # 以 AAA、BBB、CCC -> JJJ -> DXDX 这条“底背离买信号”为例
    AAA_array  = [False]*length
    BBB_array  = [False]*length
    CCC_array  = [False]*length
    JJJ_array  = [False]*length
    DXDX_array = [False]*length

    # 还要一系列 CC1, CC2, CC3, DIFL1, DIFL2, ... 也都得存:
    CC1_array = [0]*length
    CC2_array = [0]*length
    CC3_array = [0]*length
    DIFL1_array = [0]*length
    DIFL2_array = [0]*length
    DIFL3_array = [0]*length
    # ...依此类推，CH1, CH2, CH3, DIFH1, DIFH2, DIFH3, etc.

    # 同理, 对于顶背离卖信号: DBJG, DBJGXC, ...
    DBJG_array   = [False]*length
    DBJGXC_array = [False]*length
    # ...

    # === 5. 逐Bar计算脚本中每行公式 ===
    for i in range(length):

        # 5.1 N1 = BARSLAST( (REF(MACD,1)>=0) AND (MACD<0) )
        N1_array[i] = barslast(cond_flip_to_neg, i)

        #    MM1 = BARSLAST( (REF(MACD,1)<=0) AND (MACD>0) )
        MM1_array[i] = barslast(cond_flip_to_pos, i)

        # 5.2 CC1 = LLV(CLOSE, (N1 + 1))
        n1_val = N1_array[i]
        cc1 = llv(close_list, i, n1_val+1)
        CC1_array[i] = cc1

        #    CC2 = REF(CC1, (MM1 + 1))
        mm1_val = MM1_array[i]
        # 这里要注意: REF(CC1, (MM1+1)) 是往前 mm1_val+1 根去取 CC1 的值，
        # 但是 CC1 在每个 bar 都不一样, 所以我们需要 ref(CC1_array, i, mm1_val+1).
        cc2 = ref(CC1_array, i, mm1_val+1)
        CC2_array[i] = cc2 if cc2 is not None else 0

        #    CC3 = REF(CC2, (MM1+1))
        cc3 = ref(CC2_array, i, mm1_val+1)
        CC3_array[i] = cc3 if cc3 is not None else 0

        # 同理 DIFL1, DIFL2, DIFL3... 
        # DIFL1 = LLV(DIFF, (N1 + 1))
        difl1 = llv(diff, i, n1_val+1)
        DIFL1_array[i] = difl1

        # DIFL2 = REF(DIFL1, (MM1 + 1)) ...
        difl2 = ref(DIFL1_array, i, mm1_val+1)
        DIFL2_array[i] = difl2 if difl2 else 0

        # DIFL3 = REF(DIFL2, (MM1 + 1)) ...
        difl3 = ref(DIFL2_array, i, mm1_val+1)
        DIFL3_array[i] = difl3 if difl3 else 0

        # 5.3 AAA = ((CC1<CC2) AND ((DIFL1>DIFL2) AND ((REF(MACD,1)<0) AND (DIFF<0))))
        prev_macd_val = ref(macd, i, 1)
        if (prev_macd_val is not None):
            cond1 = (cc1 < cc2) if (cc2 is not None) else False
            cond2 = (difl1 > difl2) 
            cond3 = (prev_macd_val < 0) and (diff[i] < 0)
            AAA_array[i] = (cond1 and cond2 and cond3)

        # 5.4 BBB = ... (同理, 这里省略, 你要按脚本逐行翻译)

        # 5.5 CCC = (AAA OR BBB) AND (DIFF<0)
        CCC_array[i] = (AAA_array[i] or BBB_array[i]) and (diff[i] < 0)

        # 5.6 JJJ = (REF(CCC,1) AND (ABS(REF(DIFF,1)) >= (ABS(DIFF)*1.01)))
        #    需要REF(CCC,1) 以及 REF(DIFF,1)
        ccc_prev = ref(CCC_array, i, 1)
        diff_prev = ref(diff, i, 1)
        if (ccc_prev is not None) and (diff_prev is not None):
            cond_jjj = ccc_prev and (abs(diff_prev) >= abs(diff[i])*1.01)
            JJJ_array[i] = cond_jjj

        # 5.7 DXDX = ((REF(JJJ,1)=0) AND JJJ)
        jjj_prev = ref(JJJ_array, i, 1)
        if (jjj_prev is not None):
            # "REF(JJJ,1)=0" 在公式里表示上一根JJJ不为True
            # 这里可以理解为 jjj_prev == False
            DXDX_array[i] = ((not jjj_prev) and JJJ_array[i])

        # 5.x 同理, 计算脚本里顶部背离那部分( ZJDBL, GXDBL, DBBL, DBJG, DBJGXC ... )
        # 这里只示例 DBJGXC:
        # DBJGXC = (REF(NOT(DBJG),1) AND DBJG)
        dbjg_prev = ref(DBJG_array, i, 1)
        if dbjg_prev is not None:
            # REF(NOT(DBJG),1) <=> (dbjg_prev == False)
            # AND DBJG => DBJG_array[i] == True
            DBJGXC_array[i] = ((dbjg_prev == False) and DBJG_array[i])

    # === 6. 生成 BUY/SELL 信号列表 ===
    buy_signals = []
    sell_signals = []
    for i in range(length):
        # 若 DXDX_array[i] 为真 => BUY
        if DXDX_array[i]:
            buy_signals.append(1)
        else:
            buy_signals.append(0)
        # 若 DBJGXC_array[i] 为真 => SELL
        if DBJGXC_array[i]:
            sell_signals.append(1)
        else:
            sell_signals.append(0)

    return buy_signals, sell_signals



if __name__ == "__main__":
    kline_data_example = [
        # (open, close, high, low)
        (100.0, 101.0, 102.0, 99.0),
        (101.5, 102.2, 103.0, 100.5),
        (102.2, 101.7, 103.6, 101.0),
        (101.2, 103.5, 105.0, 100.8),
        (103.2, 102.8, 104.0, 102.0),
        (102.9, 103.1, 103.6, 101.2),
        (103.0, 102.0, 103.4, 101.5),
        (103.4, 120.5, 102.2, 103.4),
        (119, 139.8, 141.0, 118.5),
        (129, 150.1, 117.5, 153.0),
    ]

    signal1, signal2 = calc_buy_sell_signals(kline_data_example, s=12, p=26, m=9)

