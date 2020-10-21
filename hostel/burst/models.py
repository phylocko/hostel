from json import JSONDecodeError

import requests as r
from hostel.settings import TAX

from hostel.settings import BURST_URL


class BurstSideException(Exception):
    pass


class Burst:

    def __init__(self, burst_set):
        if not burst_set:
            raise ValueError('burst_set not given')
        self.burst_set = burst_set  # don't use if in internal methods!

        self.traffic_iface_names = [x.mrtg_name() for x in burst_set.traffic_ports()]
        self.substract_iface_names = [x.mrtg_name() for x in burst_set.substract_ports()]
        self.limit = burst_set.limit or 0
        self.price = burst_set.price or 0
        self.separated_ports = [x.mrtg_name() for x in burst_set.traffic_ports()]

    def get_burst(self, start_day, end_day):
        """
        :param start_day: дата начала периода, строка в формате YYYY-MM-DD
        :param end_day: дата окончания периода, строка в формате YYYY-MM-DD
        :return: Словарь с перечисленными ниже значениями

        traffic_in: входящий трафик (весь минус вычитаемый)
        traffic_out: исходящий трафик (весь минус вычитаемый)
        traffic: нужный траффик (выбранное направление либо превалирующий)
        burst_traffic: бёрст (traffic минус предоплаченная полоса)
        traffic_direction: подсчитываемое направление (in, out, max)
        burst_cost: стоимость берста
        burst_cost_taxed: стоимость берста (с НДС)
        total_cost: стоимость берста + абонентской платы
        total_cost_taxed: стоимость берста и абоненской платы (с НДС)
        """

        traffic_in, traffic_out = self.do_request(start_day, end_day, self.traffic_iface_names)

        if self.substract_iface_names:
            unwanted_traffic_in, unwanted_traffic_out = self.do_request(start_day, end_day, self.substract_iface_names)
            traffic_in -= unwanted_traffic_in
            traffic_out -= unwanted_traffic_out

        assert (self.burst_set.direction in ['in', 'out', 'max'])

        direction = self.burst_set.direction
        if self.burst_set.direction == 'in':
            traffic = traffic_in

        elif self.burst_set.direction == 'out':
            traffic = traffic_out

        else:
            traffic = max(traffic_in, traffic_out)
            direction = 'out'
            if traffic_in > traffic_out:
                direction = 'in'

        burst_traffic = traffic - self.limit
        if burst_traffic > 0:
            burst_traffic = round(burst_traffic, 2)
        else:
            burst_traffic = 0

        burst_cost = round(burst_traffic * self.price, 2)
        total_cost = burst_cost + self.burst_set.subscription_fee

        # учет НДС
        if self.burst_set.with_tax:
            burst_cost_taxed = burst_cost
            burst_cost = burst_cost_taxed / 120 * 100

            total_cost_taxed = total_cost
            total_cost = total_cost_taxed / 120 * 100

        else:
            burst_cost_taxed = burst_cost + burst_cost * TAX
            total_cost_taxed = total_cost + total_cost * TAX

        return {
            'traffic': round(traffic, 2),
            'traffic_in': traffic_in,
            'traffic_out': traffic_out,
            'burst_traffic': round(burst_traffic, 2),
            'burst_cost': round(burst_cost, 2),
            'burst_cost_taxed': round(burst_cost_taxed, 2),
            'total_cost': round(total_cost, 2),
            'total_cost_taxed': round(total_cost_taxed, 2),
            'direction': direction,
        }

    def get_separated_burst(self, start, end):

        report = []

        for traffic_port in self.separated_ports:
            total_in, total_out = self.do_request(start, end, [traffic_port])

            port_data = {
                'port': traffic_port,
                'total_in': total_in,
                'total_out': total_out,
            }
            report.append(port_data)
        return report

    @staticmethod
    def do_request(start, end, iface_names):

        data = {'dev': iface_names, 'start': start, 'end': end}

        try:
            result = r.post(BURST_URL, json=data)
        except r.exceptions.ConnectionError as e:
            raise BurstSideException(e)

        if result.ok:
            try:
                burst_data = result.json()
            except JSONDecodeError:
                raise BurstSideException(result.text)
            else:
                burst_in = round(int(burst_data['bytin']) * 8 / 1000 / 1000, 2)
                burst_out = round(int(burst_data['bytou']) * 8 / 1000 / 1000, 2)
                return burst_in, burst_out
        else:
            raise BurstSideException(result.text)

    def __repr__(self):
        return '<Burst "%s">' % self.burst_set.name
