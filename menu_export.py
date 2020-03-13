import json
import requests
from collections import defaultdict, namedtuple
from pprint import pprint

Category = namedtuple('Category', ['uuid', 'name'])
Bundle = namedtuple('Bundle', ['uuid', 'name'])
Item = namedtuple('Item', ['uuid', 'name'])
ItemType = namedtuple('ItemType', ['uuid', 'name'])


def call_api(url, headers):
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    resp_json = resp.json()
    return resp_json

def get_categories(tenant_uuid, store_uuid, menu_uuid):
    pass

def get_menu(tenant_uuid, store_uuid, source):
    pass

def get_menu_category_uuids(tenant_uuid, store_uuid):
    url = 'https://vmos2.vmos.io/catalog/menu'
    headers = {
        'store': store_uuid,
        'tenant': tenant_uuid,
        'x-requested-from': 'online',
    }

    resp_json = call_api(url, headers)
    menu_category_uuids = {}
    for m in resp_json['payload']:
        menu_uuid = m['uuid']
        menu_category_uuids[menu_uuid] = [c['uuid'] for c in m['categories']]
        print("Adding categories: {}".format(', '.join(c['name'] for c in m['categories'])))

    return menu_category_uuids

def get_bundles_from_menu_categories(tenant_uuid, store_uuid, menu_category_uuids, source):
    category_url_fmt = 'https://vmos2.vmos.io/catalog/categories/{}/bundles'

    all_bundles = set()
    for menu_uuid, category_uuids in menu_category_uuids.items():
        for category_uuid in category_uuids:
            headers = {
                'tenant': tenant_uuid,
                'store': store_uuid,
                'menu': menu_uuid,
                'x-requested-from': source,
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
            }

            url = category_url_fmt.format(category_uuid)
            resp_json = call_api(url, headers)
            
            for ic in resp_json['payload']['categories']:
                for b in ic['bundles']:
                    key = (b['uuid'], b['name'], menu_uuid)
                    all_bundles.add(key)

            for ib in resp_json['payload']['bundles']:
                key = (ib['uuid'], ib['name'], menu_uuid)
                all_bundles.add(key)

    print("Got {} bundles".format(len(all_bundles)))
    return all_bundles


def get_items_from_bundles(tenant_uuid, store_uuid, all_bundles, source):
    bundle_url_fmt = 'https://vmos2.vmos.io/catalog/bundles/{}/item-types'

    all_items = {}
    for bundle_uuid, bundle_name, menu_uuid in all_bundles:
        headers = {
            'TENANT': tenant_uuid,
            'STORE': store_uuid,
            'MENU': menu_uuid,
            'x-requested-from': source,
        }
        url = bundle_url_fmt.format(bundle_uuid)
        resp_json = call_api(url, headers)
        
        for ib in resp_json['payload']:
            for i in ib['items']:
                if len(i['customizations']) > 0 and len(i['customizations'][0]['variations']) > 0:
                    for var in i['customizations'][0]['variations']:
                        if var['name']:
                            pass
                
                item_name = i['name']
                if i['type'] == 'BUNDLE_BASE':
                    item_name = bundle_name
                else:
                    item_name = item_name + ' MEAL MODIFIER'
                all_items[i['itemUUID']] = (item_name, i['taxExempt'])

    print("Got {} items".format(len(all_items)))

    return all_items

def get_items_csv(all_items):
    ret = "============================\n\n"
    ret += "name;id\n"
    for uuid, (name, tax_exempt) in all_items.items():
        if not name:
            continue

        ret += '"{}";{}\n'.format(name, uuid)

    return ret


def get_bundles_from_category(tenant_uuid, store_uuid, menu_uuid, category_uuid, source):
    category_url_fmt = 'https://vmos2.vmos.io/catalog/categories/{}/bundles'

    headers = {
        'tenant': tenant_uuid,
        'store': store_uuid,
        'menu': menu_uuid,
        'x-requested-from': source,
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
    }

    url = category_url_fmt.format(category_uuid)
    resp_json = call_api(url, headers)

    bundles = []
    for ic in resp_json['payload']['categories']:
        for b in ic['bundles']:
            key = (b['name'], b['uuid'])
            bundles.append(key)

    for ib in resp_json['payload']['bundles']:
        key = (ib['name'], ib['uuid'])
        bundles.append(key)

    return bundles


def get_items_from_bundle(tenant_uuid, store_uuid, menu_uuid, category_uuid, bundle_uuid, source):
    bundle_url_fmt = 'https://vmos2.vmos.io/catalog/bundles/{}/item-types'

    item_types = {}
    headers = {
        'TENANT': tenant_uuid,
        'STORE': store_uuid,
        'MENU': menu_uuid,
        'x-requested-from': source,
    }
    url = bundle_url_fmt.format(bundle_uuid)
    resp_json = call_api(url, headers)
    for item_type in resp_json['payload']:
        item_type_key = (item_type['name'], item_type['uuid'])
        item_types[item_type_key] = {}

        for item in item_type['items']:
            item_key = (item['name'], item['itemUUID'])

            customizations = []
            for customization in item['customizations']:
                customization_type = customization['type']
                for variation in customization['variations']:
                    customization = (customization_type, variation['name'], str(variation['price']))

                    customizations.append(" - ".join(customization))


            item_types[item_type_key][item_key] = customizations

    return item_types

def stringify_keys(d):
    if type(d) == dict:
        new_d = {}
        for k, v in d.items():
            if type(k) == tuple:
                k = ['' if x is None else x for x in k]
                new_k = " - ".join(k)
            else:
                new_k = k
            
            new_d[new_k] = stringify_keys(v)

        return new_d

    else:
        return d


def get_store_menu_json(url, source):
    tenant_uuid, store_uuid, category_uuids = get_uuids_from_url(url, source)

    url = 'https://vmos2.vmos.io/catalog/menu'
    headers = {
        'store': store_uuid,
        'tenant': tenant_uuid,
        'x-requested-from': 'online',
    }

    resp_json = call_api(url, headers)
    full_menu_json = {}
    for menu in resp_json['payload']:
        menu_uuid = menu['uuid']
        menu_key = (menu['displayName'] or menu['name'], menu['uuid'])

        full_menu_json[menu_key] = {}
        for category in menu['categories']:
            category_uuid = category['uuid']
            category_key = (category['name'], category['uuid'])

            full_menu_json[menu_key][category_key] = {}
            category_bundles = get_bundles_from_category(tenant_uuid, store_uuid, menu_uuid, category_uuid, source)

            for bundle_key in category_bundles:
                bundle_uuid = bundle_key[1]
                bundle_items = get_items_from_bundle(tenant_uuid, store_uuid, menu_uuid, category_uuid, bundle_uuid, source)

                full_menu_json[menu_key][category_key][bundle_key] = bundle_items

    str_key_full_menu = stringify_keys(full_menu_json)

    print(json.dumps(str_key_full_menu, indent=2))

def get_bootstrap(origin):
    url = 'https://vmos2.vmos.io/tenant/v1/bootstrap'
    headers = {
        'origin': origin,
        'x-requested-from': 'online',
    }

    return call_api(url, headers)


def get_uuids_from_url(url, source):
    split_url = url.split('/')

    tenant_url = 'https://{}'.format(split_url[2])
    bootstrap_resp = get_bootstrap(origin=tenant_url)
    tenant_uuid = bootstrap_resp['payload']['tenant']['uuid']
    store_uuid = split_url[4]

    category_uuids = get_menu_category_uuids(tenant_uuid, store_uuid)

    return tenant_uuid, store_uuid, category_uuids


def generate_item_list_from_url(url, source):
    tenant_uuid, store_uuid, menu_category_uuids = get_uuids_from_url(url, source)

    all_bundles = get_bundles_from_menu_categories(
        tenant_uuid,
        store_uuid,
        menu_category_uuids,
        source
    )

    all_items = get_items_from_bundles(tenant_uuid, store_uuid, all_bundles, source)

    pprint(get_items_csv(all_items))



if __name__ == "__main__":
    # Leon
    # store_uuid = 'a2af6eec-33c1-4595-9cea-f17369d9b3a4'
    # #menu_uuid = '976808f1-15b9-43ab-a00a-ec44a30d31c6' # breakfast
    # menu_uuid = 'a5a36474-f9cc-40db-8cb7-5fff8cf230d8'
    # tenant_uuid = 'b122f234-d4b9-46e4-a161-98fac92d1890'


    source = 'online'
    url = 'https://leon.vmos.io/store/a2af6eec-33c1-4595-9cea-f17369d9b3a4/menu?menuUUID=a5a36474-f9cc-40db-8cb7-5fff8cf230d8'
    #generate_item_list_from_url(url, source)

    pprint(get_store_menu_json(url, source))





