import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import re
from app.routers.admin import admin_management_committee, admin_trustee_committee
from app.routers.public import page_management_committee, page_trustee_committee
from test_committee_feature import build_request

def test_all():
    req = build_request('/admin/management-committee')

    # 1. Admin SMC HTML
    res_admin_smc = admin_management_committee(req)
    html_admin_smc = res_admin_smc.body.decode('utf-8')
    imgs_admin_smc = re.findall(r'<img[^>]+col-photo-img[^>]*>', html_admin_smc)
    print(f'Admin SMC: {len(imgs_admin_smc)} member img tags found (Expected 10)')
    assert len(imgs_admin_smc) >= 10, f'Expected 10 img tags in Admin SMC, found {len(imgs_admin_smc)}'

    # Check that none have hidden class
    for tag in imgs_admin_smc:
        assert 'hidden' not in tag, f'Unexpected hidden in tag: {tag}'

    # 2. Public SMC HTML
    res_pub_smc = page_management_committee(req)
    html_pub_smc = res_pub_smc.body.decode('utf-8')
    imgs_pub_smc = re.findall(r'<img[^>]+member-photo-img[^>]*>', html_pub_smc)
    print(f'Public SMC: {len(imgs_pub_smc)} member img tags found (Expected 10)')
    assert len(imgs_pub_smc) >= 10, f'Expected 10 img tags in Public SMC, found {len(imgs_pub_smc)}'
    for tag in imgs_pub_smc:
        assert 'hidden' not in tag, f'Unexpected hidden in tag: {tag}'

    # 3. Admin Trustee HTML
    res_admin_trustee = admin_trustee_committee(req)
    html_admin_trustee = res_admin_trustee.body.decode('utf-8')
    imgs_admin_trustee = re.findall(r'<img[^>]+col-photo-img[^>]*>', html_admin_trustee)
    print(f'Admin Trustee: {len(imgs_admin_trustee)} member img tags found (Expected 9)')
    assert len(imgs_admin_trustee) >= 9

    # 4. Public Trustee HTML
    res_pub_trustee = page_trustee_committee(req)
    html_pub_trustee = res_pub_trustee.body.decode('utf-8')
    imgs_pub_trustee = re.findall(r'<img[^>]+member-photo-img[^>]*>', html_pub_trustee)
    print(f'Public Trustee: {len(imgs_pub_trustee)} member img tags found (Expected 9)')
    assert len(imgs_pub_trustee) >= 9

    print('\n==================================================')
    print('ALL FRONTEND PHOTO RENDERING CHECKS PASSED 100%!')
    print('==================================================')

if __name__ == '__main__':
    test_all()
