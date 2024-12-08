import threading
import time

from datetime import datetime
from itertools import permutations

from lock_helper import acquire_locks

class LiquidityPool:
    def __init__(self, config):
        initial_balances = config['initial_balances']
        settlement_time = config['fx_settlement_times']
        margin = config['fees']['margin'] if config['fees']['margin'] is not None else 0.01

        self.balances = initial_balances
        self.support_currencies = initial_balances.keys()
        self.balance_locks = {currency: threading.Lock() for currency in self.support_currencies}
        self.supported_pairs = [f"{a}/{b}" for a, b in permutations(self.support_currencies, 2)]
        self.rate_history = {pair: [] for pair in self.supported_pairs}
        self.settlement_time = settlement_time
        self.margin = margin
        self.profit = {currency: 0 for currency in self.support_currencies}
        self.flow = {currency: 0 for currency in self.support_currencies}
        self.rebalance_interval = config['rebalance']['interval'] if config['fees']['margin'] is not None else 600

        self._rebalance_thread()


    def update_rate(self, data):
        pair, rate, timestamp = self._parse_rate_update_data(data)

        new_entry = {"rate": rate, "timestamp": timestamp}
        rate_list = self.rate_history[pair]

        i = len(rate_list) - 1
        while i >= 0 and rate_list[i]["timestamp"] > timestamp:
            i -= 1

        rate_list.insert(i + 1, new_entry)
            
        print(f"Rate updated for pair {pair}: {rate}")
        return pair, rate


    def exchange(self, data):
        from_currency, to_currency, from_amount = self._parse_exchange_data(data)
        pair = f"{from_currency}/{to_currency}"

        try:
            with acquire_locks(self.balance_locks[from_currency], self.balance_locks[to_currency], max_retries=10):
                rate = self._get_latest_rate(pair)
                if rate is None:
                    print(f"Exchange rate for {pair} not available")
                    raise RuntimeError()
                margin_profit = from_amount * self.margin
                actual_from_amount = from_amount - margin_profit
                to_amount = actual_from_amount * rate
                if self.balances[to_currency] < to_amount:
                    print(f"Insufficient balance for currency {to_currency}, current balance: {self.balances[to_currency]}, intended withdraw amount {to_amount}")
                    raise RuntimeError()
                self._settle_funds(from_currency, to_currency)
                self.balances[to_currency] -= to_amount
                self.balances[from_currency] += actual_from_amount
                self.profit[from_currency] += margin_profit
                self._update_currency_flow(from_currency, to_currency, actual_from_amount, to_amount)
                print(f"Balance updated, {from_currency}: {self.balances[from_currency]} ({actual_from_amount}), {to_currency}: {self.balances[to_currency]} (-{to_amount})")
                return from_currency, to_currency, actual_from_amount, to_amount, margin_profit, rate

        except RuntimeError:
            raise RuntimeError("Something went wrong, please wait and try again")


    def get_rate_history(self, pair):
        return self.rate_history[pair]


    def get_status(self):
        return {
            "rates": {pair: self._get_latest_rate(pair) for pair in self.supported_pairs},
            "balances": self.balances,
            "profit": self.profit
        }


    def _rebalance_calculation(self):
        if self._verify_all_pairs_available() is False:
            print("Rebalance failed, not all rate pairs available")
            return
        locks = [self.balance_locks[currency] for currency in self.support_currencies]
        with acquire_locks(*locks):
            positive_flows, negative_flows = [], []
            total_positive_flow, total_negative_flow = 0, 0

            for currency in self.support_currencies:
                flow_amount = self.flow[currency]
                
                if currency != "USD":
                    rate = self._get_latest_rate(f"{currency}/USD")
                    flow_amount *= rate
                
                if flow_amount > 0:
                    positive_flows.append((currency, flow_amount))
                    total_positive_flow += flow_amount

                elif flow_amount < 0:
                    negative_flows.append((currency, abs(flow_amount)))
                    total_negative_flow += abs(flow_amount)

            for i, (currency, amount) in enumerate(positive_flows):
                positive_flows[i] = (currency, amount / total_positive_flow)

            for i, (currency, amount) in enumerate(negative_flows):
                negative_flows[i] = (currency, amount / total_negative_flow)

            if len(positive_flows) == 0 and len(negative_flows) == 0:
                print("No rebalancing required at this time")
                return
            
            positive_flows.sort(key=lambda x: x[1], reverse=True)
            negative_flows.sort(key=lambda x: x[1])

            pos, neg = 0, 0
            rebalance_orders = []
            
            while pos < len(positive_flows) and neg < len(negative_flows):
                inflow_currency, inflow_percentage = positive_flows[pos]
                outflow_currency, outflow_percentage = negative_flows[neg]

                allocation = min(inflow_percentage, outflow_percentage)

                rebalance_orders.append((inflow_currency, outflow_currency, allocation))

                positive_flows[pos] = (inflow_currency, inflow_percentage - allocation)
                negative_flows[neg] = (outflow_currency, outflow_percentage - allocation)

                if positive_flows[pos][1] == 0:
                    pos += 1
                if negative_flows[neg][1] == 0:
                    neg += 1

            print("Rebalancing... ")
            self._rebalance_execution(rebalance_orders, total_positive_flow)
            print("Rebalancing complete")

            for currency in self.support_currencies:
                self.flow[currency] = 0


    def _rebalance_execution(self, rebalance_orders, total_positive_flow):
        for order in rebalance_orders:
            from_usd_rate = self._get_latest_rate(f"USD/{order[0]}") if order[0] != "USD" else 1
            rate = self._get_latest_rate(f"{order[0]}/{order[1]}")
            from_amount = total_positive_flow * order[2] * from_usd_rate
            to_amount = from_amount * rate
            print(f"Rebalancing order: {order[0]} {from_amount} to {order[1]} {to_amount}")
            self.balances[order[0]] -= from_amount
            self.balances[order[1]] += to_amount
            self._settle_funds(order[0], order[1])


    def _get_latest_rate(self, pair):
        if len(self.rate_history[pair]) > 0:
            return self.rate_history[pair][-1]['rate']
        else:
            return None


    def _update_currency_flow(self, from_currency, to_currency, from_amount, to_amount):
        self.flow[from_currency] += from_amount
        self.flow[to_currency] -= to_amount


    def _verify_currency_support(self, from_currency, to_currency):
        if from_currency not in self.support_currencies:
            print(f"Currency {from_currency} not supported")
            raise ValueError(f"Currency {from_currency} not supported")
        if to_currency not in self.support_currencies:
            print(f"Currency {to_currency} not supported")
            raise ValueError(f"Currency {to_currency} not supported")


    def _parse_exchange_data(self, data):
        try:
            from_currency = data['from']
            to_currency = data['to']
            self._verify_currency_support(from_currency, to_currency)
            
            try:
                from_amount = float(data['amount'])
                if from_amount <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f"Invalid amount: {data['amount']}")

            return from_currency, to_currency, from_amount
        except ValueError as e:
            print(f"Error parsing update data: {data}")
            raise


    def _parse_rate_update_data(self, data):
        try:
            from_currency = data['pair'].split("/")[0]
            to_currency = data['pair'].split("/")[1]
            self._verify_currency_support(from_currency, to_currency)
            rate = float(data['rate'])
            timestamp = datetime.strptime(data['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
            return f"{from_currency}/{to_currency}", rate, timestamp
        except Exception:
            print(f"Error parsing update data: {data}")
            raise ValueError("Error parsing update data")


    def _settle_funds(self, from_currency, to_currency):
        settlement_time = max(self.settlement_time[from_currency], self.settlement_time[to_currency])
        time.sleep(settlement_time)


    def _process_margin(self, margin_profit, from_currency):
        self.profit[from_currency] += margin_profit 


    def _verify_all_pairs_available(self):
        for pair in self.supported_pairs:
            if len(self.rate_history[pair]) == 0:
                return False
        return True


    def _rebalance_loop(self):
        while True:
            try:
                time.sleep(self.rebalance_interval)
                self._rebalance_calculation()
            except Exception as e:
                print(f"Rebalance encountered an error", e)


    def _rebalance_thread(self):
        rebalance_thread = threading.Thread(target=self._rebalance_loop)
        rebalance_thread.start()
