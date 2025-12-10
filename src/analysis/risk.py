"""Risk analysis and Monte Carlo simulation for holding period."""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Analyzes risk during forced holding period."""
    
    def __init__(
        self,
        tc_steam: float = 0.15,
        default_exec_prob: float = 0.6
    ):
        """Initialize risk analyzer.
        
        Args:
            tc_steam: Steam transaction cost (default 15%)
            default_exec_prob: Default execution probability (guess, need to validate)
        """
        self.tc_steam = tc_steam
        self.default_exec_prob = default_exec_prob  # Conservative guess
    
    def calculate_pnl_now(
        self,
        steam_bid: float,
        buff_ask: float
    ) -> float:
        """Calculate current PnL.
        
        Args:
            steam_bid: Best bid on Steam
            buff_ask: Best ask on Buff (net of fees)
            
        Returns:
            Current PnL
        """
        adj_steam_bid = steam_bid * (1 - self.tc_steam)
        return adj_steam_bid - buff_ask
    
    def calculate_spread_pct(
        self,
        pnl: float,
        buff_ask: float
    ) -> float:
        """Calculate spread percentage.
        
        Args:
            pnl: Profit and loss
            buff_ask: Best ask on Buff
            
        Returns:
            Spread as percentage
        """
        if buff_ask == 0:
            return 0.0
        return (pnl / buff_ask) * 100
    
    def calculate_volatility(
        self,
        prices: List[float],
        method: str = 'log_returns'
    ) -> float:
        """Calculate volatility from price history.
        
        Args:
            prices: List of historical prices
            method: 'log_returns' or 'simple_returns'
            
        Returns:
            Daily volatility (as decimal, e.g., 0.20 for 20%)
        """
        if len(prices) < 2:
            return 0.0
        
        prices_array = np.array(prices)
        
        if method == 'log_returns':
            # Log returns: ln(P_t / P_{t-1})
            returns = np.diff(np.log(prices_array))
        else:
            # Simple returns: (P_t - P_{t-1}) / P_{t-1}
            returns = np.diff(prices_array) / prices_array[:-1]
        
        # Calculate standard deviation
        std_dev = np.std(returns)
        
        # Return as daily volatility
        # TODO: should probably annualize this properly but keeping it simple for now
        return float(std_dev)
    
    def monte_carlo_simulation(
        self,
        current_price: float,
        volatility: float,
        hold_days: int,
        n_simulations: int = 10000,
        drift: float = 0.0
    ) -> np.ndarray:
        """Monte Carlo simulation of price after holding period.
        
        Uses log-normal model: Price_T = Price_0 * exp(µ*T - 0.5σ²T + σ√T * Z)
        
        Args:
            current_price: Current price
            volatility: Daily volatility (as decimal)
            hold_days: Holding period in days
            n_simulations: Number of Monte Carlo simulations
            drift: Expected daily return (default 0 for short-term)
            
        Returns:
            Array of simulated prices after hold period
        """
        # Generate random normal variates
        Z = np.random.normal(0, 1, n_simulations)
        
        # Time in years (approximate)
        T = hold_days / 365.0
        
        # Log-normal model
        # Price_T = Price_0 * exp(µ*T - 0.5σ²T + σ√T * Z)
        # For daily volatility, we need to scale appropriately
        # If volatility is daily, then for T days: σ_total = σ_daily * sqrt(T)
        
        # Convert daily volatility to holding period volatility
        sigma_total = volatility * np.sqrt(hold_days)
        
        # Simulate prices
        price_multiplier = np.exp(
            drift * hold_days - 0.5 * volatility**2 * hold_days + 
            volatility * np.sqrt(hold_days) * Z
        )
        
        simulated_prices = current_price * price_multiplier
        
        return simulated_prices
    
    def analyze_hold_period_risk(
        self,
        steam_bid: float,
        buff_ask: float,
        volatility: float,
        hold_days: int,
        n_simulations: int = 10000,
        drift: float = 0.0
    ) -> Dict[str, float]:
        """Analyze risk during holding period.
        
        Args:
            steam_bid: Current best bid on Steam
            buff_ask: Current best ask on Buff (net of fees)
            volatility: Daily volatility of Steam price
            hold_days: Expected holding period in days
            n_simulations: Number of Monte Carlo simulations
            drift: Expected daily return
            
        Returns:
            Dictionary with risk metrics:
            - prob_positive: Probability of positive PnL after hold
            - expected_pnl: Expected PnL after hold
            - var_95: 95% Value at Risk (negative value means loss)
            - var_99: 99% Value at Risk
            - worst_case: Worst case PnL (1st percentile)
        """
        # Simulate Steam prices after hold period
        simulated_steam_prices = self.monte_carlo_simulation(
            steam_bid, volatility, hold_days, n_simulations, drift
        )
        
        # Calculate adjusted Steam bids (after fee)
        adj_steam_bids = simulated_steam_prices * (1 - self.tc_steam)
        
        # Calculate PnL for each simulation
        pnl_simulations = adj_steam_bids - buff_ask
        
        # Calculate metrics
        prob_positive = float(np.mean(pnl_simulations > 0))
        expected_pnl = float(np.mean(pnl_simulations))
        var_95 = float(np.percentile(pnl_simulations, 5))  # 5th percentile (loss)
        var_99 = float(np.percentile(pnl_simulations, 1))  # 1st percentile (loss)
        worst_case = float(np.min(pnl_simulations))
        
        return {
            'prob_positive': prob_positive,
            'expected_pnl': expected_pnl,
            'var_95': var_95,
            'var_99': var_99,
            'worst_case': worst_case,
            'current_pnl': self.calculate_pnl_now(steam_bid, buff_ask)
        }
    
    def calculate_risk_score(
        self,
        expected_pnl: float,
        prob_positive: float,
        var_95: float,
        execution_prob: float,
        risk_aversion: float = 0.5
    ) -> float:
        """Calculate risk-adjusted score for a trade.
        
        Args:
            expected_pnl: Expected PnL after hold period
            prob_positive: Probability of positive PnL
            var_95: 95% Value at Risk (negative)
            execution_prob: Execution probability
            risk_aversion: Risk aversion coefficient (0-1)
            
        Returns:
            Risk-adjusted score (higher is better)
        """
        # Base score: expected PnL weighted by execution probability
        base_score = expected_pnl * execution_prob
        
        # Risk penalty: proportional to VaR and inverse of prob_positive
        # Higher risk_aversion increases penalty
        risk_penalty = abs(var_95) * (1 - prob_positive) * risk_aversion
        
        # Final score
        score = base_score - risk_penalty
        
        return score
    
    def recommend_action(
        self,
        pnl_now: float,
        prob_positive: float,
        expected_pnl: float,
        min_pnl: float = 0.5,
        min_prob_positive: float = 0.6
    ) -> str:
        """Recommend action for a trade candidate.
        
        Args:
            pnl_now: Current PnL
            prob_positive: Probability of positive PnL after hold
            expected_pnl: Expected PnL after hold
            min_pnl: Minimum acceptable PnL
            min_prob_positive: Minimum acceptable probability
            
        Returns:
            'candidate', 'monitor', or 'skip'
        """
        if pnl_now < min_pnl:
            return 'skip'
        
        if prob_positive < min_prob_positive:
            return 'monitor'
        
        if expected_pnl < min_pnl:
            return 'monitor'
        
        return 'candidate'


if __name__ == "__main__":
    # Test risk analyzer
    analyzer = RiskAnalyzer()
    
    # Example: AK-47 Redline
    steam_bid = 10.0
    buff_ask = 8.5
    volatility = 0.05  # 5% daily volatility
    hold_days = 3
    
    pnl_now = analyzer.calculate_pnl_now(steam_bid, buff_ask)
    print(f"Current PnL: {pnl_now:.2f}")
    
    risk_metrics = analyzer.analyze_hold_period_risk(
        steam_bid, buff_ask, volatility, hold_days
    )
    
    print(f"Risk metrics: {risk_metrics}")
    
    risk_score = analyzer.calculate_risk_score(
        risk_metrics['expected_pnl'],
        risk_metrics['prob_positive'],
        risk_metrics['var_95'],
        0.6,
        0.5
    )
    
    print(f"Risk score: {risk_score:.2f}")

