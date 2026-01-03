"""
SEC Data Source

Fetches and manages ticker data from the SEC's public API.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import requests
from influxdb_client_3 import Point
from infrastructure.logging.logger import get_logger


class SECDataSource:
    """
    Data source for fetching ticker information from the SEC.
    
    Retrieves active ticker symbols and company metadata from the SEC's
    public company_tickers.json endpoint and stores them in InfluxDB
    for use in filtering and querying market data.
    
    Note: SEC requires a proper User-Agent header with contact information.
    Set SEC_USER_AGENT environment variable to "YourName your@email.com"
    """
    
    SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
    DEFAULT_USER_AGENT = "AlgoTrader contact@example.com"
    
    def __init__(self, influxdb_client=None, user_agent=None):
        """
        Initialize the SEC data source.
        
        Arguments:
            influxdb_client: Optional InfluxDB client for storing ticker data
            user_agent: Optional User-Agent string. If None, reads from SEC_USER_AGENT env var
        """
        self.logger = get_logger("SECDataSource")
        self.influxdb_client = influxdb_client
        self._ticker_cache = None
        
        # SEC requires proper User-Agent with contact info
        if user_agent:
            self.user_agent = user_agent
        else:
            self.user_agent = os.getenv("SEC_USER_AGENT", self.DEFAULT_USER_AGENT)
        
        self.logger.debug(f"Initialized with User-Agent: {self.user_agent}")
        
    def fetch_tickers(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch active ticker data from the SEC API.
        
        Returns:
            List of ticker dictionaries with keys: ticker, cik_str, title
            None if fetch fails
        """
        try:
            self.logger.debug(f"Fetching tickers from {self.SEC_TICKER_URL}")
            
            # SEC requires a User-Agent header with contact information
            headers = {
                "User-Agent": self.user_agent
            }
            
            response = requests.get(self.SEC_TICKER_URL, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the nested dictionary structure
            tickers = []
            for key, ticker_data in data.items():
                if isinstance(ticker_data, dict):
                    tickers.append({
                        'ticker': ticker_data.get('ticker', '').upper(),
                        'cik_str': str(ticker_data.get('cik_str', '')),
                        'title': ticker_data.get('title', '')
                    })
            
            self._ticker_cache = tickers
            self.logger.info(f"Successfully fetched {len(tickers)} tickers from SEC")
            return tickers
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch tickers from SEC: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing SEC ticker data: {e}")
            return None
    
    def get_ticker_symbols(self) -> Optional[List[str]]:
        """
        Get list of ticker symbols only.
        
        Returns:
            List of ticker symbol strings, None if fetch fails
        """
        if self._ticker_cache is None:
            tickers = self.fetch_tickers()
            if tickers is None:
                return None
        
        return [t['ticker'] for t in self._ticker_cache if t['ticker']]
    
    def store_tickers_in_influxdb(self, tickers: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Store ticker metadata in InfluxDB for filtering and reference.
        
        Stores tickers in a 'ticker_metadata' measurement with:
        - Tag: ticker (for filtering)
        - Fields: cik (CIK number), title (company name)
        - Timestamp: current time
        
        Arguments:
            tickers: Optional list of ticker dicts. If None, uses cached data or fetches
            
        Returns:
            True if storage successful, False otherwise
        """
        if self.influxdb_client is None:
            self.logger.error("No InfluxDB client provided, cannot store tickers")
            return False
        
        # Use provided tickers or fetch if needed
        if tickers is None:
            if self._ticker_cache is None:
                tickers = self.fetch_tickers()
                if tickers is None:
                    return False
            else:
                tickers = self._ticker_cache
        
        try:
            self.logger.debug(f"Storing {len(tickers)} tickers in InfluxDB")
            
            # Create points for each ticker
            points = []
            timestamp = datetime.utcnow()
            
            for ticker_data in tickers:
                ticker = ticker_data.get('ticker')
                if not ticker:
                    continue
                
                point = Point("ticker_metadata")
                point = point.tag("ticker", ticker)
                point = point.field("cik", ticker_data.get('cik_str', ''))
                point = point.field("title", ticker_data.get('title', ''))
                point = point.time(timestamp)
                
                points.append(point)
            
            # Write all points in a single batch
            if points:
                result = self.influxdb_client.write_points(points)
                if result:
                    self.logger.info(f"Successfully stored {len(points)} tickers in InfluxDB")
                return result
            else:
                self.logger.warning("No valid tickers to store")
                return False
                
        except Exception as e:
            self.logger.error(f"Error storing tickers in InfluxDB: {e}")
            return False
    
    def get_ticker_count(self) -> int:
        """
        Get the number of tickers in cache.
        
        Returns:
            Number of cached tickers, 0 if no cache
        """
        if self._ticker_cache is None:
            return 0
        return len(self._ticker_cache)

