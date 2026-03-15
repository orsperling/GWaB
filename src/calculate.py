import numpy as np

# 📊 Calculate monthly irrigation and soil water budget
def calc_irrigation(ndvi, rain, et0, irrigation_months, irrigation_limit, conversion_factor, winter_irrigation_override=None):

    df = et0.copy()
    df['ET0'] = df['ET0'] * conversion_factor

    # Field conditions and active periods
    p_ndvi = .8 * (1 - np.exp(-5 * ndvi))
    k_crop = p_ndvi / .8
    m_start, m_end = irrigation_months
    df['pNDVI'] = p_ndvi
    df['K_crop'] = k_crop
    df['is_canopy'] = df['month'].between(3, 10).astype(int)
    df['is_irrigation'] = df['month'].between(m_start, m_end).astype(int)

    canopy_mask = df['is_canopy'] == 1
    irrigation_mask = df['is_irrigation'] == 1
    irrigation_month_count = int(irrigation_mask.sum())

    df['ET0'] *= df['is_canopy']
    df['ETcrop'] = df['ET0'] * k_crop  # ETcrop is already zero outside canopy months

    # Climate inputs and winter refill
    rain_eff = rain * conversion_factor * 0.75
    soil_capacity = 400 * conversion_factor
    recommended_winter_irrigation = max(0, soil_capacity - rain_eff)
    winter_irrigation = max(0, winter_irrigation_override) if winter_irrigation_override is not None else recommended_winter_irrigation

    # Soil uptake happens in canopy months that are outside irrigation months
    df['soil_uptake'] = (df['ETcrop'] * (canopy_mask & ~irrigation_mask).astype(int)).clip(lower=0)
    # Scalar soil reserve before distributing extraction across irrigation months
    soil_reserve = float(np.clip(rain_eff + winter_irrigation, 0, soil_capacity))
    # Extraction per irrigation month
    month_extract = (soil_reserve- df['soil_uptake'].sum()) / np.maximum(irrigation_month_count, 1)
    df['extract'] = month_extract

    # Summer irrigation need (only within irrigation months)
    df['irrigation'] = (df['ETcrop'] - month_extract).clip(lower=0) * df['is_irrigation']

    # Apply user summer irrigation limit (0 means use recommended)
    total_irrigation_needed = df['irrigation'].sum()
    k_deficit = (irrigation_limit / np.maximum(total_irrigation_needed, 1e-9)) if irrigation_limit > 0 else 1
    df['irrigation'] *= k_deficit
 
    # Final balance and status
    df['ETactual'] = df['irrigation'] + df['extract']
    df['soil_budget'] = (soil_reserve + df['irrigation'].cumsum() - df['ETcrop'].cumsum())


    df['alert'] = np.where(df['soil_budget'] < -10, 'drought', 'safe')
    df['winter_irrigation'] = winter_irrigation
    df['summer_irrigation'] = df['irrigation'].sum()


    return df
