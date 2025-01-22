def safe_ref(arr, i, n=1):
    """
    Safe REF: returns arr[i-n] if in range, else 0.0
    """
    idx = i - n
    if idx < 0:
        return 0.0
    else:
        return arr[idx]

def barslast(cond_arr, i):
    """
    BARSLAST(cond):
      Returns the distance (in bars) from the current bar i
      to the most recent bar where cond_arr was True.
      If not found, return i+1 (i.e. a large number).
    """
    for dist in range(0, i+1):
        idx = i - dist
        if idx < 0:
            break
        if cond_arr[idx]:
            return dist
    return i + 1

def llv(values, i, length):
    """
    LLV(X, N):
      Minimum of X over the last N bars (including current i).
      If i < N, just use from 0..i.
    """
    start = max(0, i - length + 1)
    return min(values[start:i+1])

def hhv(values, i, length):
    """
    HHV(X, N):
      Maximum of X over the last N bars (including current i).
    """
    start = max(0, i - length + 1)
    return max(values[start:i+1])

def count(cond_arr, i, length):
    """
    COUNT(cond, N):
      Number of True in cond_arr over the last N bars (including i).
    """
    start = max(0, i - length + 1)
    return sum(cond_arr[start:i+1])

def ema_calc(values, period):
    """
    Standard EMA using period.
    """
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    ema_list = [values[0]]  # first value is just the price itself
    for i in range(1, len(values)):
        ema_list.append(alpha * values[i] + (1 - alpha) * ema_list[i - 1])
    return ema_list


def calc_buy_sell_signals(kline_data, s=12, p=26, m=9):
    """
    Translated version of your original script in Python.
    kline_data: list of bars, each bar is (open, close, high, low, ...)
    s, p, m: periods for MACD's short EMA, long EMA, and DEA EMA.
    
    Returns:
       buy_signals, sell_signals
       (Each is a list of the same length as kline_data, 
        containing 1 when a 'BUY'/'SELL' signal is triggered, else 0.)
    """
    # 1) Extract close prices
    close_list = [bar[1] for bar in kline_data]
    length = len(close_list)
    if length == 0:
        return [], []
    
    # 2) Compute MACD base lines: DIFF, DEA, MACD
    #    DIFF = EMA(close, s) - EMA(close, p)
    #    DEA  = EMA(DIFF, m)
    #    MACD = (DIFF - DEA)*2
    short_ema = ema_calc(close_list, s)
    long_ema  = ema_calc(close_list, p)
    DIFF_arr  = [s_ - l_ for s_, l_ in zip(short_ema, long_ema)]
    DEA_arr   = ema_calc(DIFF_arr, m)
    MACD_arr  = [ (d - e)*2 for d, e in zip(DIFF_arr, DEA_arr) ]
    
    # Prepare arrays for all lines in the script
    N1_arr    = [0]*length
    MM1_arr   = [0]*length
    CC1_arr   = [0]*length
    CC2_arr   = [0]*length
    CC3_arr   = [0]*length
    DIFL1_arr = [0]*length
    DIFL2_arr = [0]*length
    DIFL3_arr = [0]*length
    CH1_arr   = [0]*length
    CH2_arr   = [0]*length
    CH3_arr   = [0]*length
    DIFH1_arr = [0]*length
    DIFH2_arr = [0]*length
    DIFH3_arr = [0]*length
    
    # Boolean arrays for the conditions (AAA, BBB, etc.)
    AAA_arr   = [False]*length
    BBB_arr   = [False]*length
    CCC_arr   = [False]*length
    LLL_arr   = [False]*length
    XXX_arr   = [False]*length
    JJJ_arr   = [False]*length
    BLBL_arr  = [False]*length
    DXDX_arr  = [False]*length
    DJGXX_arr = [False]*length
    DJXX_arr  = [False]*length
    DXX_arr   = [False]*length
    
    ZJDBL_arr  = [False]*length
    GXDBL_arr  = [False]*length
    DBBL_arr   = [False]*length
    DBL_arr    = [False]*length
    DBLXS_arr  = [False]*length
    DBJG_arr   = [False]*length
    DBJGXC_arr = [False]*length
    DBJGBL_arr = [False]*length
    ZZZZZ_arr  = [False]*length
    YYYYY_arr  = [False]*length
    WWWWW_arr  = [False]*length
    
    # We may also create final signal arrays for BUY / SELL
    buy_signals  = [0]*length
    sell_signals = [0]*length
    
    # 3) We also need conditions for flipping MACD from >=0 to <0, etc.
    cond_flip_to_neg = [False]*length  # (REF(MACD,1)>=0 AND MACD<0)
    cond_flip_to_pos = [False]*length  # (REF(MACD,1)<=0 AND MACD>0)
    
    for i in range(length):
        macd_prev = safe_ref(MACD_arr, i, 1)
        macd_curr = MACD_arr[i]
        if macd_prev >= 0 and macd_curr < 0:
            cond_flip_to_neg[i] = True
        if macd_prev <= 0 and macd_curr > 0:
            cond_flip_to_pos[i] = True
    
    # 4) Main loop: compute each variable line by line
    for i in range(length):
        # N1 := BARSLAST(((REF(MACD,1) >= 0) AND (MACD < 0)));
        N1_arr[i] = barslast(cond_flip_to_neg, i)
        
        # MM1 := BARSLAST(((REF(MACD,1) <= 0) AND (MACD > 0)));
        MM1_arr[i] = barslast(cond_flip_to_pos, i)
        
        n1_val  = N1_arr[i]
        mm1_val = MM1_arr[i]
        
        # CC1 := LLV(CLOSE,(N1 + 1));
        CC1_arr[i] = llv(close_list, i, n1_val + 1)
        # CC2 := REF(CC1,(MM1 + 1));
        CC2_arr[i] = safe_ref(CC1_arr, i, mm1_val+1)
        # CC3 := REF(CC2,(MM1 + 1));
        CC3_arr[i] = safe_ref(CC2_arr, i, mm1_val+1)
        
        # DIFL1 := LLV(DIFF,(N1 + 1));
        DIFL1_arr[i] = llv(DIFF_arr, i, n1_val + 1)
        # DIFL2 := REF(DIFL1,(MM1 + 1));
        DIFL2_arr[i] = safe_ref(DIFL1_arr, i, mm1_val+1)
        # DIFL3 := REF(DIFL2,(MM1 + 1));
        DIFL3_arr[i] = safe_ref(DIFL2_arr, i, mm1_val+1)
        
        # CH1 := HHV(CLOSE,(MM1 + 1));
        CH1_arr[i] = hhv(close_list, i, mm1_val + 1)
        # CH2 := REF(CH1,(N1 + 1));
        CH2_arr[i] = safe_ref(CH1_arr, i, n1_val+1)
        # CH3 := REF(CH2,(N1 + 1));
        CH3_arr[i] = safe_ref(CH2_arr, i, n1_val+1)
        
        # DIFH1 := HHV(DIFF,(MM1 + 1));
        DIFH1_arr[i] = hhv(DIFF_arr, i, mm1_val + 1)
        # DIFH2 := REF(DIFH1,(N1 + 1));
        DIFH2_arr[i] = safe_ref(DIFH1_arr, i, n1_val+1)
        # DIFH3 := REF(DIFH2,(N1 + 1));
        DIFH3_arr[i] = safe_ref(DIFH2_arr, i, n1_val+1)
        
        # For booleans, we replicate:
        # AAA := ((CC1 < CC2) AND ((DIFL1 > DIFL2) AND ((REF(MACD,1) < 0) AND (DIFF < 0))));
        macd_prev = safe_ref(MACD_arr, i, 1)
        AAA_arr[i] = ((CC1_arr[i] < CC2_arr[i]) and
                      (DIFL1_arr[i] > DIFL2_arr[i]) and
                      (macd_prev < 0) and
                      (DIFF_arr[i] < 0))
        
        # BBB := ((CC1 < CC3) AND ((DIFL1 < DIFL2) AND ((DIFL1 > DIFL3) AND ((REF(MACD,1) < 0) AND (DIFF < 0)))));
        BBB_arr[i] = ((CC1_arr[i] < CC3_arr[i]) and
                      (DIFL1_arr[i] < DIFL2_arr[i]) and
                      (DIFL1_arr[i] > DIFL3_arr[i]) and
                      (macd_prev < 0) and
                      (DIFF_arr[i] < 0))
        
        # CCC := ((AAA OR BBB) AND (DIFF < 0));
        CCC_arr[i] = ((AAA_arr[i] or BBB_arr[i]) and (DIFF_arr[i] < 0))
        
        # LLL := ((REF(CCC,1) = 0) AND CCC);
        ccc_prev = safe_ref(CCC_arr, i, 1)  # boolean --> 0 or 1, we stored as bool, so safe_ref returns 0.0 if out of range
        # Check "REF(CCC,1) = 0" means ccc_prev is False
        LLL_arr[i] = (not bool(ccc_prev)) and CCC_arr[i]
        
        # XXX := ((REF(AAA,1) AND ((DIFL1 <= DIFL2) AND (DIFF < DEA))) 
        #         OR (REF(BBB,1) AND ((DIFL1 <= DIFL3) AND (DIFF < DEA))));
        AAA_prev = bool(safe_ref(AAA_arr, i, 1))
        BBB_prev = bool(safe_ref(BBB_arr, i, 1))
        XXX_arr[i] = ((AAA_prev and (DIFL1_arr[i] <= DIFL2_arr[i]) and (DIFF_arr[i] < DEA_arr[i]))
                      or
                      (BBB_prev and (DIFL1_arr[i] <= DIFL3_arr[i]) and (DIFF_arr[i] < DEA_arr[i])))
        
        # JJJ := (REF(CCC,1) AND (ABS(REF(DIFF,1)) >= (ABS(DIFF) * 1.01)));
        diff_prev = safe_ref(DIFF_arr, i, 1)
        ccc_prev_bool = bool(safe_ref(CCC_arr, i, 1))
        JJJ_arr[i] = (ccc_prev_bool and 
                      (abs(diff_prev) >= abs(DIFF_arr[i]) * 1.01))
        
        # BLBL := (REF(JJJ,1) AND (CCC AND ((ABS(REF(DIFF,1)) * 1.01) <= ABS(DIFF))));
        jjj_prev_bool = bool(safe_ref(JJJ_arr, i, 1))
        diff_prev2 = safe_ref(DIFF_arr, i, 1)
        BLBL_arr[i] = (jjj_prev_bool and 
                       (CCC_arr[i] and (abs(diff_prev2)*1.01 <= abs(DIFF_arr[i]))))
        
        # DXDX := ((REF(JJJ,1) = 0) AND JJJ);
        # "REF(JJJ,1) = 0" => jjj_prev_bool == False
        DXDX_arr[i] = (not jjj_prev_bool) and JJJ_arr[i]
        
        # DJGXX := (((CLOSE < CC2) OR (CLOSE < CC1)) AND 
        #           ((REF(JJJ,(MM1 + 1)) OR REF(JJJ,MM1)) AND 
        #            (NOT(REF(LLL,1)) AND (COUNT(JJJ,24) >= 1))));
        c = close_list[i]
        cond_close_part = (c < CC2_arr[i]) or (c < CC1_arr[i])
        jjj_m1_1 = bool(safe_ref(JJJ_arr, i, mm1_val+1))
        jjj_m1   = bool(safe_ref(JJJ_arr, i, mm1_val))
        lll_prev = bool(safe_ref(LLL_arr, i, 1))
        jjj_count_24 = count(JJJ_arr, i, 24)
        
        DJGXX_arr[i] = (cond_close_part and
                        ((jjj_m1_1 or jjj_m1) and
                         (not lll_prev) and (jjj_count_24 >= 1)))
        
        # DJXX := (NOT((COUNT(REF(DJGXX,1),2) >= 1)) AND DJGXX);
        # => we need REF(DJGXX,1) for the last bar, then count it in the last 2 bars
        # Actually the script means: "COUNT(REF(DJGXX,1),2) >= 1" 
        # is counting how many times DJGXX was true in the 2 bars prior to i. 
        # But let's replicate it literally:
        # We'll do a quick approach: we create temp array shift1 = [DJGXX[i-1], ...], 
        # then count how many of those in the last 2 bars are True.
        
        djgxx_prev = safe_ref(DJGXX_arr, i, 1)  # boolean or 0/1
        # But "COUNT(REF(DJGXX,1),2)" means from i-2 to i-1 how many times DJGXX[i-1-n]? 
        # A simpler approach: define a small helper to shift the DJGXX array by 1, or just 
        # do a direct check. We'll do the direct approach:
        # We'll check the 2 bars from i-1 to i (but the formula might differ slightly 
        # from your original platform’s interpretation). 
        # For consistency, let’s replicate exactly:
        shift1_val = bool(djgxx_prev)
        # count over the last 2 bars for shift1
        # We'll do "count(shift1, i, 2)" but that doesn't make sense because shift1 is just a single value. 
        # Realistically, the script "COUNT(REF(DJGXX,1),2) >= 1" means:
        # => among the previous 2 bars (including i-1, i-2?), how many times was DJGXX at bar-1?
        # There's a bit of ambiguity in how these layering references combine. 
        #
        # For simplicity, let's interpret it: we want to see if "REF(DJGXX,1)" was true 
        # in at least 1 of the last 2 bars. So:
        cond_count = 0
        if i >= 1:
            # bar i-1 => REF(DJGXX,1) at i-1 is DJGXX[i-2]
            djgxx_prev_for_i_minus_1 = safe_ref(DJGXX_arr, i-1, 1)
            if djgxx_prev_for_i_minus_1:
                cond_count += 1
        if i >= 2:
            # bar i-2 => REF(DJGXX,1) at i-2 is DJGXX[i-3]
            djgxx_prev_for_i_minus_2 = safe_ref(DJGXX_arr, i-2, 1)
            if djgxx_prev_for_i_minus_2:
                cond_count += 1
        
        # Now if cond_count >= 1 => "COUNT(REF(DJGXX,1),2) >= 1"
        DJXX_arr[i] = (not (cond_count >= 1)) and DJGXX_arr[i]
        
        # DXX := ((XXX OR DJXX) AND NOT(CCC));
        DXX_arr[i] = ((XXX_arr[i] or DJXX_arr[i]) and (not CCC_arr[i]))
        
        # (We skip the DRAWTEXT lines— instead we can mark buy signals, etc.)
        # "DRAWTEXT(DXDX, (DIFF / 0.81), 'BUY'), COLORRED" 
        # => If DXDX is True => buy signal
        if DXDX_arr[i]:
            buy_signals[i] = 1
        
        # ZJDBL := ((CH1 > CH2) AND ((DIFH1 < DIFH2) AND ((REF(MACD,1) > 0) AND (DIFF > 0))));
        macd_prev2 = safe_ref(MACD_arr, i, 1)
        ZJDBL_arr[i] = ((CH1_arr[i] > CH2_arr[i]) and
                        (DIFH1_arr[i] < DIFH2_arr[i]) and
                        (macd_prev2 > 0) and
                        (DIFF_arr[i] > 0))
        
        # GXDBL := ((CH1 > CH3) AND ((DIFH1 > DIFH2) AND ((DIFH1 < DIFH3) AND ((REF(MACD,1) > 0) AND (DIFF > 0)))));
        GXDBL_arr[i] = ((CH1_arr[i] > CH3_arr[i]) and
                        (DIFH1_arr[i] > DIFH2_arr[i]) and
                        (DIFH1_arr[i] < DIFH3_arr[i]) and
                        (macd_prev2 > 0) and
                        (DIFF_arr[i] > 0))
        
        # DBBL := ((ZJDBL OR GXDBL) AND (DIFF > 0));
        DBBL_arr[i] = ((ZJDBL_arr[i] or GXDBL_arr[i]) and (DIFF_arr[i] > 0))
        
        # DBL := ((REF(DBBL,1) = 0) AND (DBBL AND (DIFF > DEA)));
        dbbl_prev = safe_ref(DBBL_arr, i, 1)
        DBL_arr[i] = (not bool(dbbl_prev)) and DBBL_arr[i] and (DIFF_arr[i] > DEA_arr[i])
        
        # DBLXS := ((REF(ZJDBL,1) AND ((DIFH1 >= DIFH2) AND (DIFF > DEA))) OR
        #           (REF(GXDBL,1) AND ((DIFH1 >= DIFH3) AND (DIFF > DEA))));
        zj_prev = bool(safe_ref(ZJDBL_arr, i, 1))
        gx_prev = bool(safe_ref(GXDBL_arr, i, 1))
        DBLXS_arr[i] = ((zj_prev and (DIFH1_arr[i] >= DIFH2_arr[i]) and (DIFF_arr[i] > DEA_arr[i])) or
                        (gx_prev and (DIFH1_arr[i] >= DIFH3_arr[i]) and (DIFF_arr[i] > DEA_arr[i])))
        
        # DBJG := (REF(DBBL,1) AND (REF(DIFF,1) >= (DIFF * 1.01)));
        diff_prev3 = safe_ref(DIFF_arr, i, 1)
        DBJG_arr[i] = (bool(dbbl_prev) and (diff_prev3 >= (DIFF_arr[i]*1.01)))
        
        # DBJGXC := (REF(NOT(DBJG),1) AND DBJG);
        dbjg_prev = bool(safe_ref(DBJG_arr, i, 1))
        DBJGXC_arr[i] = ((not dbjg_prev) and DBJG_arr[i])
        
        # DBJGBL := (REF(DBJG,1) AND (DBBL AND ((REF(DIFF,1) * 1.01) <= DIFF)));
        dbjg_prev2 = bool(safe_ref(DBJG_arr, i, 1))
        diff_prev4 = safe_ref(DIFF_arr, i, 1)
        DBJGBL_arr[i] = (dbjg_prev2 and DBBL_arr[i] and ((diff_prev4*1.01) <= DIFF_arr[i]))
        
        # ZZZZZ := (((CLOSE > CH2) OR (CLOSE > CH1)) AND ((REF(DBJG,(N1 + 1)) OR REF(DBJG,N1)) AND (NOT(REF(DBL,1)) AND (COUNT(DBJG,23) >= 1))));
        dbjg_n1_1 = bool(safe_ref(DBJG_arr, i, n1_val+1))
        dbjg_n1   = bool(safe_ref(DBJG_arr, i, n1_val))
        dbl_prev  = bool(safe_ref(DBL_arr, i, 1))
        dbjg_count_23 = count(DBJG_arr, i, 23)
        cond_close_part2 = (c > CH2_arr[i]) or (c > CH1_arr[i])
        ZZZZZ_arr[i] = (cond_close_part2 and
                        ((dbjg_n1_1 or dbjg_n1) and (not dbl_prev) and (dbjg_count_23 >= 1)))
        
        # YYYYY := (NOT((COUNT(REF(ZZZZZ,1),2) >= 1)) AND ZZZZZ);
        # Similar situation with "COUNT(REF(ZZZZZ,1),2)"
        # We'll do a quick direct approach:
        zzzzz_prev = bool(safe_ref(ZZZZZ_arr, i, 1))
        # count how many times zzzzz_prev was True in last 2 bars, etc.
        cond_cnt2 = 0
        if i >= 1:
            zzzzz_prev_for_im1 = bool(safe_ref(ZZZZZ_arr, i-1, 1))
            if zzzzz_prev_for_im1:
                cond_cnt2 += 1
        if i >= 2:
            zzzzz_prev_for_im2 = bool(safe_ref(ZZZZZ_arr, i-2, 1))
            if zzzzz_prev_for_im2:
                cond_cnt2 += 1
        
        YYYYY_arr[i] = (not (cond_cnt2 >= 1)) and ZZZZZ_arr[i]
        
        # WWWWW := ((DBLXS OR YYYYY) AND NOT(DBBL));
        WWWWW_arr[i] = ((DBLXS_arr[i] or YYYYY_arr[i]) and (not DBBL_arr[i]))
        
        # Finally, "DRAWTEXT(DBJGXC,(DIFF * 1.21),'SELL'),COLORGREEN"
        # => If DBJGXC is True => SELL signal
        if DBJGXC_arr[i]:
            sell_signals[i] = 1
    
    # Return final signals (or any arrays you want)
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
    print("Buy signals:", signal1)
    print("Sell signals:", signal2)

