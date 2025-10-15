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
    
    def get_docs_by_agent(self, agent_id: str) -> pd.DataFrame:
        """Get documentation for specific agent"""
        docs_df = self.get_docs()
        return docs_df[docs_df['agent_id'] == agent_id]
    
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

# Global data source instance
data_source = DataSource()
