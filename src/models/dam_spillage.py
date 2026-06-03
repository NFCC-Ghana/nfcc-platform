def normalized(value, max_value):
    value = max(0, value)  # prevent negative values
    return min(100, (value / max_value) * 100)


def compute_spillage_probability(rainfall, reservoir_level, inflow):
    
    """
    Compute dam spillage probability (0–100%)

    Parameters:
        rainfall (float): Rainfall in mm
        reservoir_level (float): Reservoir level in %
        inflow (float): Inflow rate in m³/s

    Returns:
        float: Spillage probability (0–100)
    """
    rainfall_score =normalized(rainfall,200)
    reservoir_score = normalized(reservoir_level,100)
    inflow_score = normalized(inflow,500)
    
    
    probability = (0.5 * rainfall_score) + (0.3 * reservoir_score) + (0.2 * inflow_score)
    
    
    return round(min(100,max(0, probability)),2)


#service function to get spillage forecast
def get_spillage_forecast(dam,rainfall, reservoir_level, inflow):
    probability = compute_spillage_probability(rainfall, reservoir_level, inflow)
    
    risk_level = (
        "high" if probability >70 else "medium" if probability >40 else "low" 
    )
    
    
    return {
    "dam": dam,
    "spillage_probability": probability,
    "risk_level": risk_level,
    "status": "safe" if probability < 40 else "warning" if probability < 70 else "danger",
    "inputs": {
        "rainfall": rainfall,
        "reservoir_level": reservoir_level,
        "inflow": inflow
    }
   
  }
    
    