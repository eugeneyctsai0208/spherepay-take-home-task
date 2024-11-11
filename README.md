# Inventory Management system

## Overview

Your task is to build a backend service that simulates an inventory management system for a company providing cross-border liquidity services. The company operates liquidity pools in multiple currencies and manages currency transfers for users sending funds between different currencies.

The system will support the following currencies:

- **USD**, **EUR**, **JPY**, **GBP**, and **AUD**.

## Objective

The key objectives are to create a system that:

- Manages liquidity pools across various currencies.
- Tracks inventory, revenue, and FX rates for each transaction.
- Dynamically rebalances liquidity pools based on transaction data to maintain optimal balances.

## Language and Framework:

- Preferred: Node.js with TypeScript.
- Alternative: Any language or framework of your choice is accepted.

## Requirements

1. API Endpoints

   - Transfer Request: `POST /transfer`

     - Accepts a transfer request from a sender to a receiver, converting currency X to currency Y.
     - Uses the FX rate to calculate the amount in currency Y and apply a transaction margin.
     - Immediately debits the amount in Y from the liquidity pool and records it.
     - Adds revenue based on the applied margin.
     - Takes into account currency-specific settlement times.
       - Note: In the real world, settlement times typically depend on the country and payment rails. For this exercise, however, we’ll simplify by making settlement times dependent on the currency instead.

   - FX Rate Update: `POST /fx-rate`
     - Receives mock FX rates between supported currencies.
     - Updates the stored FX rates for use in transfer calculations.
     - The mock script, `mockFxRateSender.js`, should be used to send rate updates to this endpoint every 3-5 seconds.
       - Example payload from the script:
         ```
         {"pair":"AUD/JPY","rate":"82.6666","timestamp":"2024-11-11T11:22:18.123Z"}
         ```
     - The script will occasionally send extreme fluctuations (5% chance of a 5-10% change) to simulate market volatility.

2. Liquidity pool rebalancing

   - Periodically rebalance liquidity between pools to maintain optimal balances.
   - Takes into account transaction volume and send/receive imbalances.
   - Ensures each pool is adequately funded to meet anticipated demand.
   - Track available liquidity in each currency pool in real-time.

3. Revenue Calculation

   - Track revenue by calculating the margin on each transaction.

4. Foreign Exchange Rates

   - Store FX rates and allow historical lookups for use in transfer and revenue calculations.

5. Data Persistence

   - Use reliable data storage to maintain inventory levels, transactions, FX rates, and revenue.
   - Ensure atomicity and resilience to outages for each transaction.

6. Additional Requirements:

   - Use configuration files or environment variables for adjustable parameters, such as margin percentages, currency settlement times, and rebalance frequencies.
   - Ensure logging and error handling, especially for scenarios with missing liquidity or FX rates.

## Initial Balances per Currency

- **USD**: 1,000,000
- **EUR**: 921,658
- **JPY**: 109,890,110
- **GBP**: 750,000
- **AUD**: 1,349,528

## Currency Settlement Times

Each currency has a predefined settlement time, simulating the delay for funds to be confirmed in liquidity pools. These settlement times are specified in seconds for easy testing:

- **USD**: 3 seconds
- **EUR**: 2 seconds
- **JPY**: 3 seconds
- **GBP**: 2 seconds
- **AUD**: 3 seconds
