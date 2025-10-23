# Schwab API Integration

This module provides a comprehensive integration with the Schwab API for algorithmic trading applications. It handles OAuth2 authentication, token management, and provides access to market data and account operations.

## Overview

The Schwab integration consists of three main components:

- **SchwabClient**: Core OAuth2 authentication and token management
- **MarketHandler**: Market data operations (quotes, price history, market hours)
- **AccountHandler**: Account operations (positions, orders, account details)

## Token Management

The integration uses a Redis-first approach for token management with environment file fallback:

### Token Lifecycle

1. **Check Redis**: Look for valid access token (TTL: 30 minutes)
2. **Refresh from Redis**: If expired, use refresh token from Redis (TTL: 90 days)
3. **Load from Environment**: If Redis refresh fails, load refresh token from env file
4. **OAuth2 Flow**: If all else fails, initiate complete OAuth2 authentication

### Environment Variables

Required environment variables in `algo_trader.env`:

```bash
# Required for initialization
export SCHWAB_APP_NAME=your_app_name
export SCHWAB_API_KEY=your_api_key
export SCHWAB_SECRET=your_secret

# Optional - for token persistence
export SCHWAB_ACCESS_TOKEN=your_access_token
export SCHWAB_REFRESH_TOKEN=your_refresh_token
```

## OAuth2 Setup Process

### Initial Setup

1. **Register Application**: Create a Schwab API application at [Schwab Developer Portal](https://developer.schwab.com)

2. **Get Credentials**: Obtain your API key, secret, and app name

3. **Set Environment Variables**: Add credentials to `algo_trader.env`

4. **Run Authentication**: The first API call will trigger OAuth2 flow:
   ```python
   from system.algo_trader.schwab.market_handler import MarketHandler
   
   handler = MarketHandler()
   quotes = handler.get_quotes(['AAPL'])  # This will trigger OAuth2 if needed
   ```

### OAuth2 Flow Details

When OAuth2 is required, the system will:

1. Display authorization URL
2. Prompt for redirect URL after user authorization
3. Exchange authorization code for tokens
4. Store tokens in Redis and update environment file

## Usage Examples

### Market Data

```python
from system.algo_trader.schwab.market_handler import MarketHandler
from system.algo_trader.schwab.timescale_enum import PeriodType, FrequencyType

# Initialize handler
handler = MarketHandler()

# Get real-time quotes
quotes = handler.get_quotes(['AAPL', 'MSFT', 'GOOGL'])
print(f"AAPL Price: {quotes['AAPL']['price']}")

# Get historical data
history = handler.get_price_history(
    ticker='AAPL',
    period_type=PeriodType.DAY,
    period=5,
    frequency_type=FrequencyType.MINUTE,
    frequency=5
)

# Get market hours
from datetime import datetime
market_hours = handler.get_market_hours(datetime.now())
print(f"Market open: {market_hours.get('isOpen', False)}")
```

### Account Operations

```python
from system.algo_trader.schwab.account_handler import AccountHandler

# Initialize handler
account_handler = AccountHandler()

# Get all accounts
accounts = account_handler.get_accounts()

# Get account details
account_details = account_handler.get_account_details('123456789')

# Get positions
positions = account_handler.get_positions('123456789')

# Get orders
orders = account_handler.get_orders('123456789')

# Place order (example)
order_data = {
    "orderType": "MARKET",
    "session": "NORMAL",
    "duration": "DAY",
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [
        {
            "instruction": "BUY",
            "quantity": 10,
            "instrument": {
                "symbol": "AAPL",
                "assetType": "EQUITY"
            }
        }
    ]
}
order_result = account_handler.place_order('123456789', order_data)
```

## Error Handling

The integration includes comprehensive error handling:

- **Token Expiry**: Automatic refresh when possible
- **Network Errors**: Graceful degradation with logging
- **API Errors**: Detailed error messages with status codes
- **Invalid Parameters**: Validation with clear error messages

## Testing

Run the test suite:

```bash
# Run all Schwab tests
bazel test //tests/algo_trader/schwab:test_schwab_client
bazel test //tests/algo_trader/schwab:test_market_handler

# Run with coverage
bazel test //tests/algo_trader/schwab:test_schwab_client --test_output=all
```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```
   ValueError: Missing required Schwab environment variables
   ```
   **Solution**: Ensure all required env vars are set in `algo_trader.env`

2. **Token Refresh Failures**
   ```
   Token refresh failed: 400 - Bad Request
   ```
   **Solution**: Check if refresh token is valid, may need to re-authenticate

3. **OAuth2 Flow Issues**
   ```
   Invalid redirect URL provided
   ```
   **Solution**: Ensure you copy the complete redirect URL including query parameters

4. **API Rate Limits**
   ```
   Request failed with status 429
   ```
   **Solution**: Implement rate limiting in your application

### Debug Mode

Enable debug logging to see detailed token flow:

```python
import logging
logging.getLogger('system.algo_trader.schwab').setLevel(logging.DEBUG)
```

## Architecture

### Token Storage Strategy

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │      Redis      │    │  Environment    │
│                 │    │                 │    │     File        │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Access Token    │◄───┤ Access Token    │◄───┤ Access Token    │
│ (30 min TTL)    │    │ (30 min TTL)    │    │ (persistent)    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Refresh Token   │◄───┤ Refresh Token   │◄───┤ Refresh Token   │
│ (90 day TTL)    │    │ (90 day TTL)    │    │ (persistent)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Class Hierarchy

```
SchwabClient (Base)
├── MarketHandler (Market Data)
└── AccountHandler (Account Operations)
```

## Security Considerations

- **Token Storage**: Tokens are stored in Redis with appropriate TTL
- **Environment Files**: Never commit token files to version control
- **Network Security**: All API calls use HTTPS
- **Logging**: Sensitive data is not logged in production

## Rate Limits

Schwab API has rate limits that vary by endpoint:

- **Quotes**: 120 requests per minute
- **Price History**: 60 requests per minute
- **Account Data**: 30 requests per minute

The integration handles rate limiting gracefully by logging warnings and returning appropriate error responses.

## Support

For issues with this integration:

1. Check the troubleshooting section above
2. Review the test cases for usage examples
3. Enable debug logging for detailed flow information
4. Check Schwab API documentation for endpoint-specific issues
