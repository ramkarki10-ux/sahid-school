import os
from pathlib import Path

os.makedirs('static/images/committees', exist_ok=True)
os.makedirs('api/static/images/committees', exist_ok=True)

members_data = [
    # SMC members (IDs 28 through 37)
    {'id': 'smc_28', 'name': 'राम बहादुर कार्की', 'role': 'अध्यक्ष', 'gender': 'M', 'bg': ['#1e3a8a', '#172554'], 'jacket': '#1e293b', 'tie': '#dc2626', 'topi': True},
    {'id': 'smc_29', 'name': 'राम कुमारी चौधरी', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#831843', '#500724'], 'jacket': '#0f172a', 'saree': '#e11d48'},
    {'id': 'smc_30', 'name': 'सन्तोष खतिवडा', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#065f46', '#022c22'], 'jacket': '#334155', 'tie': '#2563eb'},
    {'id': 'smc_31', 'name': 'सूर्य बहादुर थापा', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#9a3412', '#431407'], 'jacket': '#1e293b', 'topi': True},
    {'id': 'smc_32', 'name': 'तीर्थ कुमारी वन', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#701a75', '#4a044e'], 'jacket': '#1f2937', 'saree': '#0284c7'},
    {'id': 'smc_33', 'name': 'पूजा खनाल', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#155e75', '#083344'], 'jacket': '#111827', 'saree': '#d97706'},
    {'id': 'smc_34', 'name': 'कृष्ण गोपाल घिमिरे', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#3730a3', '#1e1b4b'], 'jacket': '#1e293b', 'tie': '#059669'},
    {'id': 'smc_35', 'name': 'राजकुमार आचार्य', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#3f3f46', '#18181b'], 'jacket': '#27272a', 'topi': True},
    {'id': 'smc_36', 'name': 'जमुना भण्डारी', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#854d0e', '#422006'], 'jacket': '#18181b', 'saree': '#9333ea'},
    {'id': 'smc_37', 'name': 'रीता फुयल', 'role': 'सदस्य-सचिव', 'gender': 'F', 'bg': ['#064e3b', '#022c22'], 'jacket': '#0f172a', 'saree': '#dc2626'},
    
    # Trustee members (IDs 1 through 9)
    {'id': 'trustee_1', 'name': 'धर्मशिला चापागाई', 'role': 'गुठियार प्रमुख', 'gender': 'F', 'bg': ['#831843', '#4c0519'], 'jacket': '#1e293b', 'saree': '#e11d48'},
    {'id': 'trustee_2', 'name': 'मणिकुमार साम्पाङ', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#1e3a8a', '#172554'], 'jacket': '#1e293b', 'tie': '#dc2626', 'topi': True},
    {'id': 'trustee_3', 'name': 'राम बहादुर कार्की', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#1e3a8a', '#0f172a'], 'jacket': '#334155', 'topi': True},
    {'id': 'trustee_4', 'name': 'राम कुमारी चौधरी', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#701a75', '#4a044e'], 'jacket': '#0f172a', 'saree': '#e11d48'},
    {'id': 'trustee_5', 'name': 'पूजा खनाल', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#155e75', '#083344'], 'jacket': '#1f2937', 'saree': '#d97706'},
    {'id': 'trustee_6', 'name': 'कृष्ण गोपाल घिमिरे', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#3730a3', '#1e1b4b'], 'jacket': '#1e293b', 'tie': '#059669'},
    {'id': 'trustee_7', 'name': 'केशर बहादुर प्रधान', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#065f46', '#022c22'], 'jacket': '#27272a', 'topi': True},
    {'id': 'trustee_8', 'name': 'मणिराम गिरी', 'role': 'सदस्य', 'gender': 'M', 'bg': ['#9a3412', '#431407'], 'jacket': '#334155', 'tie': '#2563eb'},
    {'id': 'trustee_9', 'name': 'सपना परियार', 'role': 'सदस्य', 'gender': 'F', 'bg': ['#854d0e', '#422006'], 'jacket': '#111827', 'saree': '#0284c7'}
]

def make_svg(m):
    bg1, bg2 = m['bg'][0], m['bg'][1]
    is_f = m['gender'] == 'F'
    skin = '#f5d0b5' if is_f else '#e2b391'
    skin_shadow = '#e4bc9f' if is_f else '#cc9c78'
    hair_color = '#1c1917'
    jacket = m.get('jacket', '#1e293b')
    accent = m.get('saree' if is_f else 'tie', '#dc2626')
    topi = m.get('topi', False)
    
    topi_markup = ''
    if topi:
        topi_markup = '''
        <!-- Nepali Dhaka Topi -->
        <path d="M 145 130 L 155 70 L 225 65 L 255 125 Z" fill="#b91c1c" stroke="#f59e0b" stroke-width="2"/>
        <polygon points="155,70 185,67 180,95 152,95" fill="#991b1b"/>
        <polygon points="185,67 225,65 220,95 180,95" fill="#b91c1c"/>
        <polygon points="225,65 255,125 240,125 220,95" fill="#7f1d1d"/>
        <path d="M 145 125 Q 200 135 255 120" stroke="#fbbf24" stroke-width="3" fill="none"/>
        '''

    hair_markup = ''
    if is_f:
        hair_markup = f'''
        <!-- Female Hair (Bun & Sides) -->
        <circle cx="200" cy="140" r="82" fill="{hair_color}"/>
        <ellipse cx="200" cy="90" rx="50" ry="35" fill="{hair_color}"/>
        <path d="M 125 150 Q 120 220 145 250 Q 160 210 160 170 Z" fill="{hair_color}"/>
        <path d="M 275 150 Q 280 220 255 250 Q 240 210 240 170 Z" fill="{hair_color}"/>
        '''
    else:
        if not topi:
            hair_markup = f'''
            <!-- Male Hair -->
            <path d="M 130 150 Q 130 90 200 85 Q 270 90 270 150 Q 250 110 200 110 Q 150 110 130 150 Z" fill="{hair_color}"/>
            '''

    chest_clothing = ''
    if is_f:
        chest_clothing = f'''
        <!-- Female Blouse & Saree / Coat -->
        <path d="M 110 400 L 140 260 L 260 260 L 290 400 Z" fill="{jacket}"/>
        <!-- Saree Pallu across shoulder -->
        <path d="M 120 400 L 155 260 L 220 260 L 170 400 Z" fill="{accent}" opacity="0.95"/>
        <path d="M 155 260 Q 200 290 245 260" stroke="#fbbf24" stroke-width="3" fill="none"/>
        '''
    else:
        chest_clothing = f'''
        <!-- Male Suit Coat & Shirt & Tie -->
        <path d="M 100 400 L 140 250 L 260 250 L 300 400 Z" fill="{jacket}"/>
        <!-- Shirt V -->
        <polygon points="170,250 230,250 200,320" fill="#ffffff"/>
        <!-- Tie -->
        <polygon points="195,270 205,270 208,350 200,365 192,350" fill="{accent}"/>
        <!-- Lapels -->
        <polygon points="140,250 170,250 185,340 150,330" fill="{jacket}" stroke="#0f172a" stroke-width="1"/>
        <polygon points="260,250 230,250 215,340 250,330" fill="{jacket}" stroke="#0f172a" stroke-width="1"/>
        '''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
  <defs>
    <linearGradient id="grad_{m['id']}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg1}" />
      <stop offset="100%" stop-color="{bg2}" />
    </linearGradient>
    <filter id="shadow_{m['id']}" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000" flood-opacity="0.35" />
    </filter>
  </defs>

  <!-- Background Canvas -->
  <rect width="400" height="400" fill="url(#grad_{m['id']})" />
  <circle cx="200" cy="200" r="170" fill="none" stroke="#ffffff" stroke-width="2" stroke-opacity="0.1" />

  <!-- Avatar Group -->
  <g filter="url(#shadow_{m['id']})">
    {hair_markup}

    <!-- Neck -->
    <rect x="175" y="215" width="50" height="45" rx="6" fill="{skin_shadow}" />

    <!-- Face Oval -->
    <ellipse cx="200" cy="165" rx="55" ry="65" fill="{skin}" />

    {topi_markup}

    <!-- Ears -->
    <ellipse cx="145" cy="165" rx="9" ry="16" fill="{skin_shadow}" />
    <ellipse cx="255" cy="165" rx="9" ry="16" fill="{skin_shadow}" />

    <!-- Eyebrows -->
    <path d="M 165 142 Q 180 138 190 144" stroke="#292524" stroke-width="3" stroke-linecap="round" fill="none" />
    <path d="M 235 142 Q 220 138 210 144" stroke="#292524" stroke-width="3" stroke-linecap="round" fill="none" />

    <!-- Eyes -->
    <ellipse cx="177" cy="153" rx="6" ry="4" fill="#1c1917" />
    <circle cx="179" cy="151" r="1.5" fill="#ffffff" />
    <ellipse cx="223" cy="153" rx="6" ry="4" fill="#1c1917" />
    <circle cx="225" cy="151" r="1.5" fill="#ffffff" />

    <!-- Nose -->
    <path d="M 200 152 L 200 175 L 206 177" stroke="{skin_shadow}" stroke-width="2.5" stroke-linecap="round" fill="none" />

    <!-- Smile / Lips -->
    <path d="M 184 193 Q 200 205 216 193" stroke="{'#be123c' if is_f else '#991b1b'}" stroke-width="{'3.5' if is_f else '2.5'}" stroke-linecap="round" fill="none" />

    {chest_clothing}
  </g>

  <!-- Bottom Badge: School Initial / Role -->
  <rect x="20" y="340" width="360" height="45" rx="10" fill="#0f172a" fill-opacity="0.85" />
  <text x="200" y="368" font-family="sans-serif" font-size="15" font-weight="bold" fill="#f8fafc" text-anchor="middle">{m['name']}</text>
</svg>'''
    return svg

def run():
    for m in members_data:
        svg_content = make_svg(m)
        for p in [f'static/images/committees/{m["id"]}.svg', f'api/static/images/committees/{m["id"]}.svg']:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(svg_content)
        print(f'Generated {m["id"]}.svg')

if __name__ == '__main__':
    run()

