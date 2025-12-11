"""
Sentinel Agent - Advanced Market Intelligence & Risk Detection
Monitors external factors: RoW issues, strikes, price spikes, policy changes
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import MarketSentiment, Project


class SentinelAgent:
    """
    AI-powered market intelligence and risk detection system.
    
    Monitors external factors: RoW issues, strikes, price spikes, policy changes.
    In production, this would integrate with:
    - NLP for news/social media monitoring
    - Real-time commodity price APIs
    - Government policy tracking systems
    - Labor union calendars
    """
    
    def __init__(self):
        """Initialize Sentinel Agent"""
        self.sentiment_data = self._load_market_sentiment()
        self.alert_history = []
        self.risk_scores = {}
    
    def _load_market_sentiment(self) -> pd.DataFrame:
        """
        Load market sentiment data.
        
        In production, this would connect to real-time news/social media APIs
        and perform NLP-based sentiment analysis.
        """
        sentiment_file = os.path.join(RAW_DATA_DIR, "Market_Sentiment_Log.csv")
        
        if not os.path.exists(sentiment_file):
            print(f"⚠️  Market sentiment file not found: {sentiment_file}")
            return pd.DataFrame()
        
        df = pd.read_csv(sentiment_file)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    
    def scan_market_intelligence(self, 
                                 date: datetime,
                                 region: Optional[str] = None) -> List[MarketSentiment]:
        """
        Scan for market intelligence and external risks.
        
        Args:
            date: Date to scan
            region: Optional region filter
        
        Returns:
            List of MarketSentiment objects
        """
        
        if self.sentiment_data.empty:
            return []
        
        # Filter by date
        day_data = self.sentiment_data[self.sentiment_data['Date'] == date]
        
        if region:
            day_data = day_data[day_data['Region'] == region]
        
        sentiments = []
        
        for _, row in day_data.iterrows():
            # Parse affected states
            affected_states = row['Affected_States'].split(',') if pd.notna(row['Affected_States']) else []
            
            # Determine halt flag
            halt_projects = SENTIMENT_IMPACT.get(row['Topic'], {}).get('halt_project', False)
            
            # Get impact multipliers
            impact = SENTIMENT_IMPACT.get(row['Topic'], {})
            lead_time_buffer = impact.get('lead_time_buffer', 0)
            price_multiplier = impact.get('price_multiplier', 1.0)
            
            sentiment = MarketSentiment(
                date=date,
                region=row['Region'],
                topic=row['Topic'],
                severity=row['Severity'],
                affected_states=affected_states,
                description=row['Description'],
                recommended_action=row['Recommended_Action'],
                lead_time_buffer_days=lead_time_buffer,
                price_multiplier=price_multiplier,
                halt_projects=halt_projects
            )
            
            sentiments.append(sentiment)
            
            # Log critical alerts
            if row['Severity'] in ['High', 'Critical']:
                self._log_alert(sentiment)
        
        return sentiments
    
    def check_row_status(self, 
                        project: Project,
                        date: datetime,
                        lookahead_days: int = 30) -> Dict[str, any]:
        """
        Check Right-of-Way (RoW) status for a project
        
        Args:
            project: Project to check
            date: Current date
            lookahead_days: Days to look ahead for potential issues
        
        Returns:
            RoW status assessment
        
        TODO: ADVANCED ROW TRACKING
        1. Integration with land registry databases
        2. Court case status API integration
        3. Community sentiment analysis (local news, social media)
        4. Historical RoW issue pattern learning
        5. Predictive ML model for RoW risk scoring
        6. Legal document analysis (NLP on court orders)
        7. Stakeholder identification and tracking
        8. Automated negotiation status updates
        9. Compensation payment tracking
        10. Environmental clearance status
        11. Forest clearance status (for transmission lines)
        12. Archaeological site proximity checks
        """
        
        result = {
            'status': project.row_status,
            'risk_level': 'Low',
            'potential_issues': [],
            'blocked_days': 0,
            'recommended_action': 'Continue',
            'affected_by_sentiment': False
        }
        
        # Check if project is already marked as RoW blocked
        if project.row_status == "Blocked":
            result['risk_level'] = 'Critical'
            result['recommended_action'] = 'HALT_ALL_PROCUREMENT'
            result['potential_issues'].append("RoW currently blocked")
            
            # TODO: Estimate unblock timeline using ML
            # result['estimated_unblock_days'] = self._predict_row_resolution(project)
            
            return result
        
        # Scan for potential RoW issues in sentiment data
        for day_offset in range(lookahead_days):
            check_date = date + timedelta(days=day_offset)
            sentiments = self.scan_market_intelligence(check_date, project.region)
            
            for sentiment in sentiments:
                if sentiment.topic == "RoW_Issue":
                    # Check if project's state is affected
                    if project.state in sentiment.affected_states:
                        result['affected_by_sentiment'] = True
                        result['risk_level'] = 'High' if sentiment.severity == 'High' else 'Medium'
                        result['potential_issues'].append(
                            f"RoW issue reported in {project.state} on {check_date.strftime('%Y-%m-%d')}"
                        )
                        
                        if day_offset < 7:  # Issue within next week
                            result['recommended_action'] = 'HOLD_PROCUREMENT'
        
        # TODO: Add predictive risk scoring
        # risk_score = self._calculate_row_risk_score(project)
        # result['risk_score'] = risk_score
        
        return result
    
    def detect_labor_disruptions(self,
                                region: str,
                                date: datetime,
                                forecast_days: int = 14) -> Dict[str, any]:
        """
        Detect potential labor strikes and transport disruptions
        
        Args:
            region: Region to monitor
            date: Current date
            forecast_days: Days to forecast ahead
        
        Returns:
            Disruption assessment
        
        TODO: ADVANCED LABOR MONITORING
        1. Union calendar integration
        2. Historical strike pattern analysis
        3. Social media protest sentiment
        4. Government labor department APIs
        5. Transport association announcements
        6. Truck driver union monitoring
        7. Railway strike schedules
        8. Port worker union calendars
        9. Predictive strike probability models
        10. Alternative route planning during strikes
        """
        
        result = {
            'strikes_detected': [],
            'risk_level': 'Low',
            'affected_days': 0,
            'lead_time_buffer_needed': 0,
            'alternative_actions': []
        }
        
        for day_offset in range(forecast_days):
            check_date = date + timedelta(days=day_offset)
            sentiments = self.scan_market_intelligence(check_date, region)
            
            for sentiment in sentiments:
                if sentiment.topic == "Labor_Strike":
                    result['strikes_detected'].append({
                        'date': check_date.strftime('%Y-%m-%d'),
                        'severity': sentiment.severity,
                        'description': sentiment.description,
                        'states': sentiment.affected_states
                    })
                    
                    result['affected_days'] += 1
                    result['lead_time_buffer_needed'] = max(
                        result['lead_time_buffer_needed'],
                        sentiment.lead_time_buffer_days
                    )
                    
                    if sentiment.severity == "High":
                        result['risk_level'] = 'High'
                    elif result['risk_level'] == 'Low':
                        result['risk_level'] = 'Medium'
        
        # Generate alternative actions
        if result['strikes_detected']:
            result['alternative_actions'].append("Advance procurement before strike dates")
            result['alternative_actions'].append(f"Add {result['lead_time_buffer_needed']} day buffer to lead times")
            
            if result['risk_level'] == 'High':
                result['alternative_actions'].append("Consider air freight for critical materials")
                result['alternative_actions'].append("Pre-position inventory in affected regions")
        
        return result
    
    def monitor_commodity_prices(self,
                                material_category: str,
                                date: datetime) -> Dict[str, any]:
        """
        Monitor commodity price trends and spikes
        
        Args:
            material_category: Category to monitor (Steel, Copper, etc.)
            date: Current date
        
        Returns:
            Price trend analysis
        
        TODO: REAL-TIME PRICE INTEGRATION
        1. Bloomberg API for metal prices
        2. London Metal Exchange (LME) integration
        3. Multi Commodity Exchange (MCX) India
        4. Cement manufacturers association pricing
        5. Oil price tracking (Brent, WTI)
        6. Currency exchange rate impact
        7. Import duty change tracking
        8. GST rate change monitoring
        9. Futures price analysis
        10. Predictive price movement models
        11. Optimal procurement timing recommendations
        12. Hedging strategy suggestions
        """
        
        result = {
            'current_multiplier': 1.0,
            'trend': 'Stable',
            'spike_detected': False,
            'recommended_action': 'Continue normal procurement',
            'price_forecast': []
        }
        
        # Check sentiment data for price spikes
        sentiments = self.scan_market_intelligence(date)
        
        for sentiment in sentiments:
            if sentiment.topic == "Commodity_Price_Spike":
                result['spike_detected'] = True
                result['current_multiplier'] = sentiment.price_multiplier
                result['trend'] = 'Increasing'
                
                if sentiment.severity == "High":
                    result['recommended_action'] = 'URGENT: Lock in prices now, bulk procurement'
                else:
                    result['recommended_action'] = 'Consider forward contracts'
        
        # TODO: Add ML-based price prediction
        # forecast = self._predict_price_trend(material_category, date, forecast_days=90)
        # result['price_forecast'] = forecast
        
        return result
    
    def assess_policy_impacts(self,
                            date: datetime,
                            region: Optional[str] = None) -> List[Dict[str, any]]:
        """
        Assess impact of policy changes
        
        Args:
            date: Current date
            region: Optional region filter
        
        Returns:
            List of policy impacts
        
        TODO: POLICY MONITORING
        1. Government gazette notification monitoring
        2. GST council meeting outcome tracking
        3. Budget announcement analysis
        4. State government policy changes
        5. Environmental regulation updates
        6. Power sector reforms tracking
        7. Import/export policy changes
        8. Tariff and duty modifications
        9. Subsidy scheme announcements
        10. Industry incentive programs
        """
        
        impacts = []
        sentiments = self.scan_market_intelligence(date, region)
        
        for sentiment in sentiments:
            if sentiment.topic == "Policy_Change":
                impact = {
                    'date': date.strftime('%Y-%m-%d'),
                    'region': sentiment.region,
                    'description': sentiment.description,
                    'severity': sentiment.severity,
                    'action_required': sentiment.recommended_action,
                    'affected_states': sentiment.affected_states
                }
                impacts.append(impact)
        
        return impacts
    
    def generate_risk_report(self,
                           date: datetime,
                           region: str,
                           projects: List[Project]) -> Dict[str, any]:
        """
        Generate comprehensive risk report for a region
        
        Args:
            date: Report date
            region: Region to analyze
            projects: List of active projects
        
        Returns:
            Comprehensive risk assessment
        
        TODO: ADVANCED RISK ANALYTICS
        1. Risk scoring model (ML-based)
        2. Risk correlation analysis
        3. Cascading risk identification
        4. Portfolio risk optimization
        5. Scenario planning (best/worst case)
        6. Risk mitigation cost-benefit analysis
        7. Insurance recommendation engine
        8. Contingency planning automation
        """
        
        report = {
            'date': date.strftime('%Y-%m-%d'),
            'region': region,
            'overall_risk_level': 'Low',
            'active_alerts': [],
            'projects_at_risk': [],
            'financial_exposure': 0.0,
            'recommended_actions': []
        }
        
        # Scan all intelligence
        sentiments = self.scan_market_intelligence(date, region)
        
        # Analyze each project
        for project in projects:
            if project.region != region or not project.is_active():
                continue
            
            project_risks = []
            
            # RoW check
            row_status = self.check_row_status(project, date)
            if row_status['risk_level'] in ['High', 'Critical']:
                project_risks.append(f"RoW: {row_status['risk_level']}")
                report['projects_at_risk'].append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'risk_type': 'RoW',
                    'risk_level': row_status['risk_level']
                })
            
            # TODO: Add more risk dimensions
            # - Financial risk (budget overrun probability)
            # - Timeline risk (delay probability)
            # - Quality risk (contractor performance)
            # - Safety risk (accident probability)
        
        # Overall risk level
        if any(s.severity == 'Critical' for s in sentiments):
            report['overall_risk_level'] = 'Critical'
        elif any(s.severity == 'High' for s in sentiments):
            report['overall_risk_level'] = 'High'
        elif any(s.severity == 'Medium' for s in sentiments):
            report['overall_risk_level'] = 'Medium'
        
        # Active alerts
        for sentiment in sentiments:
            if sentiment.severity in ['High', 'Critical']:
                report['active_alerts'].append({
                    'topic': sentiment.topic,
                    'severity': sentiment.severity,
                    'description': sentiment.description,
                    'action': sentiment.recommended_action
                })
        
        return report
    
    def _log_alert(self, sentiment: MarketSentiment) -> None:
        """
        Log critical alert for tracking
        
        TODO: ALERT MANAGEMENT
        1. Email notification system
        2. SMS alerts for critical issues
        3. Dashboard push notifications
        4. Slack/Teams integration
        5. Alert deduplication
        6. Alert escalation rules
        7. Alert acknowledgment tracking
        """
        self.alert_history.append({
            'timestamp': datetime.now(),
            'date': sentiment.date,
            'region': sentiment.region,
            'topic': sentiment.topic,
            'severity': sentiment.severity,
            'description': sentiment.description
        })
    
    def get_alert_history(self, days: int = 30) -> List[Dict]:
        """Get recent alert history"""
        cutoff = datetime.now() - timedelta(days=days)
        return [a for a in self.alert_history if a['timestamp'] > cutoff]


# TODO: FUTURE SENTINEL AGENT FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. REAL-TIME DATA SOURCES
   - News API integration (Google News, NewsAPI.org)
   - Social media monitoring (Twitter API, Reddit)
   - Government portal scrapers (e-Gazette, state portals)
   - Commodity price APIs (Bloomberg, Reuters, MCX)
   - Legal database integration (court cases, RoW disputes)
   - Weather API (already in weather_service.py)

2. NATURAL LANGUAGE PROCESSING
   - Sentiment analysis on news articles
   - Entity recognition (company names, locations, materials)
   - Topic classification (RoW, strike, price, policy)
   - Summarization of long documents
   - Translation (regional language news)
   - Keyword extraction and trending topics

3. MACHINE LEARNING MODELS
   - Risk prediction models (probability of delays, cost overruns)
   - Price forecasting (commodity prices, labor costs)
   - Strike probability prediction
   - RoW resolution timeline estimation
   - Sentiment trend analysis
   - Anomaly detection in supply chain

4. ADVANCED ANALYTICS
   - Correlation analysis (which events cause which risks)
   - Cascading risk identification
   - Portfolio optimization under uncertainty
   - Scenario planning and simulation
   - Cost-benefit analysis of mitigation strategies
   - Insurance and hedging recommendations

5. INTEGRATION CAPABILITIES
   - ERP system integration (SAP, Oracle)
   - Project management tools (Primavera, MS Project)
   - Communication platforms (Slack, Teams, Email)
   - BI tools (Tableau, Power BI)
   - Mobile app for alerts
   - Voice alerts (Alexa, Google Assistant)

6. SPECIALIZED MONITORS
   - Environmental clearance tracking
   - Forest clearance status
   - Archaeological site proximity
   - Wildlife protection area conflicts
   - Community engagement metrics
   - Stakeholder sentiment analysis
"""


if __name__ == "__main__":
    """Test Sentinel Agent"""
    from datetime import datetime
    
    agent = SentinelAgent()
    
    print("Testing Sentinel Agent...")
    print("="*70)
    
    # Test market scan
    test_date = datetime(2025, 1, 15)
    sentiments = agent.scan_market_intelligence(test_date, "Northern")
    
    print(f"\nMarket Intelligence for {test_date.strftime('%Y-%m-%d')}:")
    for sentiment in sentiments:
        print(f"  Topic: {sentiment.topic}")
        print(f"  Severity: {sentiment.severity}")
        print(f"  Region: {sentiment.region}")
        print(f"  Action: {sentiment.recommended_action}")
        print()
    
    # Test labor disruption detection
    labor_check = agent.detect_labor_disruptions("Western", test_date)
    print(f"Labor Disruption Check:")
    print(f"  Risk Level: {labor_check['risk_level']}")
    print(f"  Strikes Detected: {len(labor_check['strikes_detected'])}")
    if labor_check['alternative_actions']:
        print(f"  Actions: {labor_check['alternative_actions'][0]}")
    
    print("\n✓ Sentinel Agent test complete!")
