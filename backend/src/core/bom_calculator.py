"""
BOM (Bill of Materials) Calculator
Calculates material requirements based on engineering standards
"""

import os
import pandas as pd
from typing import Dict
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import *
from src.core.models import Project, ProjectType, ProjectStage, ProjectStatus, TerrainType


class BOMCalculator:
    """Calculates material requirements for projects"""
    
    def __init__(self):
        """Initialize BOM calculator with standards data"""
        self.bom_standards = self._load_bom_standards()
    
    def _load_bom_standards(self) -> pd.DataFrame:
        """Load BOM standards from CSV"""
        bom_file = os.path.join(RAW_DATA_DIR, "Master_BOM_Standards.csv")
        
        if not os.path.exists(bom_file):
            print(f"⚠️  BOM standards file not found: {bom_file}")
            print("Please run data_factory.py first to generate required files.")
            return pd.DataFrame()
        
        return pd.read_csv(bom_file)
    
    def calculate_capex_demand(self, project: Project) -> Dict[str, int]:
        """
        Calculate material requirements for a project based on current stage.
        
        Args:
            project: Project object
        
        Returns:
            Dictionary mapping material_id to required quantity
        
        Raises:
            ValueError: If project is None or has invalid attributes
        """
        if project is None:
            raise ValueError("Project cannot be None")
        
        if self.bom_standards.empty:
            return {}
        
        # Validate project has required attributes
        if project.project_type is None or project.voltage_kv is None:
            return {}
        
        # Filter BOM standards for this project type and voltage
        project_type_str = project.project_type.value
        voltage_kv = project.voltage_kv
        
        relevant_bom = self.bom_standards[
            (self.bom_standards['Project_Type'] == project_type_str) &
            (self.bom_standards['Voltage_kV'] == voltage_kv)
        ]
        
        if relevant_bom.empty:
            return {}
        
        # Get stage multiplier
        stage_multiplier = self._get_stage_multiplier(project.stage, relevant_bom)
        
        # Calculate quantities
        material_requirements = {}
        
        for _, row in relevant_bom.iterrows():
            material_id = row['Material_ID']
            qty_per_unit = row['Quantity_Per_Unit']
            
            # Calculate base quantity based on project specifications
            if project.project_type == ProjectType.TRANSMISSION_LINE:
                # For transmission lines, multiply by length
                base_qty = qty_per_unit * (project.length_km or 0)
            else:
                # For substations, use per-unit quantities
                base_qty = qty_per_unit
            
            # Apply stage multiplier
            stage_qty = int(base_qty * stage_multiplier)
            
            # Apply terrain multiplier for certain materials
            if material_id in ["MAT-001", "MAT-002", "MAT-003", "MAT-022"]:  # Structural materials
                terrain_mult = TERRAIN_MULTIPLIERS.get(project.terrain_type.value, 1.0)
                stage_qty = int(stage_qty * terrain_mult)
            
            material_requirements[material_id] = stage_qty
        
        return material_requirements
    
    def _get_stage_multiplier(self, stage: ProjectStage, bom_df: pd.DataFrame) -> float:
        """
        Get the material requirement percentage for current project stage
        
        Args:
            stage: Current project stage
            bom_df: BOM dataframe
        
        Returns:
            Multiplier (0.0 to 1.0)
        """
        if bom_df.empty:
            return 0.0
        
        # Get first row (all rows have same stage percentages)
        row = bom_df.iloc[0]
        
        stage_col_map = {
            ProjectStage.PLANNING: 'Stage_Planning_Pct',
            ProjectStage.FOUNDATION: 'Stage_Foundation_Pct',
            ProjectStage.CONSTRUCTION: 'Stage_Construction_Pct',
            ProjectStage.COMMISSIONING: 'Stage_Commissioning_Pct',
            ProjectStage.COMPLETED: 0.0
        }
        
        col_name = stage_col_map.get(stage, 'Stage_Planning_Pct')
        return row[col_name] if col_name in row else 0.1
    
    def calculate_progressive_demand(self, project: Project) -> Dict[ProjectStage, Dict[str, int]]:
        """
        Calculate material requirements for all future stages
        
        Args:
            project: Project object
        
        Returns:
            Dictionary mapping stages to material requirements
        """
        if self.bom_standards.empty:
            return {}
        
        # Get BOM for this project
        project_type_str = project.project_type.value
        voltage_kv = project.voltage_kv
        
        relevant_bom = self.bom_standards[
            (self.bom_standards['Project_Type'] == project_type_str) &
            (self.bom_standards['Voltage_kV'] == voltage_kv)
        ]
        
        if relevant_bom.empty:
            return {}
        
        # Calculate for each stage
        all_stages = [
            ProjectStage.PLANNING,
            ProjectStage.FOUNDATION,
            ProjectStage.CONSTRUCTION,
            ProjectStage.COMMISSIONING
        ]
        
        progressive_demand = {}
        
        for stage in all_stages:
            # Temporarily set project stage
            original_stage = project.stage
            project.stage = stage
            
            # Calculate demand
            stage_demand = self.calculate_capex_demand(project)
            progressive_demand[stage] = stage_demand
            
            # Restore original stage
            project.stage = original_stage
        
        return progressive_demand
    
    def estimate_total_project_cost(self, project: Project, materials_dict: Dict[str, object]) -> float:
        """
        Estimate total material cost for a project
        
        Args:
            project: Project object
            materials_dict: Dictionary mapping material_id to Material object
        
        Returns:
            Estimated total cost in INR
        """
        material_requirements = self.calculate_capex_demand(project)
        
        total_cost = 0.0
        
        for material_id, quantity in material_requirements.items():
            if material_id in materials_dict:
                material = materials_dict[material_id]
                cost = material.base_price * quantity
                
                # Add GST
                gst_rate = GST_RATES.get(material.category, 0.18)
                cost_with_tax = cost * (1 + gst_rate)
                
                total_cost += cost_with_tax
        
        return round(total_cost, 2)
    
    def validate_bom_completeness(self) -> bool:
        """
        Validate that BOM standards are loaded and complete
        
        Returns:
            True if BOM standards are valid
        """
        if self.bom_standards.empty:
            return False
        
        required_columns = [
            'Project_Type', 'Voltage_kV', 'Material_ID', 
            'Quantity_Per_Unit', 'Unit',
            'Stage_Planning_Pct', 'Stage_Foundation_Pct',
            'Stage_Construction_Pct', 'Stage_Commissioning_Pct'
        ]
        
        return all(col in self.bom_standards.columns for col in required_columns)


if __name__ == "__main__":
    """Test BOM calculator"""
    from src.core.models import Material
    from datetime import datetime
    
    calculator = BOMCalculator()
    
    if calculator.validate_bom_completeness():
        print("✓ BOM Standards loaded successfully!")
        print(f"  Total BOM entries: {len(calculator.bom_standards)}")
        
        # Create a test project
        test_project = Project(
            id="TEST-001",
            name="Test_400kV_Line",
            project_type=ProjectType.TRANSMISSION_LINE,
            region="Northern",
            state="Delhi",
            stage=ProjectStage.CONSTRUCTION,
            status=ProjectStatus.ACTIVE,
            start_date=datetime.now(),
            expected_end_date=datetime.now(),
            latitude=28.6,
            longitude=77.2,
            length_km=100.0,
            voltage_kv=400,
            terrain_type=TerrainType.PLAIN
        )
        
        # Calculate requirements
        requirements = calculator.calculate_capex_demand(test_project)
        print(f"\n✓ Test calculation for {test_project.name}:")
        for mat_id, qty in requirements.items():
            print(f"  {mat_id}: {qty} units")
    else:
        print("❌ BOM Standards validation failed!")
