import os
import yaml

from flask import Flask, request, jsonify

from liquidity_pool import LiquidityPool

app = Flask(__name__)

liquidity_pool = None
config = None
margin = None

@app.route('/fx-rate', methods=['POST'])
def post_fx_rate():
    try:
        data = request.json
        pair, rate = liquidity_pool.update_rate(data)
        return jsonify({"pair": pair, "rate": rate}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(e)
        return jsonify({"error": "Something went wrong please try again later"}), 500


@app.route('/transfer', methods=['POST'])
def post_transfer():
    try:
        data = request.json
        from_currency, to_currency, actual_from_amount, to_amount, margin_profit, rate = liquidity_pool.exchange(data)
        return jsonify({
                "fx_rate": {
                    "pair": f"{from_currency}/{to_currency}",
                    "rate": rate
                },
                "from": {
                    "currency": from_currency,
                    "amount": actual_from_amount
                },
                "to": {
                    "currency": to_currency,
                    "amount": to_amount
                },
                "fees": {
                    "currency": from_currency,
                    "amount": margin_profit
                }
                
            }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(e)
        return jsonify({"error": "Something went wrong please try again later"}), 500


@app.route("/internal/fx-rate/<pair>", methods=["GET"])
def get_fx_rate_history(pair):
    try:
        pair = pair.replace("-", "/")
        latest_rate = liquidity_pool.get_rate_history(pair)
        return jsonify(latest_rate), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/internal/status", methods=["GET"])
def get_liquidity_pool_status():
    try:
        return jsonify(liquidity_pool.get_status()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/internal/rebalance", methods=["POST"])
def post_manual_rebalance():
    try:
        liquidity_pool._rebalance_calculation()
        return "", 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def load_config(file_path="config.yaml"):
    global config
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)


def initialize_liquidity_pool():
    global config, liquidity_pool
    liquidity_pool = LiquidityPool(config['liquidity_pool'])


def main():
    load_config()
    initialize_liquidity_pool()


if __name__ == "__main__":
    main()
    app.run(
        debug=config["app"]["debug"],
        host=config["app"]["host"],
        port=config["app"]["port"],
        use_reloader=False
    )
