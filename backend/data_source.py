"""
Simple data source module for Agents Marketplace
Supports both CSV files and PostgreSQL database
"""
import pandas as pd
import psycopg2
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging
from config import CSV_PATHS, DATABASE_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource:
    """Simple data source class that can read from CSV or PostgreSQL"""
    
    def __init__(self):
        self.data_source = DATABASE_CONFIG["data_source"]
        self.csv_paths = CSV_PATHS
        self.db_config = DATABASE_CONFIG
        
    def get_table_data(self, table_name: str) -> pd.DataFrame:
        """
        Get data from specified table
        Args:
            table_name: Name of the table (agents, demo_assets, etc.)
        Returns:
            pandas DataFrame with table data
        """
        if self.data_source == "csv":
            return self._get_csv_data(table_name)
        elif self.data_source == "postgres":
            return self._get_postgres_data(table_name)
        else:
            raise ValueError(f"Unknown data source: {self.data_source}")
    
    def _get_csv_data(self, table_name: str) -> pd.DataFrame:
        """Read data from CSV file with multiple encoding attempts"""
        if table_name not in self.csv_paths:
            raise ValueError(f"Unknown table: {table_name}")
        
        csv_path = self.csv_paths[table_name]
        
        if not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return pd.DataFrame()
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                logger.info(f"Loaded {len(df)} rows from {table_name} using {encoding} encoding")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading CSV {table_name} with {encoding}: {e}")
                continue
        
        logger.error(f"Failed to read CSV {table_name} with any encoding")
        return pd.DataFrame()
    
    def _get_postgres_data(self, table_name: str) -> pd.DataFrame:
        """Read data from PostgreSQL database"""
        try:
            # Create connection
            conn = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config["username"],
                password=self.db_config["password"]
            )
            
            # Read data
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, conn)
            
            conn.close()
            logger.info(f"Loaded {len(df)} rows from PostgreSQL table {table_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading from PostgreSQL {table_name}: {e}")
            return pd.DataFrame()
    
    def get_agents(self) -> pd.DataFrame:
        """Get all agents"""
        return self.get_table_data("agents")
    
    def get_demo_assets(self) -> pd.DataFrame:
        """Get all demo assets"""
        return self.get_table_data("demo_assets")
    
    def get_deployments(self) -> pd.DataFrame:
        """Get all deployment services"""
        return self.get_table_data("deployments")
    
    def get_docs(self) -> pd.DataFrame:
        """Get all documentation"""
        return self.get_table_data("docs")
    
    def get_isvs(self) -> pd.DataFrame:
        """Get all ISVs"""
        return self.get_table_data("isv")
    
    def get_resellers(self) -> pd.DataFrame:
        """Get all resellers"""
        return self.get_table_data("reseller")
    
    def get_capabilities_mapping(self) -> pd.DataFrame:
        """Get capabilities mapping table"""
        return self.get_table_data("capabilities_mapping")
    
    def get_auth(self) -> pd.DataFrame:
        """Get authentication table"""
        return self.get_table_data("auth")
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict]:
        """Get specific agent by ID"""
        agents_df = self.get_agents()
        agent = agents_df[agents_df['agent_id'] == agent_id]
        
        if agent.empty:
            return None
        
        return agent.iloc[0].to_dict()
    
    def get_demo_assets_by_agent(self, agent_id: str) -> pd.DataFrame:
        """Get demo assets for specific agent"""
        assets_df = self.get_demo_assets()
        return assets_df[assets_df['agent_id'] == agent_id]
    
    def get_deployments_by_capability(self, capability_id: str) -> pd.DataFrame:
        """Get deployment services for specific capability"""
        deployments_df = self.get_deployments()
        return deployments_df[deployments_df['by_capability_id'] == capability_id]
    
    def get_capabilities_by_agent(self, agent_id: str) -> pd.DataFrame:
        """Get capabilities for specific agent"""
        mapping_df = self.get_capabilities_mapping()
        return mapping_df[mapping_df['agent_id'] == agent_id]
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with email and password"""
        auth_df = self.get_auth()
        user = auth_df[(auth_df['email'] == email) & (auth_df['password'] == password) & (auth_df['is_active'] == 'yes')]
        
        if user.empty:
            return None
        
        return user.iloc[0].to_dict()
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        auth_df = self.get_auth()
        user = auth_df[auth_df['email'] == email]
        
        if user.empty:
            return None
        
        return user.iloc[0].to_dict()
    
    def get_agents_by_isv(self, isv_id: str) -> pd.DataFrame:
        """Get all agents for a specific ISV"""
        agents_df = self.get_agents()
        return agents_df[agents_df['isv_id'] == isv_id]
    
    def save_isv_data(self, isv_data: Dict) -> bool:
        """Save new ISV data to CSV file"""
        try:
            isv_df = self.get_isvs()
            
            # Convert to DataFrame and append
            new_row = pd.DataFrame([isv_data])
            updated_df = pd.concat([isv_df, new_row], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["isv"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved new ISV: {isv_data['isv_id']}")
            return True
        except Exception as e:
            logger.error(f"Error saving ISV data: {e}")
            return False
    
    def save_auth_data(self, auth_data: Dict) -> bool:
        """Save new auth data to CSV file"""
        try:
            auth_df = self.get_auth()
            
            # Convert to DataFrame and append
            new_row = pd.DataFrame([auth_data])
            updated_df = pd.concat([auth_df, new_row], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["auth"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved new auth record: {auth_data['auth_id']}")
            return True
        except Exception as e:
            logger.error(f"Error saving auth data: {e}")
            return False
    
    def get_next_isv_id(self) -> str:
        """Generate next sequential ISV ID"""
        try:
            isv_df = self.get_isvs()
            if isv_df.empty:
                return "isv_001"
            
            # Extract numeric part and find max
            existing_ids = isv_df['isv_id'].str.extract(r'isv_(\d+)')[0].astype(int)
            next_num = existing_ids.max() + 1
            
            return f"isv_{next_num:03d}"
        except Exception as e:
            logger.error(f"Error generating ISV ID: {e}")
            return f"isv_{len(isv_df) + 1:03d}"
    
    def get_next_auth_id(self) -> str:
        """Generate next sequential Auth ID"""
        try:
            auth_df = self.get_auth()
            if auth_df.empty:
                return "auth_001"
            
            # Extract numeric part and find max
            existing_ids = auth_df['auth_id'].str.extract(r'auth_(\d+)')[0].astype(int)
            next_num = existing_ids.max() + 1
            
            return f"auth_{next_num:03d}"
        except Exception as e:
            logger.error(f"Error generating Auth ID: {e}")
            return f"auth_{len(auth_df) + 1:03d}"
    
    def update_isv_data(self, isv_id: str, updated_data: Dict) -> bool:
        """Update existing ISV data in CSV file"""
        try:
            isv_df = self.get_isvs()
            
            # Find the row to update
            mask = isv_df['isv_id'] == isv_id
            if not mask.any():
                logger.error(f"ISV not found: {isv_id}")
                return False
            
            # Update the row
            for key, value in updated_data.items():
                if key in isv_df.columns:
                    isv_df.loc[mask, key] = value
            
            # Save back to CSV
            csv_path = self.csv_paths["isv"]
            isv_df.to_csv(csv_path, index=False)
            
            logger.info(f"Updated ISV: {isv_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating ISV data: {e}")
            return False
    
    def get_reseller_by_id(self, reseller_id: str) -> Optional[Dict]:
        """Get specific reseller by ID"""
        resellers_df = self.get_resellers()
        reseller = resellers_df[resellers_df['reseller_id'] == reseller_id]
        
        if reseller.empty:
            return None
        
        return reseller.iloc[0].to_dict()
    
    def save_reseller_data(self, reseller_data: Dict) -> bool:
        """Save new reseller data to CSV file"""
        try:
            resellers_df = self.get_resellers()
            
            # Convert to DataFrame and append
            new_row = pd.DataFrame([reseller_data])
            updated_df = pd.concat([resellers_df, new_row], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["reseller"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved new reseller: {reseller_data['reseller_id']}")
            return True
        except Exception as e:
            logger.error(f"Error saving reseller data: {e}")
            return False
    
    def update_reseller_data(self, reseller_id: str, updated_data: Dict) -> bool:
        """Update existing reseller data in CSV file"""
        try:
            resellers_df = self.get_resellers()
            
            # Find the row to update
            mask = resellers_df['reseller_id'] == reseller_id
            if not mask.any():
                logger.error(f"Reseller not found: {reseller_id}")
                return False
            
            # Update the row
            for key, value in updated_data.items():
                if key in resellers_df.columns:
                    resellers_df.loc[mask, key] = value
            
            # Save back to CSV
            csv_path = self.csv_paths["reseller"]
            resellers_df.to_csv(csv_path, index=False)
            
            logger.info(f"Updated reseller: {reseller_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating reseller data: {e}")
            return False
    
    def get_next_reseller_id(self) -> str:
        """Generate next sequential reseller ID"""
        try:
            resellers_df = self.get_resellers()
            if resellers_df.empty:
                return "reseller_001"
            
            # Extract numeric part and find max
            existing_ids = resellers_df['reseller_id'].str.extract(r'reseller_(\d+)')[0].astype(int)
            next_num = existing_ids.max() + 1
            
            return f"reseller_{next_num:03d}"
        except Exception as e:
            logger.error(f"Error generating reseller ID: {e}")
            return f"reseller_{len(resellers_df) + 1:03d}"
    
    def get_docs_by_agent(self, agent_id: str) -> pd.DataFrame:
        """Get documentation for specific agent"""
        docs_df = self.get_docs()
        return docs_df[docs_df['agent_id'] == agent_id]
    
    def get_next_agent_id(self) -> str:
        """Generate next sequential agent ID"""
        try:
            agents_df = self.get_agents()
            if agents_df.empty:
                return "agent_001"
            
            # Extract numeric part and find max
            existing_ids = agents_df['agent_id'].str.extract(r'agent_(\d+)')[0].astype(int)
            next_num = existing_ids.max() + 1
            
            return f"agent_{next_num:03d}"
        except Exception as e:
            logger.error(f"Error generating agent ID: {e}")
            return f"agent_{len(agents_df) + 1:03d}"
    
    def save_agent_data(self, agent_data: Dict) -> bool:
        """Save new agent data to CSV file"""
        try:
            agents_df = self.get_agents()
            
            # Convert to DataFrame and append
            new_row = pd.DataFrame([agent_data])
            updated_df = pd.concat([agents_df, new_row], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["agents"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved new agent: {agent_data['agent_id']}")
            return True
        except Exception as e:
            logger.error(f"Error saving agent data: {e}")
            return False
    
    def save_capabilities_mapping_data(self, capabilities_data: List[Dict]) -> bool:
        """Save capabilities mapping data to CSV file"""
        try:
            capabilities_df = self.get_capabilities_mapping()
            
            # Convert to DataFrame and append
            new_rows = pd.DataFrame(capabilities_data)
            updated_df = pd.concat([capabilities_df, new_rows], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["capabilities_mapping"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved {len(capabilities_data)} capability mappings")
            return True
        except Exception as e:
            logger.error(f"Error saving capabilities mapping data: {e}")
            return False
    
    def save_demo_assets_data(self, demo_assets_data: List[Dict]) -> bool:
        """Save demo assets data to CSV file"""
        try:
            demo_assets_df = self.get_demo_assets()
            
            # Convert to DataFrame and append
            new_rows = pd.DataFrame(demo_assets_data)
            updated_df = pd.concat([demo_assets_df, new_rows], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["demo_assets"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved {len(demo_assets_data)} demo assets")
            return True
        except Exception as e:
            logger.error(f"Error saving demo assets data: {e}")
            return False
    
    def save_docs_data(self, docs_data: Dict) -> bool:
        """Save documentation data to CSV file"""
        try:
            docs_df = self.get_docs()
            
            # Convert to DataFrame and append
            new_row = pd.DataFrame([docs_data])
            updated_df = pd.concat([docs_df, new_row], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["docs"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved documentation for agent: {docs_data['agent_id']}")
            return True
        except Exception as e:
            logger.error(f"Error saving docs data: {e}")
            return False
    
    def save_deployments_data(self, deployments_data: List[Dict]) -> bool:
        """Save deployments data to CSV file"""
        try:
            deployments_df = self.get_deployments()
            
            # Convert to DataFrame and append
            new_rows = pd.DataFrame(deployments_data)
            updated_df = pd.concat([deployments_df, new_rows], ignore_index=True)
            
            # Save back to CSV
            csv_path = self.csv_paths["deployments"]
            updated_df.to_csv(csv_path, index=False)
            
            logger.info(f"Saved {len(deployments_data)} deployments")
            return True
        except Exception as e:
            logger.error(f"Error saving deployments data: {e}")
            return False
    
    def update_agent_data(self, agent_id: str, updated_data: Dict) -> bool:
        """Update existing agent data in CSV file"""
        try:
            agents_df = self.get_agents()
            
            # Find the row to update
            mask = agents_df['agent_id'] == agent_id
            if not mask.any():
                logger.error(f"Agent not found: {agent_id}")
                return False
            
            # Update the row
            for key, value in updated_data.items():
                if key in agents_df.columns:
                    agents_df.loc[mask, key] = value
            
            # Save back to CSV
            csv_path = self.csv_paths["agents"]
            agents_df.to_csv(csv_path, index=False)
            
            logger.info(f"Updated agent: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating agent data: {e}")
            return False
    
    def health_check(self) -> Dict:
        """Check health of data source"""
        try:
            if self.data_source == "csv":
                # Check if CSV files exist
                missing_files = []
                for table_name, path in self.csv_paths.items():
                    if not path.exists():
                        missing_files.append(str(path))
                
                return {
                    "status": "healthy" if not missing_files else "degraded",
                    "data_source": self.data_source,
                    "missing_files": missing_files
                }
            
            elif self.data_source == "postgres":
                # Test database connection
                conn = psycopg2.connect(
                    host=self.db_config["host"],
                    port=self.db_config["port"],
                    database=self.db_config["database"],
                    user=self.db_config["username"],
                    password=self.db_config["password"]
                )
                conn.close()
                
                return {
                    "status": "healthy",
                    "data_source": self.data_source
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "data_source": self.data_source,
                "error": str(e)
            }

    def get_agent_requirements(self) -> pd.DataFrame:
        """Get all agent requirements"""
        return self.get_table_data("agent_requirements")
    
    def get_next_requirement_id(self) -> str:
        """Generate next sequential requirement ID"""
        try:
            requirements_df = self.get_agent_requirements()
            if requirements_df.empty:
                return "req_001"
            
            # Extract numeric part and find max
            existing_ids = requirements_df['requirement_id'].str.extract(r'req_(\d+)')[0].astype(int)
            next_num = existing_ids.max() + 1
            
            return f"req_{next_num:03d}"
        except Exception as e:
            logger.error(f"Error generating requirement ID: {e}")
            return f"req_{len(requirements_df) + 1:03d}"
    
    def save_agent_requirements_data(self, requirements_data: Dict) -> bool:
        """Save new agent requirements data to CSV file"""
        try:
            requirements_df = self.get_agent_requirements()
            
            # Add requirement ID and timestamps
            requirements_data['requirement_id'] = self.get_next_requirement_id()
            requirements_data['created_at'] = datetime.now().isoformat()
            requirements_data['updated_at'] = datetime.now().isoformat()
            requirements_data['status'] = 'discovered'
            
            # Convert to DataFrame and append
            new_requirement_df = pd.DataFrame([requirements_data])
            
            if requirements_df.empty:
                # First requirement
                new_requirement_df.to_csv(self.csv_paths["agent_requirements"], index=False)
            else:
                # Append to existing
                combined_df = pd.concat([requirements_df, new_requirement_df], ignore_index=True)
                combined_df.to_csv(self.csv_paths["agent_requirements"], index=False)
            
            logger.info(f"Agent requirements saved with ID: {requirements_data['requirement_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving agent requirements: {str(e)}")
            return False
    
    def update_agent_requirements_data(self, requirement_id: str, updated_data: Dict) -> bool:
        """Update existing agent requirements data"""
        try:
            requirements_df = self.get_agent_requirements()
            
            if requirements_df.empty:
                logger.warning("No agent requirements found to update")
                return False
            
            # Find and update the requirement
            mask = requirements_df['requirement_id'] == requirement_id
            if not mask.any():
                logger.warning(f"Agent requirement {requirement_id} not found")
                return False
            
            # Update the data
            for key, value in updated_data.items():
                if key in requirements_df.columns:
                    requirements_df.loc[mask, key] = value
            
            # Update timestamp
            requirements_df.loc[mask, 'updated_at'] = datetime.now().isoformat()
            
            # Save back to CSV
            requirements_df.to_csv(self.csv_paths["agent_requirements"], index=False)
            
            logger.info(f"Agent requirements {requirement_id} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating agent requirements: {str(e)}")
            return False

# Global data source instance
data_source = DataSource()
