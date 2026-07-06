import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Smart Community Decision Intelligence MCP Server")

@mcp.tool()
def get_traffic_conditions(location: str) -> str:
    """Get live traffic conditions, congestion levels, and route recommendations for a location.

    Args:
        location: The name of the city, area, or street.
    """
    loc_lower = location.lower()
    if "downtown" in loc_lower or "center" in loc_lower:
        return (
            "Traffic Alert: High Congestion on Main St & 5th Ave due to an active road closure. "
            "Congestion level: 85%. Travel delay: +20 minutes. "
            "Fastest route suggestion: Detour via Broad St and 8th Ave (Delay: +4 mins). "
            "Public transportation recommendation: Subway Line Red (5 min intervals, running on time)."
        )
    elif "highway" in loc_lower or "expressway" in loc_lower:
        return (
            "Traffic Update: Moderate traffic flowing at 45 mph. "
            "Congestion level: 45%. Travel delay: +5 minutes. "
            "No active accidents or closures detected."
        )
    else:
        return (
            f"Traffic Update for {location}: Normal traffic flow. "
            "Congestion level: 15%. Travel delay: None. "
            "Safe to travel."
        )

@mcp.tool()
def get_environmental_data(location: str) -> str:
    """Get current Air Quality Index (AQI), weather, and sustainability warnings for a location.

    Args:
        location: The name of the city or area.
    """
    loc_lower = location.lower()
    if "industrial" in loc_lower or "factory" in loc_lower:
        return (
            "Environmental Status: Poor Air Quality detected. "
            "AQI: 155 (Unhealthy). Primary pollutant: PM2.5. "
            "Weather: 82°F, Humid, minimal wind. "
            "Risk level: High. "
            "Sustainability recommendation: Sensitive groups should avoid outdoor activities. "
            "Energy grid warning: High HVAC load, voluntary energy conservation active."
        )
    elif "park" in loc_lower or "residential" in loc_lower:
        return (
            "Environmental Status: Excellent Air Quality. "
            "AQI: 35 (Good). Primary pollutant: None. "
            "Weather: 72°F, Sunny, light breeze. "
            "Risk level: Very Low. "
            "Sustainability recommendation: Outdoor activities highly recommended."
        )
    else:
        return (
            f"Environmental Status for {location}: Moderate. "
            "AQI: 55 (Moderate). Primary pollutant: Ozone. "
            "Weather: 75°F, Partly Cloudy. "
            "Risk level: Low. "
            "Sustainability recommendation: General public can enjoy normal activities."
        )

@mcp.tool()
def get_healthcare_facilities(location: str, specialty: str = None) -> str:
    """Get nearby healthcare facilities, emergency wait times, and services for a location.

    Args:
        location: The name of the area or city.
        specialty: Optional medical specialty needed (e.g., 'pediatric', 'cardiology').
    """
    loc_lower = location.lower()
    specialty_str = f" ({specialty})" if specialty else ""
    
    if "downtown" in loc_lower:
        return (
            f"Healthcare facilities near Downtown{specialty_str}:\n"
            "1. Mercy General Hospital (0.8 miles) - ER Wait time: 15 mins. Bed availability: High. Specialty services: Trauma, Cardiology.\n"
            "2. Downtown Community Health Center (0.3 miles) - Wait time: 30 mins (Urgent care). Bed availability: N/A. Specialty services: Pediatrics, Family Medicine."
        )
    else:
        return (
            f"Healthcare facilities near {location}{specialty_str}:\n"
            f"1. Community Medical Center (2.5 miles) - ER Wait time: 45 mins. Bed availability: Medium. General Emergency services.\n"
            f"2. Eastside Clinic (3.1 miles) - Wait time: 15 mins (Walk-in). Primary Care."
        )

@mcp.tool()
def get_citizen_programs(income: float = 50000.0, age: int = 30, location: str = "City") -> str:
    """Get eligible government schemes and public citizen support programs.

    Args:
        income: The monthly/annual household income in USD.
        age: The age of the citizen.
        location: The residence city or area.
    """
    programs = []
    if age >= 65:
        programs.append("Senior Wellness & Support Program (eligible for free healthcare checkups and transport discounts)")
    if income < 30000:
        programs.append("Income-Assisted Housing & Utility Credit Program (up to 30% discount on electricity and water bills)")
    
    programs.append("Community Engagement Initiative (open to all residents for local civic governance volunteering)")
    
    programs_list = "\n- ".join(programs)
    return (
        f"Eligible Programs for age {age}, income ${income:.2f} in {location}:\n"
        f"- {programs_list}\n"
        "Next steps: File application on the Smart Citizen Portal or visit the Community Support Office."
    )

if __name__ == "__main__":
    mcp.run()
