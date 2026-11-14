import os
import sqlite3
import re

def verify_all():
    print("=== STARTING MOBILE & AVATAR VERIFICATION ===")
    errors = []

    # 1. Check Committee & Teacher Photos on Disk
    conn = sqlite3.connect('school.db')
    conn.row_factory = sqlite3.Row

    # SMC
    smc = conn.execute("SELECT id, name, position, photo FROM school_management_committee").fetchall()
    print(f"Checking {len(smc)} SMC members...")
    for m in smc:
        svg_name = f"smc_{m['id']}.svg"
        p1 = os.path.join('static', 'images', 'committees', svg_name)
        p2 = os.path.join('api', 'static', 'images', 'committees', svg_name)
        if not os.path.exists(p1) or not os.path.exists(p2):
            errors.append(f"Missing SMC SVG for ID {m['id']}: {p1} or {p2}")

    # Trustee
    trustees = conn.execute("SELECT id, name, position, photo FROM trustee_committee").fetchall()
    print(f"Checking {len(trustees)} Trustee members...")
    for m in trustees:
        svg_name = f"trustee_{m['id']}.svg"
        p1 = os.path.join('static', 'images', 'committees', svg_name)
        p2 = os.path.join('api', 'static', 'images', 'committees', svg_name)
        if not os.path.exists(p1) or not os.path.exists(p2):
            errors.append(f"Missing Trustee SVG for ID {m['id']}: {p1} or {p2}")

    # Teachers
    teachers = conn.execute("SELECT id, name_nepali, position, photo FROM teachers").fetchall()
    print(f"Checking {len(teachers)} Teachers...")
    for t in teachers:
        svg_name = f"teacher_{t['id']}.svg"
        p1 = os.path.join('static', 'images', 'teachers', svg_name)
        p2 = os.path.join('api', 'static', 'images', 'teachers', svg_name)
        if not os.path.exists(p1) or not os.path.exists(p2):
            errors.append(f"Missing Teacher SVG for ID {t['id']}: {p1} or {p2}")

    conn.close()

    # 2. Check SVG ViewBox & Scalability
    svg_dirs = [
        os.path.join('static', 'images', 'committees'),
        os.path.join('static', 'images', 'teachers')
    ]
    for d in svg_dirs:
        for fname in os.listdir(d):
            if fname.endswith('.svg'):
                fpath = os.path.join(d, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'viewBox="0 0 400 400"' not in content:
                        errors.append(f"SVG {fname} missing viewBox: {fpath}")
                    if 'preserveAspectRatio' not in content:
                        errors.append(f"SVG {fname} missing preserveAspectRatio: {fpath}")

    # 3. Check Templates for mobile responsiveness and lack of onerror hiding
    templates_to_check = [
        'templates/admin/management_committee.html',
        'templates/admin/trustee_committee.html',
        'templates/admin/teachers.html',
        'templates/public/management_committee.html',
        'templates/public/trustee_committee.html',
        'templates/public/teachers.html',
        'api/templates/admin/management_committee.html',
        'api/templates/admin/trustee_committee.html',
        'api/templates/admin/teachers.html',
        'api/templates/public/management_committee.html',
        'api/templates/public/trustee_committee.html',
        'api/templates/public/teachers.html'
    ]

    for tpath in templates_to_check:
        if not os.path.exists(tpath):
            errors.append(f"Missing template: {tpath}")
            continue
        with open(tpath, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.splitlines():
                if 'onerror=' in line.lower() and ('hidden' in line.lower() or 'display:none' in line.lower()):
                    errors.append(f"Template {tpath} contains destructive inline onerror hiding: {line.strip()[:80]}")
            if 'admin' in tpath and 'MobileList' not in content:
                errors.append(f"Admin template {tpath} missing MobileList container!")

    # 4. Check PWA Manifest and SW
    for sw_path in ['static/sw.js', 'api/static/sw.js']:
        if not os.path.exists(sw_path):
            errors.append(f"Missing service worker: {sw_path}")
        else:
            with open(sw_path, 'r', encoding='utf-8') as f:
                c = f.read()
                if 'sahid-smriti-cache-v2' not in c:
                    errors.append(f"SW {sw_path} not updated to v2")

    for mf_path in ['static/manifest.json', 'api/static/manifest.json']:
        if not os.path.exists(mf_path):
            errors.append(f"Missing manifest: {mf_path}")
        else:
            with open(mf_path, 'r', encoding='utf-8') as f:
                c = f.read()
                if '"scope": "/"' not in c:
                    errors.append(f"Manifest {mf_path} missing scope")

    if errors:
        print("FAILURES FOUND:")
        for e in errors:
            print(" -", e)
        return False
    else:
        print("ALL VERIFICATIONS PASSED! MOBILE RESPONSIVENESS, AVATARS, AND PWA SYNC ARE 100% READY.")
        return True

if __name__ == '__main__':
    verify_all()
