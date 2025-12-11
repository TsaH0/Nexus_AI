"""
Prophet Forecaster - Time Series Forecasting for OpEx Demand
Uses Facebook Prophet for seasonal consumption forecasting with weather regressors
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("⚠️ Prophet not installed. Install with: pip install prophet")


@dataclass
class ProphetForecast:
    """Prophet forecast result"""
    material_id: str
    forecast_date: datetime
    predicted_quantity: float
    lower_bound: float
    upper_bound: float
    trend: float
    seasonal: float
    confidence: float
    reasoning: str


class ProphetForecaster:
    """
    Advanced time series forecasting using Facebook Prophet
    
    TODO: PRODUCTION ENHANCEMENTS
    1. Automated hyperparameter tuning (Bayesian optimization)
    2. Cross-validation for model selection
    3. Ensemble forecasting (Prophet + ARIMA + LSTM)
    4. Anomaly detection in historical data
    5. Model versioning and experiment tracking (MLflow)
    6. Real-time model retraining triggers
    7. Forecast accuracy monitoring (MAPE, RMSE tracking)
    8. Multi-horizon forecasting (1-day, 7-day, 30-day)
    9. Hierarchical forecasting (total → region → warehouse)
    10. External event modeling (holidays, strikes, festivals)
    """
    
    def __init__(self, 
                 historical_data_path: Optional[str] = None,
                 model_save_dir: Optional[str] = None):
        """
        Initialize Prophet forecaster
        
        Args:
            historical_data_path: Path to historical consumption CSV
            model_save_dir: Directory to save trained models
        
        TODO: MODEL INITIALIZATION ENHANCEMENTS
        1. Auto-detect seasonality from data
        2. Load pre-trained models from disk
        3. Distributed training for large datasets
        4. GPU acceleration support
        """
        
        if not PROPHET_AVAILABLE:
            raise ImportError("Prophet not installed. Run: pip install prophet")
        
        self.historical_data_path = historical_data_path or os.path.join(
            DATA_DIR, "generated", "historical_consumption.csv"
        )
        self.model_save_dir = model_save_dir or os.path.join(DATA_DIR, "models")
        
        # Create model directory
        os.makedirs(self.model_save_dir, exist_ok=True)
        
        # Cache for trained models
        self.models = {}  # {material_id: Prophet model}
        self.last_train_date = {}  # {material_id: datetime}
        
        # Load historical data
        self.historical_data = self._load_historical_data()
        
        # Prophet configuration
        self.prophet_params = {
            'yearly_seasonality': True,
            'weekly_seasonality': True,
            'daily_seasonality': False,
            'changepoint_prior_scale': 0.05,  # Flexibility of trend
            'seasonality_prior_scale': 10.0,  # Strength of seasonality
            'interval_width': 0.80,  # 80% confidence interval
        }
    
    def _load_historical_data(self) -> pd.DataFrame:
        """
        Load historical consumption data
        
        Returns:
            DataFrame with columns: date, material_id, quantity, temperature, rainfall
        """
        if not os.path.exists(self.historical_data_path):
            print(f"⚠️ Historical data not found: {self.historical_data_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(self.historical_data_path)
        
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif 'Date' in df.columns:
            df['date'] = pd.to_datetime(df['Date'])
        
        # Normalize column names
        column_mapping = {
            'Date': 'date',
            'Material_ID': 'material_id',
            'Consumption_Quantity': 'quantity',
            'Region': 'region'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Sort by date
        df = df.sort_values('date')
        
        return df
    
    def prepare_prophet_data(self, 
                            material_id: str,
                            region: Optional[str] = None,
                            include_regressors: bool = True) -> pd.DataFrame:
        """
        Prepare data in Prophet format (ds, y, regressors)
        
        Args:
            material_id: Material to prepare data for
            region: Optional region filter
            include_regressors: Whether to include weather regressors
        
        Returns:
            DataFrame with Prophet-compatible format
        """
        if self.historical_data.empty:
            return pd.DataFrame()
        
        # Filter for specific material
        mask = self.historical_data['material_id'] == material_id
        if region:
            mask &= self.historical_data['region'] == region
        
        material_data = self.historical_data[mask].copy()
        
        if material_data.empty:
            return pd.DataFrame()
        
        # Aggregate by date if multiple regions
        if region is None:
            material_data = material_data.groupby('date').agg({
                'quantity': 'sum',
                'temperature': 'mean',
                'rainfall': 'mean'
            }).reset_index()
        
        # Prophet requires 'ds' (datestamp) and 'y' (value) columns
        prophet_df = pd.DataFrame({
            'ds': material_data['date'],
            'y': material_data['quantity']
        })
        
        if include_regressors:
            if 'temperature' in material_data.columns:
                prophet_df['temperature'] = material_data['temperature'].values
            
            if 'rainfall' in material_data.columns:
                prophet_df['rainfall'] = material_data['rainfall'].values
        
        return prophet_df
    
    def train_model(self, 
                   material_id: str,
                   region: Optional[str] = None,
                   include_weather: bool = True,
                   save_model: bool = True) -> Optional[Prophet]:
        """
        Train Prophet model for a specific material
        
        Args:
            material_id: Material to train for
            region: Optional region filter
            include_weather: Whether to use weather as regressors
            save_model: Whether to save trained model to disk
        
        Returns:
            Trained Prophet model
        """
        # Prepare data
        prophet_df = self.prepare_prophet_data(material_id, region, include_weather)
        
        if prophet_df.empty:
            print(f"⚠️ No data available for {material_id}")
            return None
        
        # Check if we have enough data (Prophet needs at least 2 periods)
        if len(prophet_df) < 30:  # At least 30 days
            print(f"⚠️ Insufficient data for {material_id}: {len(prophet_df)} days")
            return None
        
        # Initialize Prophet model with suppressed logging
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            interval_width=0.80
        )
        
        # Add regressors if using weather
        if include_weather:
            if 'temperature' in prophet_df.columns:
                model.add_regressor('temperature')
            
            if 'rainfall' in prophet_df.columns:
                model.add_regressor('rainfall')
        
        try:
            # Suppress Prophet's verbose output
            import logging
            logging.getLogger('prophet').setLevel(logging.WARNING)
            logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
            
            # Fit model
            model.fit(prophet_df)
            
            # Cache model with key including region
            cache_key = f"{material_id}_{region}" if region else material_id
            self.models[cache_key] = model
            self.last_train_date[cache_key] = datetime.now()
            
            return model
        
        except Exception as e:
            print(f"❌ Error training model for {material_id}: {e}")
            return None
    
    def predict(self,
               material_id: str,
               region: Optional[str] = None,
               forecast_days: int = 30,
               include_weather: bool = True,
               future_weather: Optional[pd.DataFrame] = None) -> List[ProphetForecast]:
        """
        Generate forecast for a material
        
        Args:
            material_id: Material to forecast
            region: Optional region filter
            forecast_days: Number of days to forecast
            include_weather: Whether to use weather predictions
            future_weather: DataFrame with future weather (ds, temperature, rainfall)
        
        Returns:
            List of ProphetForecast objects
        """
        # Create cache key
        cache_key = f"{material_id}_{region}" if region else material_id
        
        # Get or train model
        if cache_key not in self.models:
            model = self.train_model(material_id, region, include_weather)
            if model is None:
                return []
        else:
            model = self.models[cache_key]
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=forecast_days)
        
        # Add weather regressors if the model was trained with them
        if include_weather:
            if future_weather is not None:
                # Merge future weather data
                future = future.merge(future_weather, on='ds', how='left')
            
            # Fill missing weather with reasonable defaults
            if 'temperature' in future.columns:
                future['temperature'].fillna(30.0, inplace=True)
            else:
                future['temperature'] = 30.0  # Default average temp
            
            if 'rainfall' in future.columns:
                future['rainfall'].fillna(5.0, inplace=True)
            else:
                future['rainfall'] = 5.0  # Default rainfall
        
        # Generate forecast
        try:
            forecast_df = model.predict(future)
            
            # Extract forecasts for future dates only
            forecast_df = forecast_df.tail(forecast_days)
            
            # Convert to ProphetForecast objects
            forecasts = []
            
            for _, row in forecast_df.iterrows():
                # Calculate confidence (based on interval width)
                pred_value = max(1, row['yhat'])
                uncertainty = row['yhat_upper'] - row['yhat_lower']
                confidence = max(0.0, min(1.0, 1.0 - (uncertainty / (2 * pred_value))))
                
                forecast = ProphetForecast(
                    material_id=material_id,
                    forecast_date=row['ds'].to_pydatetime(),
                    predicted_quantity=max(0, row['yhat']),  # Non-negative
                    lower_bound=max(0, row['yhat_lower']),
                    upper_bound=row['yhat_upper'],
                    trend=row.get('trend', 0),
                    seasonal=row.get('yearly', 0) + row.get('weekly', 0),
                    confidence=confidence,
                    reasoning=f"Prophet forecast for {material_id}: {row['yhat']:.0f} units"
                )
                
                forecasts.append(forecast)
            
            return forecasts
        
        except Exception as e:
            print(f"❌ Error predicting for {material_id}: {e}")
            return []
    
    def get_forecast_for_date(self,
                             material_id: str,
                             region: str,
                             forecast_date: datetime,
                             horizon_days: int = 30) -> int:
        """
        Get single forecast value for a specific date
        
        Args:
            material_id: Material to forecast
            region: Region
            forecast_date: Date to forecast for
            horizon_days: Forecast horizon
        
        Returns:
            Predicted quantity (int)
        """
        forecasts = self.predict(
            material_id=material_id,
            region=region,
            forecast_days=horizon_days
        )
        
        if not forecasts:
            return 0
        
        # Find forecast closest to requested date
        for f in forecasts:
            if f.forecast_date.date() == forecast_date.date():
                return int(f.predicted_quantity)
        
        # Return last forecast if date not found
        return int(forecasts[-1].predicted_quantity) if forecasts else 0
    
    def _generate_forecast_reasoning(self,
                                    material_id: str,
                                    forecast_row: pd.Series,
                                    model: Prophet) -> str:
        """
        Generate human-readable reasoning for forecast
        
        TODO: REASONING ENHANCEMENTS
        1. Component decomposition explanation
        2. Feature contribution analysis (SHAP values)
        3. Comparison with historical patterns
        4. Anomaly flags
        """
        
        reasoning_parts = []
        
        # Base forecast
        reasoning_parts.append(
            f"Predicted {forecast_row['yhat']:.1f} units for {material_id}"
        )
        
        # Trend component
        if 'trend' in forecast_row:
            trend_dir = "increasing" if forecast_row['trend'] > 0 else "decreasing"
            reasoning_parts.append(f"Trend: {trend_dir}")
        
        # Seasonal component
        if 'yearly' in forecast_row:
            seasonal = forecast_row.get('yearly', 0) + forecast_row.get('weekly', 0)
            if abs(seasonal) > 5:
                reasoning_parts.append(f"Seasonal effect: {seasonal:+.1f}")
        
        # Weather impact
        if 'temperature' in forecast_row:
            reasoning_parts.append(
                f"Temperature: {forecast_row['temperature']:.1f}°C"
            )
        
        if 'rainfall' in forecast_row:
            if forecast_row['rainfall'] > 50:
                reasoning_parts.append("Heavy rainfall expected")
        
        return " | ".join(reasoning_parts)
    
    def _save_model(self, model: Prophet, material_id: str):
        """
        Save trained model to disk
        
        TODO: MODEL PERSISTENCE ENHANCEMENTS
        1. Model versioning (timestamp, git hash)
        2. Model metadata (training date, accuracy metrics)
        3. Model registry (MLflow, DVC)
        4. Compression for storage efficiency
        """
        
        import pickle
        
        model_path = os.path.join(
            self.model_save_dir, 
            f"prophet_{material_id}.pkl"
        )
        
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            print(f"✓ Model saved: {model_path}")
        except Exception as e:
            print(f"⚠️ Failed to save model: {e}")
    
    def load_model(self, material_id: str) -> Optional[Prophet]:
        """
        Load trained model from disk
        
        TODO: MODEL LOADING ENHANCEMENTS
        1. Version-aware loading (load specific version)
        2. Lazy loading (load only when needed)
        3. Model validation (check compatibility)
        """
        
        import pickle
        
        model_path = os.path.join(
            self.model_save_dir,
            f"prophet_{material_id}.pkl"
        )
        
        if not os.path.exists(model_path):
            return None
        
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            self.models[material_id] = model
            return model
        
        except Exception as e:
            print(f"⚠️ Failed to load model: {e}")
            return None
    
    def train_all_materials(self, materials: List[str]) -> Dict[str, bool]:
        """
        Train models for all materials
        
        Args:
            materials: List of material IDs
        
        Returns:
            Dictionary of {material_id: success}
        
        TODO: BATCH TRAINING ENHANCEMENTS
        1. Parallel training (multiprocessing)
        2. Priority-based training (critical materials first)
        3. Incremental training (only retrain if data changed)
        4. Distributed training (Spark, Dask)
        """
        
        results = {}
        
        for material_id in materials:
            print(f"Training model for {material_id}...")
            model = self.train_model(material_id)
            results[material_id] = model is not None
        
        success_count = sum(results.values())
        print(f"\n✓ Trained {success_count}/{len(materials)} models")
        
        return results
    
    def evaluate_model(self, 
                      material_id: str,
                      test_days: int = 30) -> Dict[str, float]:
        """
        Evaluate model accuracy using holdout test set
        
        Args:
            material_id: Material to evaluate
            test_days: Number of days to use as test set
        
        Returns:
            Dictionary of accuracy metrics
        
        TODO: EVALUATION ENHANCEMENTS
        1. Cross-validation with time series splits
        2. Multiple metrics (MAE, MAPE, RMSE, R²)
        3. Business metrics (cost of forecast error)
        4. Comparison with baseline (naive, moving average)
        5. Forecast horizon analysis (accuracy by day)
        """
        
        # Get data
        prophet_df = self.prepare_prophet_data(material_id)
        
        if prophet_df.empty or len(prophet_df) < test_days + 30:
            return {'error': 'Insufficient data'}
        
        # Split into train/test
        train_df = prophet_df[:-test_days]
        test_df = prophet_df[-test_days:]
        
        # Train on training set
        model = Prophet(**self.prophet_params)
        
        if 'temperature' in train_df.columns:
            model.add_regressor('temperature')
        if 'rainfall' in train_df.columns:
            model.add_regressor('rainfall')
        
        train_df['is_monsoon'] = train_df['ds'].dt.month.isin([6, 7, 8, 9])
        model.add_seasonality(
            name='monsoon', period=365.25, fourier_order=5,
            condition_name='is_monsoon'
        )
        
        model.fit(train_df)
        
        # Predict on test set
        test_df['is_monsoon'] = test_df['ds'].dt.month.isin([6, 7, 8, 9])
        forecast = model.predict(test_df)
        
        # Calculate metrics
        actual = test_df['y'].values
        predicted = forecast['yhat'].values
        
        mae = np.mean(np.abs(actual - predicted))
        mape = np.mean(np.abs((actual - predicted) / (actual + 1))) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        
        return {
            'mae': mae,
            'mape': mape,
            'rmse': rmse,
            'test_days': test_days
        }


# TODO: FUTURE PROPHET FORECASTER FEATURES
"""
PRODUCTION-READY ENHANCEMENTS:

1. ADVANCED MODELING
   - Hierarchical forecasting (top-down, bottom-up)
   - Transfer learning across similar materials
   - Deep learning models (Temporal Fusion Transformer)
   - Bayesian structural time series

2. REAL-TIME CAPABILITIES
   - Streaming predictions (Apache Kafka)
   - Online learning (model updates with new data)
   - A/B testing of model versions
   - Champion/challenger framework
   - Real-time accuracy monitoring

3. EXPLAINABILITY
   - SHAP values for feature importance
   - Component decomposition visualization
   - Counterfactual explanations (what-if)
   - Uncertainty quantification
   - Forecast confidence scoring

4. PRODUCTION INFRASTRUCTURE
   - Model versioning (MLflow, DVC)
   - Model registry with approval workflow
   - Automated retraining pipelines
   - Model monitoring (data drift, concept drift)
   - Rollback mechanisms

5. ADVANCED FEATURES
   - Multi-horizon forecasting (1-day, 7-day, 30-day)
   - Scenario forecasting (best/worst/likely)
   - Conditional forecasting (if project starts)
   - Anomaly detection in forecasts
   - Forecast accuracy by segment (material, region)

6. INTEGRATION
   - Real-time weather APIs (OpenWeatherMap, IMD)
   - Project scheduling systems
   - ERP systems (actual consumption data)
   - Business intelligence dashboards
   - Alerting systems (Slack, email)
"""


if __name__ == "__main__":
    """Test Prophet forecaster"""
    
    print("Testing Prophet Forecaster...")
    print("="*70)
    
    if not PROPHET_AVAILABLE:
        print("❌ Prophet not installed. Install with: pip install prophet")
        sys.exit(1)
    
    # Create forecaster
    forecaster = ProphetForecaster()
    
    # Check if historical data exists
    if forecaster.historical_data.empty:
        print("⚠️ No historical data found. Run data_factory.py first.")
        print("   python src/core/data_factory.py")
    else:
        print(f"✓ Loaded {len(forecaster.historical_data)} historical records")
        
        # Get unique materials
        materials = forecaster.historical_data['material_id'].unique()
        print(f"✓ Found {len(materials)} materials in historical data")
        
        # Train model for first material
        if len(materials) > 0:
            test_material = materials[0]
            print(f"\nTraining model for {test_material}...")
            
            model = forecaster.train_model(test_material)
            
            if model:
                print(f"✓ Model trained successfully")
                
                # Generate forecast
                print(f"\nGenerating 7-day forecast...")
                forecasts = forecaster.predict(test_material, forecast_days=7)
                
                if forecasts:
                    print(f"✓ Generated {len(forecasts)} forecasts")
                    print("\nSample forecasts:")
                    for forecast in forecasts[:3]:
                        print(f"  {forecast.forecast_date.strftime('%Y-%m-%d')}: "
                              f"{forecast.predicted_quantity:.1f} units "
                              f"(confidence: {forecast.confidence:.2f})")
                
                # Evaluate model
                print(f"\nEvaluating model accuracy...")
                metrics = forecaster.evaluate_model(test_material, test_days=30)
                
                if 'error' not in metrics:
                    print(f"✓ Evaluation complete:")
                    print(f"  MAE:  {metrics['mae']:.2f}")
                    print(f"  MAPE: {metrics['mape']:.2f}%")
                    print(f"  RMSE: {metrics['rmse']:.2f}")
    
    print("\n✓ Prophet forecaster test complete!")
