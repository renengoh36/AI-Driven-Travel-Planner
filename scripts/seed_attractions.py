"""
scripts/seed_attractions.py

Pre-populates the ATTRACTIONS table for the 6 featured destination cities so that
the app works immediately after setup — without needing to search each city first.

Two modes:
  1. REAL mode  — GOOGLE_API_KEY is set in .env → fetches live data from Google Places
  2. DEMO mode  — no API key              → inserts synthetic placeholder attractions
                                            so the UI is fully testable offline

Run this BEFORE generate_synthetic_data.py:
    python scripts/seed_attractions.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.db import db
from app.models.attraction import Attraction

# (city, country, lat, lon) — coordinates hardcoded to skip Geocoding API
FEATURED_CITIES = [
    ("Tokyo",        "Japan",           35.6762,  139.6503),
    ("Paris",        "France",          48.8566,    2.3522),
    ("Kuala Lumpur", "Malaysia",         3.1390,  101.6869),
    ("Bali",         "Indonesia",       -8.3405,  115.0920),
    ("New York",     "United States",   40.7128,  -74.0060),
    ("Rome",         "Italy",           41.9028,   12.4964),
    ("Bangkok",      "Thailand",        13.7563,  100.5018),
    ("London",       "United Kingdom",  51.5074,   -0.1278),
    ("Osaka",        "Japan",           34.6937,  135.5023),
    ("Sydney",       "Australia",      -33.8688,  151.2093),
]

# ── Synthetic fallback attractions (used when no API key is available) ──────
# 41 cities × 8 attractions = 328 total
SYNTHETIC_ATTRACTIONS = [

    # ═══════════════════════════════════
    #  EAST ASIA
    # ═══════════════════════════════════

    # Tokyo, Japan
    ("Tokyo Tower",              "Tokyo","Japan","history",    4.5, 10.0, 3,  35.6586, 139.7454),
    ("Shinjuku Gyoen",           "Tokyo","Japan","nature",     4.6,  5.0, 3,  35.6851, 139.7100),
    ("Senso-ji Temple",          "Tokyo","Japan","history",    4.7,  0.0, 4,  35.7148, 139.7967),
    ("Tsukiji Fish Market",      "Tokyo","Japan","food",       4.3,  0.0, 3,  35.6654, 139.7707),
    ("Akihabara District",       "Tokyo","Japan","shopping",   4.4,  0.0, 3,  35.7023, 139.7745),
    ("teamLab Borderless",       "Tokyo","Japan","adventure",  4.6, 32.0, 4,  35.6248, 139.7830),
    ("Harajuku Takeshita St",    "Tokyo","Japan","shopping",   4.1,  0.0, 3,  35.6702, 139.7026),
    ("Ueno Park",                "Tokyo","Japan","nature",     4.4,  0.0, 3,  35.7148, 139.7737),

    # Osaka, Japan
    ("Osaka Castle",             "Osaka","Japan","history",    4.5,  6.0, 4,  34.6873, 135.5262),
    ("Dotonbori",                "Osaka","Japan","food",       4.4,  0.0, 4,  34.6687, 135.5006),
    ("Shinsekai",                "Osaka","Japan","food",       4.2,  0.0, 3,  34.6524, 135.5063),
    ("Namba Kuromon Market",     "Osaka","Japan","food",       4.3,  0.0, 3,  34.6637, 135.5030),
    ("Universal Studios Japan",  "Osaka","Japan","adventure",  4.5, 75.0, 4,  34.6654, 135.4323),
    ("Shinsaibashi",             "Osaka","Japan","shopping",   4.3,  0.0, 3,  34.6731, 135.5001),
    ("Sumiyoshi Taisha",         "Osaka","Japan","history",    4.5,  0.0, 3,  34.6142, 135.4929),
    ("Tempozan Ferris Wheel",    "Osaka","Japan","adventure",  4.1, 13.0, 3,  34.6553, 135.4279),

    # Kyoto, Japan
    ("Fushimi Inari Shrine",     "Kyoto","Japan","history",    4.8,  0.0, 4,  34.9671, 135.7727),
    ("Kinkaku-ji Gold Temple",   "Kyoto","Japan","history",    4.7,  5.0, 4,  35.0394, 135.7292),
    ("Arashiyama Bamboo Grove",  "Kyoto","Japan","nature",     4.6,  0.0, 4,  35.0094, 135.6722),
    ("Nishiki Market",           "Kyoto","Japan","food",       4.4,  0.0, 3,  35.0050, 135.7660),
    ("Gion Geisha District",     "Kyoto","Japan","history",    4.5,  0.0, 3,  35.0035, 135.7755),
    ("Philosopher's Path",       "Kyoto","Japan","nature",     4.5,  0.0, 3,  35.0205, 135.7953),
    ("Nijo Castle",              "Kyoto","Japan","history",    4.5,  6.0, 3,  35.0142, 135.7480),
    ("Ryoan-ji Rock Garden",     "Kyoto","Japan","relaxation", 4.6,  5.0, 3,  35.0345, 135.7179),

    # Seoul, South Korea
    ("Gyeongbokgung Palace",     "Seoul","South Korea","history",    4.7,  3.0, 4,  37.5796, 126.9770),
    ("Myeongdong Shopping",      "Seoul","South Korea","shopping",   4.3,  0.0, 4,  37.5633, 126.9856),
    ("N Seoul Tower",            "Seoul","South Korea","history",    4.6,  8.0, 4,  37.5512, 126.9882),
    ("Bukchon Hanok Village",    "Seoul","South Korea","history",    4.5,  0.0, 3,  37.5823, 126.9830),
    ("Hongdae District",         "Seoul","South Korea","food",       4.4,  0.0, 3,  37.5563, 126.9236),
    ("Lotte World",              "Seoul","South Korea","adventure",  4.3, 45.0, 3,  37.5112, 127.0982),
    ("Insadong Market",          "Seoul","South Korea","shopping",   4.3,  0.0, 3,  37.5742, 126.9853),
    ("Han River Park",           "Seoul","South Korea","relaxation", 4.4,  0.0, 3,  37.5285, 126.9973),

    # Hong Kong, China
    ("Victoria Peak",            "Hong Kong","China","nature",      4.6, 12.0, 4,  22.2755, 114.1455),
    ("Temple Street Night Market","Hong Kong","China","shopping",   4.3,  0.0, 3,  22.3069, 114.1703),
    ("Disneyland Hong Kong",     "Hong Kong","China","adventure",   4.4, 80.0, 4,  22.3130, 114.0413),
    ("Mong Kok Market",          "Hong Kong","China","shopping",    4.2,  0.0, 3,  22.3193, 114.1694),
    ("Star Ferry Harbour",       "Hong Kong","China","relaxation",  4.5,  3.0, 4,  22.2906, 114.1681),
    ("Man Mo Temple",            "Hong Kong","China","history",     4.4,  0.0, 3,  22.2835, 114.1437),
    ("Lantau Island Big Buddha", "Hong Kong","China","history",     4.6,  5.0, 3,  22.2540, 113.9049),
    ("Aberdeen Floating Village","Hong Kong","China","food",        4.2,  0.0, 2,  22.2464, 114.1522),

    # ═══════════════════════════════════
    #  SOUTHEAST ASIA
    # ═══════════════════════════════════

    # Kuala Lumpur, Malaysia
    ("Petronas Twin Towers",     "Kuala Lumpur","Malaysia","history",  4.6, 22.0, 4,   3.1579, 101.7119),
    ("Batu Caves",               "Kuala Lumpur","Malaysia","history",  4.6,  0.0, 4,   3.2379, 101.6840),
    ("Bukit Bintang",            "Kuala Lumpur","Malaysia","shopping", 4.3,  0.0, 3,   3.1466, 101.7138),
    ("KL Bird Park",             "Kuala Lumpur","Malaysia","nature",   4.5, 25.0, 3,   3.1420, 101.6866),
    ("Central Market KL",        "Kuala Lumpur","Malaysia","shopping", 4.1,  0.0, 2,   3.1450, 101.6954),
    ("Jalan Alor Night Market",  "Kuala Lumpur","Malaysia","food",     4.4,  0.0, 2,   3.1467, 101.7073),
    ("KLCC Park",                "Kuala Lumpur","Malaysia","nature",   4.5,  0.0, 3,   3.1567, 101.7121),
    ("Merdeka Square",           "Kuala Lumpur","Malaysia","history",  4.4,  0.0, 2,   3.1486, 101.6943),

    # Penang, Malaysia
    ("George Town Heritage",     "Penang","Malaysia","history",    4.7,  0.0, 4,   5.4141, 100.3288),
    ("Penang Hill",              "Penang","Malaysia","nature",     4.6, 10.0, 4,   5.4264, 100.2756),
    ("Kek Lok Si Temple",        "Penang","Malaysia","history",    4.5,  5.0, 3,   5.4003, 100.2710),
    ("Gurney Drive Hawker Str",  "Penang","Malaysia","food",       4.6,  0.0, 3,   5.4399, 100.3042),
    ("Batu Ferringhi Beach",     "Penang","Malaysia","relaxation", 4.3,  0.0, 3,   5.4738, 100.2470),
    ("Khoo Kongsi Clan House",   "Penang","Malaysia","history",    4.4,  3.0, 3,   5.4152, 100.3395),
    ("Clan Jetties",             "Penang","Malaysia","history",    4.3,  0.0, 3,   5.4152, 100.3454),
    ("Street Art Penang",        "Penang","Malaysia","history",    4.6,  0.0, 3,   5.4138, 100.3370),

    # Langkawi, Malaysia
    ("Langkawi Sky Bridge",      "Langkawi","Malaysia","adventure",  4.5, 20.0, 3,   6.3774, 99.6595),
    ("Pantai Cenang Beach",      "Langkawi","Malaysia","relaxation", 4.4,  0.0, 3,   6.2841, 99.7152),
    ("Langkawi Eagle Square",    "Langkawi","Malaysia","history",    4.3,  0.0, 2,   6.3156, 99.8458),
    ("Mangrove Tour Langkawi",   "Langkawi","Malaysia","nature",     4.6, 15.0, 3,   6.3500, 99.8000),
    ("Underwater World Langkawi","Langkawi","Malaysia","nature",     4.2, 18.0, 2,   6.2827, 99.7139),
    ("Telaga Harbour Park",      "Langkawi","Malaysia","relaxation", 4.2,  0.0, 2,   6.3707, 99.6622),
    ("Black Sand Beach Langkawi","Langkawi","Malaysia","relaxation", 4.3,  0.0, 2,   6.4120, 99.7880),
    ("Gunung Raya Mountain",     "Langkawi","Malaysia","nature",     4.4,  0.0, 2,   6.3700, 99.7800),

    # Singapore
    ("Marina Bay Sands",         "Singapore","Singapore","relaxation", 4.6, 30.0, 4,   1.2838, 103.8607),
    ("Gardens by the Bay",       "Singapore","Singapore","nature",     4.8, 15.0, 4,   1.2816, 103.8636),
    ("Sentosa Island",           "Singapore","Singapore","adventure",  4.5, 20.0, 4,   1.2494, 103.8303),
    ("Maxwell Hawker Centre",    "Singapore","Singapore","food",       4.5,  0.0, 3,   1.2800, 103.8453),
    ("Orchard Road",             "Singapore","Singapore","shopping",   4.4,  0.0, 4,   1.3048, 103.8318),
    ("Universal Studios SG",     "Singapore","Singapore","adventure",  4.5, 70.0, 4,   1.2540, 103.8238),
    ("Chinatown Singapore",      "Singapore","Singapore","history",    4.3,  0.0, 3,   1.2825, 103.8445),
    ("Singapore Zoo",            "Singapore","Singapore","nature",     4.7, 35.0, 3,   1.4043, 103.7930),

    # Bangkok, Thailand
    ("Grand Palace",             "Bangkok","Thailand","history",   4.5, 15.0, 4,  13.7500, 100.4913),
    ("Wat Pho Temple",           "Bangkok","Thailand","history",   4.5,  4.0, 4,  13.7466, 100.4930),
    ("Chatuchak Market",         "Bangkok","Thailand","shopping",  4.3,  0.0, 4,  13.7999, 100.5501),
    ("Lumphini Park",            "Bangkok","Thailand","nature",    4.4,  0.0, 3,  13.7301, 100.5413),
    ("Khao San Road",            "Bangkok","Thailand","food",      4.0,  0.0, 3,  13.7587, 100.4971),
    ("Asiatique Waterfront",     "Bangkok","Thailand","shopping",  4.3,  0.0, 3,  13.7040, 100.5049),
    ("Wat Arun",                 "Bangkok","Thailand","history",   4.5,  2.0, 4,  13.7436, 100.4883),
    ("Sukhumvit Night Market",   "Bangkok","Thailand","food",      4.2,  0.0, 3,  13.7310, 100.5693),

    # Phuket, Thailand
    ("Patong Beach",             "Phuket","Thailand","relaxation", 4.2,  0.0, 4,   7.8966, 98.2966),
    ("Phi Phi Islands",          "Phuket","Thailand","nature",     4.7, 20.0, 4,   7.7407, 98.7784),
    ("Big Buddha Phuket",        "Phuket","Thailand","history",    4.5,  0.0, 3,   7.8273, 98.2988),
    ("Phang Nga Bay",            "Phuket","Thailand","nature",     4.7, 25.0, 3,   8.2813, 98.5042),
    ("Old Phuket Town",          "Phuket","Thailand","history",    4.4,  0.0, 3,   7.8783, 98.3920),
    ("Rawai Beach",              "Phuket","Thailand","relaxation", 4.3,  0.0, 2,   7.7836, 98.3257),
    ("Bangla Road Nightlife",    "Phuket","Thailand","food",       4.0,  0.0, 3,   7.8919, 98.2949),
    ("Kata Noi Beach",           "Phuket","Thailand","relaxation", 4.5,  0.0, 3,   7.8163, 98.2993),

    # Chiang Mai, Thailand
    ("Doi Inthanon Park",        "Chiang Mai","Thailand","nature",   4.8, 10.0, 3,  18.5896, 98.4869),
    ("Doi Suthep Temple",        "Chiang Mai","Thailand","history",  4.6,  2.0, 4,  18.8046, 98.9218),
    ("Night Bazaar Chiang Mai",  "Chiang Mai","Thailand","shopping", 4.3,  0.0, 3,  18.7870, 98.9981),
    ("Elephant Nature Park",     "Chiang Mai","Thailand","nature",   4.8, 70.0, 4,  19.0483, 98.9044),
    ("Old City Temples CM",      "Chiang Mai","Thailand","history",  4.5,  0.0, 3,  18.7883, 98.9853),
    ("Sunday Walking Street CM", "Chiang Mai","Thailand","food",     4.5,  0.0, 3,  18.7872, 98.9878),
    ("Mae Sa Elephant Camp",     "Chiang Mai","Thailand","adventure",4.4, 50.0, 3,  18.9184, 98.8620),
    ("Nimmanhaemin Road",        "Chiang Mai","Thailand","food",     4.4,  0.0, 3,  18.7991, 98.9680),

    # Bali, Indonesia
    ("Tanah Lot Temple",         "Bali","Indonesia","history",    4.6, 10.0, 4,  -8.6215, 115.0865),
    ("Ubud Monkey Forest",       "Bali","Indonesia","nature",     4.5, 10.0, 3,  -8.5189, 115.2626),
    ("Tegallalang Rice Terrace", "Bali","Indonesia","nature",     4.5,  0.0, 3,  -8.4320, 115.2784),
    ("Seminyak Beach",           "Bali","Indonesia","relaxation", 4.4,  0.0, 3,  -8.6920, 115.1641),
    ("Uluwatu Temple",           "Bali","Indonesia","history",    4.6,  5.0, 3,  -8.8291, 115.0849),
    ("Kuta Beach",               "Bali","Indonesia","relaxation", 4.2,  0.0, 3,  -8.7188, 115.1686),
    ("Tirta Empul",              "Bali","Indonesia","history",    4.7,  5.0, 3,  -8.4153, 115.3147),
    ("Nusa Penida",              "Bali","Indonesia","adventure",  4.7, 15.0, 3,  -8.7277, 115.5444),

    # Ho Chi Minh City, Vietnam
    ("War Remnants Museum",      "Ho Chi Minh City","Vietnam","history",  4.6,  2.0, 3,  10.7797, 106.6926),
    ("Ben Thanh Market",         "Ho Chi Minh City","Vietnam","shopping", 4.1,  0.0, 3,  10.7725, 106.6980),
    ("Cu Chi Tunnels",           "Ho Chi Minh City","Vietnam","history",  4.6, 10.0, 3,  11.1437, 106.4618),
    ("Reunification Palace",     "Ho Chi Minh City","Vietnam","history",  4.4,  2.0, 3,  10.7769, 106.6951),
    ("Notre-Dame Cathedral HCM", "Ho Chi Minh City","Vietnam","history",  4.5,  0.0, 3,  10.7797, 106.6989),
    ("Bui Vien Walking Street",  "Ho Chi Minh City","Vietnam","food",     4.2,  0.0, 3,  10.7679, 106.6921),
    ("Mekong Delta",             "Ho Chi Minh City","Vietnam","nature",   4.7, 20.0, 3,  10.0411, 105.7472),
    ("Jade Emperor Pagoda",      "Ho Chi Minh City","Vietnam","history",  4.5,  0.0, 3,  10.7872, 106.6900),

    # Hanoi, Vietnam
    ("Hoan Kiem Lake",           "Hanoi","Vietnam","nature",    4.5,  0.0, 4,  21.0285, 105.8521),
    ("Ho Chi Minh Mausoleum",    "Hanoi","Vietnam","history",   4.4,  0.0, 3,  21.0368, 105.8352),
    ("Temple of Literature",     "Hanoi","Vietnam","history",   4.5,  1.5, 3,  21.0281, 105.8359),
    ("Old Quarter Hanoi",        "Hanoi","Vietnam","food",      4.4,  0.0, 3,  21.0340, 105.8484),
    ("Ha Long Bay",              "Hanoi","Vietnam","nature",    4.8, 50.0, 4,  20.9101, 107.1839),
    ("Hoa Lo Prison Museum",     "Hanoi","Vietnam","history",   4.3,  1.0, 2,  21.0317, 105.8449),
    ("Tran Quoc Pagoda",         "Hanoi","Vietnam","history",   4.5,  0.0, 2,  21.0467, 105.8415),
    ("Bat Trang Pottery Village","Hanoi","Vietnam","shopping",  4.4,  0.0, 2,  20.9872, 105.9018),

    # ═══════════════════════════════════
    #  SOUTH ASIA & MIDDLE EAST
    # ═══════════════════════════════════

    # Mumbai, India
    ("Gateway of India",         "Mumbai","India","history",    4.5,  0.0, 4,  18.9220,  72.8347),
    ("Chhatrapati Shivaji Museum","Mumbai","India","history",   4.6,  5.0, 3,  18.9267,  72.8328),
    ("Marine Drive",             "Mumbai","India","relaxation", 4.5,  0.0, 4,  18.9441,  72.8233),
    ("Elephanta Caves",          "Mumbai","India","history",    4.3, 10.0, 3,  18.9633,  72.9315),
    ("Juhu Beach",               "Mumbai","India","relaxation", 4.0,  0.0, 3,  19.1075,  72.8263),
    ("Colaba Causeway Market",   "Mumbai","India","shopping",   4.3,  0.0, 3,  18.9162,  72.8295),
    ("Dharavi Street Food",      "Mumbai","India","food",       4.3,  0.0, 2,  19.0430,  72.8530),
    ("Siddhivinayak Temple",     "Mumbai","India","history",    4.5,  0.0, 3,  19.0167,  72.8302),

    # Delhi, India
    ("Taj Mahal Agra",           "Delhi","India","history",    4.8, 15.0, 4,  27.1751,  78.0421),
    ("Red Fort Delhi",           "Delhi","India","history",    4.5,  8.0, 4,  28.6562,  77.2410),
    ("India Gate",               "Delhi","India","history",    4.6,  0.0, 4,  28.6129,  77.2295),
    ("Humayun's Tomb",           "Delhi","India","history",    4.6,  6.0, 3,  28.5933,  77.2507),
    ("Qutub Minar",              "Delhi","India","history",    4.5,  5.0, 3,  28.5245,  77.1855),
    ("Chandni Chowk Market",     "Delhi","India","shopping",   4.2,  0.0, 3,  28.6508,  77.2311),
    ("Akshardham Temple",        "Delhi","India","history",    4.6,  0.0, 3,  28.6127,  77.2773),
    ("Lodhi Garden",             "Delhi","India","nature",     4.6,  0.0, 3,  28.5931,  77.2198),

    # Dubai, United Arab Emirates
    ("Burj Khalifa",             "Dubai","United Arab Emirates","history",    4.7, 30.0, 4,  25.1972,  55.2744),
    ("Dubai Mall",               "Dubai","United Arab Emirates","shopping",   4.6,  0.0, 4,  25.1975,  55.2796),
    ("Palm Jumeirah",            "Dubai","United Arab Emirates","relaxation", 4.5,  0.0, 4,  25.1124,  55.1390),
    ("Dubai Creek",              "Dubai","United Arab Emirates","history",    4.3,  0.0, 3,  25.2631,  55.3012),
    ("Dubai Museum",             "Dubai","United Arab Emirates","history",    4.2,  1.0, 3,  25.2637,  55.2972),
    ("Jumeirah Beach",           "Dubai","United Arab Emirates","relaxation", 4.5,  0.0, 4,  25.2048,  55.2368),
    ("Global Village Dubai",     "Dubai","United Arab Emirates","food",       4.4, 15.0, 3,  25.0682,  55.3071),
    ("Desert Safari Dubai",      "Dubai","United Arab Emirates","adventure",  4.7, 50.0, 4,  24.9897,  55.2040),

    # Doha, Qatar
    ("Museum of Islamic Art",    "Doha","Qatar","history",     4.7,  0.0, 4,  25.2948,  51.5361),
    ("Souq Waqif",               "Doha","Qatar","shopping",    4.6,  0.0, 4,  25.2867,  51.5320),
    ("The Pearl Island Doha",    "Doha","Qatar","relaxation",  4.5,  0.0, 4,  25.3688,  51.5561),
    ("Katara Cultural Village",  "Doha","Qatar","history",     4.5,  0.0, 3,  25.3561,  51.5261),
    ("Corniche Promenade Doha",  "Doha","Qatar","relaxation",  4.5,  0.0, 3,  25.3000,  51.5333),
    ("Aspire Park",              "Doha","Qatar","nature",      4.3,  0.0, 3,  25.2625,  51.4509),
    ("Villaggio Mall",           "Doha","Qatar","shopping",    4.5,  0.0, 3,  25.2600,  51.4300),
    ("Desert Safari Qatar",      "Doha","Qatar","adventure",   4.6, 40.0, 3,  25.0000,  51.1000),

    # Istanbul, Turkey
    ("Hagia Sophia",             "Istanbul","Turkey","history",    4.7,  0.0, 4,  41.0086,  28.9802),
    ("Blue Mosque",              "Istanbul","Turkey","history",    4.7,  0.0, 4,  41.0054,  28.9768),
    ("Grand Bazaar",             "Istanbul","Turkey","shopping",   4.4,  0.0, 4,  41.0107,  28.9681),
    ("Topkapi Palace",           "Istanbul","Turkey","history",    4.6, 15.0, 4,  41.0115,  28.9833),
    ("Bosphorus Cruise",         "Istanbul","Turkey","relaxation", 4.5, 12.0, 3,  41.0300,  29.0100),
    ("Spice Bazaar",             "Istanbul","Turkey","food",       4.4,  0.0, 3,  41.0166,  28.9703),
    ("Galata Tower",             "Istanbul","Turkey","history",    4.5,  9.0, 3,  41.0258,  28.9742),
    ("Dolmabahce Palace",        "Istanbul","Turkey","history",    4.6, 14.0, 3,  41.0390,  29.0002),

    # ═══════════════════════════════════
    #  EUROPE
    # ═══════════════════════════════════

    # Paris, France
    ("Eiffel Tower",             "Paris","France","history",    4.7, 26.0, 4,  48.8584,   2.2945),
    ("Louvre Museum",            "Paris","France","history",    4.7, 17.0, 4,  48.8606,   2.3376),
    ("Notre-Dame Cathedral",     "Paris","France","history",    4.7,  0.0, 4,  48.8530,   2.3499),
    ("Montmartre",               "Paris","France","history",    4.5,  0.0, 3,  48.8867,   2.3431),
    ("Musee d'Orsay",            "Paris","France","history",    4.8, 16.0, 4,  48.8600,   2.3266),
    ("Champs-Elysees",           "Paris","France","shopping",   4.4,  0.0, 3,  48.8698,   2.3079),
    ("Seine River Cruise",       "Paris","France","relaxation", 4.5, 15.0, 3,  48.8588,   2.3470),
    ("Palace of Versailles",     "Paris","France","history",    4.6, 20.0, 4,  48.8049,   2.1204),

    # London, United Kingdom
    ("Tower of London",          "London","United Kingdom","history",    4.7, 35.0, 4,  51.5081,  -0.0759),
    ("British Museum",           "London","United Kingdom","history",    4.7,  0.0, 4,  51.5194,  -0.1269),
    ("Buckingham Palace",        "London","United Kingdom","history",    4.6,  0.0, 4,  51.5014,  -0.1419),
    ("Hyde Park",                "London","United Kingdom","nature",     4.7,  0.0, 4,  51.5073,  -0.1657),
    ("Tate Modern",              "London","United Kingdom","history",    4.6,  0.0, 3,  51.5076,  -0.0994),
    ("Camden Market",            "London","United Kingdom","shopping",   4.3,  0.0, 3,  51.5418,  -0.1477),
    ("Borough Market",           "London","United Kingdom","food",       4.6,  0.0, 4,  51.5055,  -0.0910),
    ("Greenwich Park",           "London","United Kingdom","nature",     4.6,  0.0, 3,  51.4777,  -0.0001),

    # Rome, Italy
    ("Colosseum",                "Rome","Italy","history",    4.7, 16.0, 4,  41.8902,  12.4922),
    ("Vatican Museums",          "Rome","Italy","history",    4.7, 17.0, 4,  41.9065,  12.4536),
    ("Trevi Fountain",           "Rome","Italy","history",    4.7,  0.0, 4,  41.9009,  12.4833),
    ("Pantheon",                 "Rome","Italy","history",    4.8,  5.0, 4,  41.8986,  12.4769),
    ("Borghese Gallery",         "Rome","Italy","history",    4.8, 15.0, 4,  41.9141,  12.4924),
    ("Trastevere Quarter",       "Rome","Italy","food",       4.5,  0.0, 3,  41.8896,  12.4690),
    ("Campo de Fiori",           "Rome","Italy","food",       4.4,  0.0, 3,  41.8956,  12.4722),
    ("Villa Borghese",           "Rome","Italy","nature",     4.6,  0.0, 3,  41.9141,  12.4924),

    # Florence, Italy
    ("Uffizi Gallery",           "Florence","Italy","history",  4.7, 20.0, 4,  43.7681,  11.2556),
    ("Duomo Cathedral Florence", "Florence","Italy","history",  4.8,  0.0, 4,  43.7732,  11.2560),
    ("Ponte Vecchio",            "Florence","Italy","history",  4.6,  0.0, 4,  43.7680,  11.2531),
    ("Piazzale Michelangelo",    "Florence","Italy","nature",   4.7,  0.0, 3,  43.7628,  11.2650),
    ("Boboli Gardens",           "Florence","Italy","nature",   4.5,  8.0, 3,  43.7638,  11.2490),
    ("Mercato Centrale Florence","Florence","Italy","food",     4.5,  0.0, 3,  43.7768,  11.2529),
    ("Galleria dell'Accademia",  "Florence","Italy","history",  4.6, 12.0, 3,  43.7768,  11.2586),
    ("San Miniato al Monte",     "Florence","Italy","history",  4.7,  0.0, 3,  43.7589,  11.2650),

    # Barcelona, Spain
    ("Sagrada Familia",          "Barcelona","Spain","history",    4.8, 26.0, 4,  41.4036,   2.1744),
    ("Park Guell",               "Barcelona","Spain","nature",     4.6, 10.0, 4,  41.4145,   2.1527),
    ("La Rambla",                "Barcelona","Spain","shopping",   4.3,  0.0, 4,  41.3797,   2.1740),
    ("Gothic Quarter Barcelona", "Barcelona","Spain","history",    4.5,  0.0, 3,  41.3833,   2.1760),
    ("Barceloneta Beach",        "Barcelona","Spain","relaxation", 4.4,  0.0, 4,  41.3809,   2.1897),
    ("Camp Nou Stadium",         "Barcelona","Spain","history",    4.5, 28.0, 4,  41.3809,   2.1228),
    ("La Boqueria Market",       "Barcelona","Spain","food",       4.4,  0.0, 4,  41.3817,   2.1719),
    ("Palau de la Musica",       "Barcelona","Spain","history",    4.7, 22.0, 3,  41.3875,   2.1753),

    # Amsterdam, Netherlands
    ("Anne Frank House",         "Amsterdam","Netherlands","history",    4.7, 16.0, 4,  52.3752,   4.8840),
    ("Rijksmuseum",              "Amsterdam","Netherlands","history",    4.8, 22.5, 4,  52.3600,   4.8852),
    ("Van Gogh Museum",          "Amsterdam","Netherlands","history",    4.7, 20.0, 4,  52.3584,   4.8811),
    ("Vondelpark",               "Amsterdam","Netherlands","nature",     4.7,  0.0, 3,  52.3580,   4.8686),
    ("Canal Ring Cruise",        "Amsterdam","Netherlands","relaxation", 4.5, 15.0, 3,  52.3676,   4.9041),
    ("Jordaan District",         "Amsterdam","Netherlands","shopping",   4.5,  0.0, 3,  52.3745,   4.8832),
    ("Heineken Experience",      "Amsterdam","Netherlands","food",       4.3, 23.0, 3,  52.3578,   4.8924),
    ("Albert Cuyp Market",       "Amsterdam","Netherlands","food",       4.4,  0.0, 3,  52.3556,   4.8972),

    # Prague, Czech Republic
    ("Prague Castle",            "Prague","Czech Republic","history",    4.7, 15.0, 4,  50.0906,  14.4006),
    ("Charles Bridge",           "Prague","Czech Republic","history",    4.7,  0.0, 4,  50.0865,  14.4114),
    ("Old Town Square Prague",   "Prague","Czech Republic","history",    4.6,  0.0, 4,  50.0873,  14.4213),
    ("Prague Jewish Quarter",    "Prague","Czech Republic","history",    4.6, 14.0, 3,  50.0901,  14.4178),
    ("Wenceslas Square",         "Prague","Czech Republic","shopping",   4.3,  0.0, 3,  50.0811,  14.4278),
    ("Petrin Hill",              "Prague","Czech Republic","nature",     4.6,  0.0, 3,  50.0823,  14.3991),
    ("Prague Beer Gardens",      "Prague","Czech Republic","food",       4.4,  0.0, 3,  50.0804,  14.4276),
    ("Vysehrad Citadel",         "Prague","Czech Republic","history",    4.5,  0.0, 3,  50.0643,  14.4183),

    # Berlin, Germany
    ("Brandenburg Gate",         "Berlin","Germany","history",    4.7,  0.0, 4,  52.5163,  13.3777),
    ("Berlin Wall Memorial",     "Berlin","Germany","history",    4.6,  0.0, 4,  52.5351,  13.3900),
    ("Museum Island Berlin",     "Berlin","Germany","history",    4.7, 18.0, 4,  52.5169,  13.4015),
    ("Reichstag Building",       "Berlin","Germany","history",    4.6,  0.0, 4,  52.5186,  13.3762),
    ("East Side Gallery",        "Berlin","Germany","history",    4.6,  0.0, 3,  52.5051,  13.4393),
    ("Tiergarten Park",          "Berlin","Germany","nature",     4.6,  0.0, 3,  52.5145,  13.3501),
    ("Checkpoint Charlie",       "Berlin","Germany","history",    4.3,  0.0, 3,  52.5076,  13.3904),
    ("Hackescher Markt",         "Berlin","Germany","shopping",   4.3,  0.0, 3,  52.5232,  13.4022),

    # Vienna, Austria
    ("Schonbrunn Palace",        "Vienna","Austria","history",    4.8, 22.0, 4,  48.1845,  16.3122),
    ("St Stephen's Cathedral",   "Vienna","Austria","history",    4.7,  0.0, 4,  48.2082,  16.3738),
    ("Kunsthistorisches Museum", "Vienna","Austria","history",    4.7, 16.0, 4,  48.2032,  16.3614),
    ("Vienna State Opera",       "Vienna","Austria","relaxation", 4.7, 10.0, 4,  48.2030,  16.3694),
    ("Prater Ferris Wheel",      "Vienna","Austria","adventure",  4.4,  5.0, 3,  48.2169,  16.3967),
    ("Naschmarkt Vienna",        "Vienna","Austria","food",       4.4,  0.0, 3,  48.1983,  16.3644),
    ("Belvedere Palace",         "Vienna","Austria","history",    4.7, 16.0, 3,  48.1918,  16.3806),
    ("Vienna Woods",             "Vienna","Austria","nature",     4.5,  0.0, 3,  48.2000,  16.1600),

    # Athens, Greece
    ("Acropolis of Athens",      "Athens","Greece","history",    4.8, 20.0, 4,  37.9715,  23.7257),
    ("Parthenon",                "Athens","Greece","history",    4.7,  0.0, 4,  37.9715,  23.7268),
    ("Athens National Museum",   "Athens","Greece","history",    4.7,  8.0, 3,  37.9897,  23.7322),
    ("Plaka Old Town",           "Athens","Greece","food",       4.4,  0.0, 3,  37.9731,  23.7295),
    ("Monastiraki Flea Market",  "Athens","Greece","shopping",   4.3,  0.0, 3,  37.9758,  23.7244),
    ("Cape Sounion",             "Athens","Greece","history",    4.6, 10.0, 3,  37.6524,  24.0256),
    ("Lycabettus Hill",          "Athens","Greece","nature",     4.6,  0.0, 3,  37.9797,  23.7441),
    ("Athens Riviera Beach",     "Athens","Greece","relaxation", 4.3,  0.0, 3,  37.9297,  23.7000),

    # Lisbon, Portugal
    ("Belem Tower",              "Lisbon","Portugal","history",    4.6, 10.0, 4,  38.6916,  -9.2160),
    ("Jeronimos Monastery",      "Lisbon","Portugal","history",    4.7,  8.0, 4,  38.6979,  -9.2066),
    ("Alfama District",          "Lisbon","Portugal","history",    4.5,  0.0, 4,  38.7138,  -9.1324),
    ("Sintra Palace",            "Lisbon","Portugal","history",    4.7, 14.0, 4,  38.7877,  -9.3906),
    ("Time Out Market Lisbon",   "Lisbon","Portugal","food",       4.5,  0.0, 3,  38.7065,  -9.1452),
    ("LX Factory Market",        "Lisbon","Portugal","shopping",   4.5,  0.0, 3,  38.7018,  -9.1780),
    ("Castelo de Sao Jorge",     "Lisbon","Portugal","history",    4.5, 10.0, 3,  38.7139,  -9.1335),
    ("Cascais Coastal Town",     "Lisbon","Portugal","relaxation", 4.6,  0.0, 3,  38.6979,  -9.4215),

    # ═══════════════════════════════════
    #  AMERICAS
    # ═══════════════════════════════════

    # New York, United States
    ("Central Park",             "New York","United States","nature",    4.8,  0.0, 4,  40.7851,  -73.9683),
    ("Times Square",             "New York","United States","shopping",  4.3,  0.0, 4,  40.7580,  -73.9855),
    ("Metropolitan Museum",      "New York","United States","history",   4.8, 25.0, 4,  40.7794,  -73.9632),
    ("Brooklyn Bridge",          "New York","United States","history",   4.8,  0.0, 4,  40.7061,  -73.9969),
    ("High Line Park",           "New York","United States","nature",    4.6,  0.0, 3,  40.7479,  -74.0048),
    ("Chelsea Market",           "New York","United States","food",      4.5,  0.0, 3,  40.7424,  -74.0059),
    ("Empire State Building",    "New York","United States","history",   4.7, 42.0, 4,  40.7484,  -73.9857),
    ("Statue of Liberty",        "New York","United States","history",   4.7, 24.0, 4,  40.6892,  -74.0445),

    # Los Angeles, United States
    ("Hollywood Walk of Fame",   "Los Angeles","United States","history",    4.3,  0.0, 4,  34.1016, -118.3267),
    ("Griffith Observatory",     "Los Angeles","United States","nature",     4.7,  0.0, 4,  34.1184, -118.3004),
    ("Santa Monica Pier",        "Los Angeles","United States","relaxation", 4.5,  0.0, 4,  34.0095, -118.4975),
    ("Universal Studios Hollywood","Los Angeles","United States","adventure",4.5, 90.0, 4,  34.1381,-118.3534),
    ("Venice Beach Boardwalk",   "Los Angeles","United States","relaxation", 4.4,  0.0, 3,  33.9850, -118.4695),
    ("The Getty Center",         "Los Angeles","United States","history",    4.7,  0.0, 3,  34.0780, -118.4741),
    ("Rodeo Drive",              "Los Angeles","United States","shopping",   4.4,  0.0, 4,  34.0668, -118.4002),
    ("Disneyland Anaheim",       "Los Angeles","United States","adventure",  4.7,109.0, 4,  33.8121, -117.9190),

    # Toronto, Canada
    ("CN Tower",                 "Toronto","Canada","history",    4.7, 38.0, 4,  43.6426,  -79.3871),
    ("Niagara Falls",            "Toronto","Canada","nature",     4.9, 12.0, 4,  43.0896,  -79.0849),
    ("Royal Ontario Museum",     "Toronto","Canada","history",    4.6, 20.0, 3,  43.6677,  -79.3945),
    ("Kensington Market Toronto","Toronto","Canada","shopping",   4.4,  0.0, 3,  43.6543,  -79.4022),
    ("Distillery District",      "Toronto","Canada","food",       4.5,  0.0, 3,  43.6503,  -79.3596),
    ("Toronto Islands",          "Toronto","Canada","nature",     4.6,  8.0, 3,  43.6228,  -79.3817),
    ("St Lawrence Market",       "Toronto","Canada","food",       4.5,  0.0, 3,  43.6487,  -79.3716),
    ("Casa Loma Castle",         "Toronto","Canada","history",    4.5, 28.0, 3,  43.6780,  -79.4094),

    # Rio de Janeiro, Brazil
    ("Christ the Redeemer",      "Rio de Janeiro","Brazil","history",    4.7, 22.0, 4, -22.9519,  -43.2105),
    ("Copacabana Beach",         "Rio de Janeiro","Brazil","relaxation", 4.6,  0.0, 4, -22.9711,  -43.1822),
    ("Sugarloaf Mountain",       "Rio de Janeiro","Brazil","nature",     4.7, 30.0, 4, -22.9490,  -43.1546),
    ("Ipanema Beach",            "Rio de Janeiro","Brazil","relaxation", 4.6,  0.0, 3, -22.9868,  -43.2028),
    ("Lapa Arches",              "Rio de Janeiro","Brazil","history",    4.5,  0.0, 3, -22.9110,  -43.1806),
    ("Santa Teresa District",    "Rio de Janeiro","Brazil","history",    4.5,  0.0, 3, -22.9236,  -43.1882),
    ("Botanical Garden Rio",     "Rio de Janeiro","Brazil","nature",     4.7,  7.0, 3, -22.9672,  -43.2232),
    ("Maracana Stadium",         "Rio de Janeiro","Brazil","history",    4.4, 18.0, 3, -22.9121,  -43.2302),

    # Buenos Aires, Argentina
    ("La Boca and Caminito",     "Buenos Aires","Argentina","history",    4.5,  0.0, 4, -34.6345,  -58.3630),
    ("Recoleta Cemetery",        "Buenos Aires","Argentina","history",    4.6,  0.0, 3, -34.5875,  -58.3927),
    ("San Telmo Market",         "Buenos Aires","Argentina","food",       4.5,  0.0, 3, -34.6214,  -58.3731),
    ("Plaza de Mayo",            "Buenos Aires","Argentina","history",    4.4,  0.0, 3, -34.6083,  -58.3712),
    ("Teatro Colon",             "Buenos Aires","Argentina","history",    4.7, 15.0, 3, -34.6008,  -58.3833),
    ("Palermo Parks",            "Buenos Aires","Argentina","nature",     4.5,  0.0, 3, -34.5763,  -58.4190),
    ("Tigre Delta",              "Buenos Aires","Argentina","nature",     4.5, 10.0, 3, -34.4269,  -58.5797),
    ("Tango Show Buenos Aires",  "Buenos Aires","Argentina","relaxation", 4.7, 40.0, 3, -34.6158,  -58.3731),

    # ═══════════════════════════════════
    #  AFRICA & OCEANIA
    # ═══════════════════════════════════

    # Sydney, Australia
    ("Sydney Opera House",       "Sydney","Australia","history",    4.7, 40.0, 4, -33.8568, 151.2153),
    ("Bondi Beach",              "Sydney","Australia","relaxation", 4.6,  0.0, 4, -33.8915, 151.2767),
    ("Taronga Zoo",              "Sydney","Australia","nature",     4.7, 50.0, 4, -33.8432, 151.2415),
    ("The Rocks",                "Sydney","Australia","history",    4.4,  0.0, 3, -33.8599, 151.2090),
    ("Darling Harbour",          "Sydney","Australia","food",       4.3,  0.0, 3, -33.8733, 151.1983),
    ("Blue Mountains",           "Sydney","Australia","nature",     4.8, 12.0, 4, -33.7036, 150.3124),
    ("Manly Beach",              "Sydney","Australia","relaxation", 4.6,  0.0, 3, -33.7969, 151.2876),
    ("Royal Botanic Garden",     "Sydney","Australia","nature",     4.7,  0.0, 3, -33.8642, 151.2166),

    # Melbourne, Australia
    ("Federation Square",        "Melbourne","Australia","history",    4.3,  0.0, 3, -37.8179, 144.9690),
    ("Royal Botanic Gardens Mel","Melbourne","Australia","nature",     4.7,  0.0, 3, -37.8304, 144.9797),
    ("Queen Victoria Market",    "Melbourne","Australia","food",       4.5,  0.0, 4, -37.8073, 144.9566),
    ("MCG Cricket Ground",       "Melbourne","Australia","history",    4.6, 25.0, 3, -37.8200, 144.9836),
    ("Great Ocean Road",         "Melbourne","Australia","nature",     4.9,  0.0, 4, -38.6800, 143.3900),
    ("St Kilda Beach",           "Melbourne","Australia","relaxation", 4.4,  0.0, 3, -37.8676, 144.9798),
    ("Fitzroy Street Market",    "Melbourne","Australia","shopping",   4.4,  0.0, 2, -37.8700, 144.9800),
    ("National Gallery Victoria","Melbourne","Australia","history",    4.7,  0.0, 3, -37.8225, 144.9686),

    # Cape Town, South Africa
    ("Table Mountain",           "Cape Town","South Africa","nature",    4.8, 20.0, 4, -33.9628,  18.4098),
    ("Robben Island",            "Cape Town","South Africa","history",   4.6, 25.0, 3, -33.8032,  18.3665),
    ("V&A Waterfront",           "Cape Town","South Africa","shopping",  4.6,  0.0, 4, -33.9019,  18.4216),
    ("Boulders Beach Penguins",  "Cape Town","South Africa","nature",    4.7, 10.0, 3, -34.1966,  18.4528),
    ("Cape Point",               "Cape Town","South Africa","nature",    4.7, 15.0, 3, -34.3566,  18.4969),
    ("Kirstenbosch Garden",      "Cape Town","South Africa","nature",    4.7, 12.0, 3, -33.9877,  18.4326),
    ("Bo-Kaap Quarter",          "Cape Town","South Africa","history",   4.5,  0.0, 3, -33.9241,  18.4162),
    ("Cape Winelands",           "Cape Town","South Africa","food",      4.8, 15.0, 3, -33.9321,  18.8602),

    # Cairo, Egypt
    ("Pyramids of Giza",         "Cairo","Egypt","history",    4.8, 12.0, 4,  29.9792,  31.1342),
    ("Egyptian Museum",          "Cairo","Egypt","history",    4.6, 10.0, 4,  30.0478,  31.2336),
    ("Khan el-Khalili Bazaar",   "Cairo","Egypt","shopping",   4.4,  0.0, 3,  30.0478,  31.2619),
    ("Sphinx of Giza",           "Cairo","Egypt","history",    4.7,  0.0, 4,  29.9753,  31.1376),
    ("Al-Azhar Mosque",          "Cairo","Egypt","history",    4.5,  0.0, 3,  30.0455,  31.2626),
    ("Nile River Cruise Cairo",  "Cairo","Egypt","relaxation", 4.5, 20.0, 3,  30.0444,  31.2357),
    ("Citadel of Cairo",         "Cairo","Egypt","history",    4.6,  8.0, 3,  30.0285,  31.2600),
    ("Memphis and Saqqara",      "Cairo","Egypt","history",    4.6, 10.0, 3,  29.8710,  31.2169),

    # Marrakech, Morocco
    ("Djemaa el-Fna Square",     "Marrakech","Morocco","food",       4.5,  0.0, 4,  31.6260,  -7.9892),
    ("Majorelle Garden",         "Marrakech","Morocco","nature",     4.6,  7.0, 4,  31.6425,  -8.0040),
    ("Medina Souks",             "Marrakech","Morocco","shopping",   4.4,  0.0, 4,  31.6295,  -7.9868),
    ("Bahia Palace",             "Marrakech","Morocco","history",    4.5,  2.0, 3,  31.6213,  -7.9846),
    ("Saadian Tombs",            "Marrakech","Morocco","history",    4.4,  1.0, 3,  31.6173,  -7.9891),
    ("Ben Youssef Madrasa",      "Marrakech","Morocco","history",    4.4,  3.0, 3,  31.6340,  -7.9876),
    ("Koutoubia Mosque",         "Marrakech","Morocco","history",    4.4,  0.0, 3,  31.6238,  -7.9939),
    ("Atlas Mountains Day Trip", "Marrakech","Morocco","adventure",  4.7, 30.0, 3,  31.4200,  -7.7000),
]


def seed_from_api(app):
    """Fetch live attractions from Google Places for all 6 featured cities."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return False

    os.environ["GOOGLE_API_KEY"] = api_key
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from fetch_attractions import build_attraction_records

    with app.app_context():
        total = 0
        for city, country, lat, lon in FEATURED_CITIES:
            existing = Attraction.query.filter(Attraction.city.ilike(f"%{city}%")).count()
            if existing >= 5:
                print(f"  {city}: {existing} attractions already in DB. Skipping.")
                continue

            print(f"  Fetching {city} from Google Places...", end=" ", flush=True)
            try:
                records = build_attraction_records(city_name=city, lat=lat, lon=lon, country=country)
                added = 0
                for r in records:
                    if not Attraction.query.filter_by(name=r["name"], city=r["city"]).first():
                        att = Attraction(
                            name=r["name"], city=r["city"], country=r["country"],
                            category=r["category"], rating=r["rating"],
                            entry_cost=r["entry_cost"], popularity_score=r["popularity_score"],
                            latitude=r["latitude"], longitude=r["longitude"],
                            photo_reference=r.get("photo_reference"),
                        )
                        db.session.add(att)
                        added += 1
                db.session.commit()
                print(f"{added} added.")
                total += added
            except Exception as e:
                print(f"Failed ({e})")
        print(f"\nGoogle Places seed complete. {total} new attractions added.")
    return True


def seed_synthetic(app):
    """Insert hardcoded synthetic attractions for cities that have no real API data yet.

    Skips any city that already has 5+ attractions in the DB so that real
    Google Places data is never overwritten with synthetic placeholders.
    """
    with app.app_context():
        city_has_data: dict[str, bool] = {}
        added = 0

        for row in SYNTHETIC_ATTRACTIONS:
            name, city, country, category, rating, cost, pop, lat, lng = row

            # Cache the check per city to avoid N+1 queries
            if city not in city_has_data:
                count = Attraction.query.filter(
                    Attraction.city.ilike(f"%{city}%")
                ).count()
                city_has_data[city] = count >= 5

            if city_has_data[city]:
                continue  # real API data already present — skip synthetic rows

            if not Attraction.query.filter_by(name=name, city=city).first():
                att = Attraction(
                    name=name, city=city, country=country,
                    category=category, rating=rating,
                    entry_cost=cost, popularity_score=pop,
                    latitude=lat, longitude=lng,
                    photo_reference=None,
                )
                db.session.add(att)
                added += 1

        db.session.commit()
        skipped = [c for c, has in city_has_data.items() if has]
        if skipped:
            print(f"  Skipped {len(skipped)} cities already seeded by Google API.")
        print(f"  Synthetic attractions added: {added}")


if __name__ == "__main__":
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key and api_key != "your_google_api_key_here":
        print("Google API key found. Fetching real attraction data for featured cities...")
        seed_from_api(flask_app)

    # Always seed synthetic data — fills all 41 cities, skips rows already in DB
    print("\nSeeding synthetic attractions for all cities...")
    seed_synthetic(flask_app)

    with flask_app.app_context():
        from sqlalchemy import func
        cities = db.session.query(Attraction.city, Attraction.country, func.count())\
            .group_by(Attraction.city, Attraction.country)\
            .order_by(Attraction.country).all()
        total = sum(c[2] for c in cities)
        print(f"\n{len(cities)} cities / {total} attractions now in DB.")

    print("\nDone. Next: python scripts/generate_synthetic_data.py")
