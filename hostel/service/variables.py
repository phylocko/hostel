import re
import netaddr
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


# Validators

def validate_mail_list(value):
    emails = [x.strip() for x in value.split(',')]
    for email in emails:
        validator_class = EmailValidator(message='%s: некорректный email' % email)
        validator_class(email)


def validate_netname(value):
    if not re.match("^[a-z0-9-]*$", value):
        raise ValidationError("Допустимы только малые латинские буквы и дефис")


def validate_vlan_id(value):
    if value < 1 or value > 4096:
        raise ValidationError("vlan-id '%s' is incorrect. Use 1-4096." % value)


def validate_vlan_name(value):
    if not re.match('^[a-z0-9_-]*$', value):
        raise ValidationError('Value must contain only a-z, 0-9 and "_" symbols.')


def validate_netmask(mask):
    if mask < 0 or mask > 32:
        raise ValidationError("Netmask %s is invalid. Use 0-32." % mask)


def validate_mac(mac):
    try:
        netaddr.EUI(mac)
    except netaddr.AddrFormatError as e:
        raise ValidationError(e)


# Type variables

DEVICE_TYPES = (
    ("router", "Маршрутизатор"),
    ("switch", "Коммутатор"),
    ("server", "Сервер"),
    ("transponder", "Транспондер"),
    ("kvm", "Виртуалка"),
    ("ups", "Бесперебойник"),
    ("nas", "NAS"),
    ("pdu", "Управляемая розетка"),
    ("t8", "T8"),
    ("mux", "Мультиплексор"),
    ("phone", "Телефон"),
    ("other", "Непонятное"),
)

lease_types = (
    ('dwdm', 'L1 Лямбда DWDM'),
    ("fiber", "L1 Волокно"),
    ("cross", "L1 СЛ (Кроссировка на площадке)"),
    ("l2", "L2 vlan"),
    ("evpn", "L2 EVPN"),
    ("qinq", "L2 802.1ad Q-in-Q"),
    ("pseudowire", "PseudoWire"),
    ("l3_inet", "L3 Интернет"),
    ("colocation", "Размещение оборудования"),
    ("bgp_uplink", "Аплинк BGP"),
    ("bgp_resell", "Перепродажа BGP"),
    ("maintenance", "Remote hands"),
    ("ipmpls", "IP/MPLS стык"),
    ("other", "Другое"),

)

# services

service_params = {

    'default': {
        'status': 'off',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': False,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': None,
        'allow_subservices': False,
    },
    'wix': {
        'status': 'test',
        'service_types': (
            ('global', 'Global'),
            ('ru', 'RU'),
            ('msk', 'MSK'),
            ('mskplus', 'MSK+'),
            ('customers', 'Customers'),
            ('peer', 'Peer'),
        ),
        'service_type': 'global',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': True,
        'require_as': True,
        'max_mask': 32,
        'min_mask': 32,
        'default_mask': 32,
        'require_port': True,
        'allow_subservices': False,
    },

    'inet2': {
        'status': 'test',
        'service_types': (
            ('generic', 'Generic'),
            ('peer', 'Peer'),
            ('uplink', 'Uplink'),
            ('dg', 'With DoS guard'),
            ('rkn', 'With RKN filter'),
            ('kdp', 'With  Kaspersky DDoS Protection'),
        ),
        'service_type': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': True,
        'require_as': True,
        'max_mask': 32,
        'min_mask': 32,
        'default_mask': 32,
        'require_port': True,
        'allow_subservices': False,
    },

    'bgpinet': {
        'status': 'test',
        'service_types': (
            ('generic', 'Generic'),
            ('peer', 'Peer'),
            ('kdp', 'With  Kaspersky DDoS Protection'),
        ),
        'service_type': 'generic',
        'require_vlan': True,
        'multiple_vlans': False,
        'require_net': True,
        'require_as': True,
        'max_mask': 30,
        'min_mask': 24,
        'default_mask': 30,
        'require_port': True,
        'allow_subservices': False,
    },

    'homeix': {
        'status': 'test',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': True,
        'require_as': True,
        'max_mask': 32,
        'min_mask': 32,
        'default_mask': 32,
        'require_port': True,
        'allow_subservices': False,
    },

    'l3inet': {
        'status': 'on',
        'service_types': (
            ('generic', 'Generic'),
            ('kdp', 'With  Kaspersky DDoS Protection'),
        ),
        'service_type': 'generic',
        'require_vlan': True,
        'multiple_vlans': False,
        'require_net': True,
        'require_as': False,
        'max_mask': 30,
        'min_mask': 24,
        'default_mask': 30,
        'require_port': True,
        'allow_subservices': False,
    },

    'l3vpn': {
        'status': 'on',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': True,
        'multiple_vlans': True,
        'require_net': True,
        'require_as': False,
        'max_mask': 30,
        'min_mask': 24,
        'default_mask': 30,
        'require_port': True,
        'allow_subservices': True,
    },

    'l2': {
        'status': 'on',
        'service_types': (
            ('vlan', 'Vlan'),
            ('vpls', 'VPLS'),
            ('qinq', '802.1ad Q-in-Q'),
        ),
        'service_type': 'vlan',
        'require_vlan': True,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': False,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': True,
        'allow_subservices': True,
    },

    'l1': {
        'status': 'on',
        'service_types': (
            ('dwdm', 'Лямбда *WDM'),
            ('fiber', 'Волокно'),
            ("crossconnect", "СЛ (Кроссировка на площадке)"),
        ),
        'service_type': 'dwdm',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': False,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': False,
        'allow_subservices': True,
    },

    'telephony': {
        'status': 'on',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': False,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': None,
        'allow_subservices': False,
    },

    'telia': {
        'status': 'on',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': True,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': True,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': True,
        'allow_subservices': False,
    },

    'colocation': {
        'status': 'on',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': False,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': None,
        'allow_subservices': True,
    },

    'hosting': {
        'status': 'on',
        'service_types': (
            ('generic', 'Generic'),
        ),
        'service_type': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': False,
        'require_as': False,
        'max_mask': None,
        'min_mask': None,
        'default_mask': None,
        'require_port': None,
        'allow_subservices': True,
    },

}
