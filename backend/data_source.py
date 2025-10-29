"""
Simple data source module for Agents Marketplace
Supports both CSV files and PostgreSQL database
"""
import pandas as pd
import psycopg2
from psycopg2 import pool
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging
import os
from datetime import datetime
from config import CSV_PATHS, DATABASE_CONFIG
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource:
    """Simple data source class that can read from CSV or PostgreSQL"""
    
    def __init__(self):
        self.data_source = DATABASE_CONFIG["data_source"]
        self.csv_paths = CSV_PATHS
        self.db_config = DATABASE_CONFIG
        self._connection_pool = None
        self._lock = threading.Lock()
        
        # Initialize connection pool if using PostgreSQL
        if self.data_source == "postgres":
            self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            # Get connection parameters
            if "DATABASE_URL" in self.db_config and self.db_config["DATABASE_URL"]:
                db_url = self.db_config["DATABASE_URL"]
                
                # Handle JDBC format URLs (jdbc:postgresql://...)
                if db_url.startswith("jdbc:postgresql://"):
                    db_url = self._convert_jdbc_to_postgresql_url(db_url)
                    logger.info("Converted JDBC URL to PostgreSQL format")
                
                # Handle postgres:// URLs (convert to postgresql://)
                elif db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                # Add SSL parameters for Render/cloud databases
                if "render.com" in db_url or "heroku.com" in db_url or "neon.tech" in db_url:
                    # Check if sslmode is already in the URL
                    if "sslmode=" not in db_url:
                        if "?" in db_url:
                            db_url += "&sslmode=require"
                        else:
                            db_url += "?sslmode=require"
                        logger.info("Added SSL mode (require) for cloud database")
                    elif "sslmode=prefer" in db_url:
                        # Replace prefer with require for Render
                        db_url = db_url.replace("sslmode=prefer", "sslmode=require")
                        logger.info("Changed SSL mode from prefer to require for Render database")
                
                # Create connection pool with URL
                # For Render, we need sslmode=require with proper connection settings
                # Add connection timeout and keepalive settings if not present
                if "connect_timeout=" not in db_url:
                    db_url += "&connect_timeout=10" if "?" in db_url else "?connect_timeout=10"
                if "keepalives=" not in db_url:
                    db_url += "&keepalives=1"
                if "keepalives_idle=" not in db_url:
                    db_url += "&keepalives_idle=30"
                
                try:
                    self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=1,
                        maxconn=10,
                        dsn=db_url
                    )
                except Exception as ssl_error:
                    # If SSL connection fails, try with sslmode=require without certificate verification
                    if "SSL" in str(ssl_error) or "ssl" in str(ssl_error).lower():
                        logger.warning(f"SSL connection failed with sslmode=require, trying sslmode=require with no verification: {str(ssl_error)}")
                        # Replace or add sslmode=require
                        if "sslmode=" in db_url:
                            db_url = db_url.split("?")[0] + "?sslmode=require&sslcert=&sslkey=&sslrootcert=&sslcrl="
                        else:
                            db_url = db_url + "?sslmode=require&sslcert=&sslkey=&sslrootcert=&sslcrl="
                        
                        try:
                            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                                minconn=1,
                                maxconn=10,
                                dsn=db_url
                            )
                            logger.info("Connection pool initialized with SSL (no cert verification)")
                        except Exception as retry_error:
                            logger.error(f"SSL connection retry also failed: {str(retry_error)}")
                            raise retry_error
                    else:
                        raise ssl_error
            else:
                # Create connection pool with individual parameters
                self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=self.db_config["host"],
                    port=self.db_config["port"],
                    database=self.db_config["database"],
                    user=self.db_config["username"],
                    password=self.db_config["password"]
                )
            
            logger.info("PostgreSQL connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing connection pool: {str(e)}")
            logger.error(f"Database config data_source: {self.data_source}")
            logger.error(f"Database config has DATABASE_URL: {'DATABASE_URL' in self.db_config}")
            if 'DATABASE_URL' in self.db_config:
                db_url_preview = self.db_config['DATABASE_URL'][:50] + "..." if len(str(self.db_config.get('DATABASE_URL', ''))) > 50 else self.db_config.get('DATABASE_URL', '')
                logger.error(f"DATABASE_URL preview: {db_url_preview}")
            else:
                logger.error(f"Using individual parameters - host: {self.db_config.get('host', 'N/A')}, database: {self.db_config.get('database', 'N/A')}")
            self._connection_pool = None
            # Don't raise here - let the app start, but pool will be None
    
    def _get_connection(self):
        """Get PostgreSQL database connection from pool"""
        # If pool is not initialized, try to initialize it
        if not self._connection_pool:
            logger.warning("Connection pool not initialized, attempting to initialize...")
            self._init_connection_pool()
            
            # If still not initialized after retry, raise error
            if not self._connection_pool:
                raise Exception("Connection pool not initialized and initialization failed")
        
        try:
            return self._connection_pool.getconn()
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            # Try to re-initialize pool if connection fails
            logger.info("Attempting to re-initialize connection pool...")
            self._connection_pool = None
            self._init_connection_pool()
            
            if not self._connection_pool:
                raise Exception(f"Failed to get connection and re-initialization failed: {str(e)}")
            
            # Retry getting connection after re-initialization
            try:
                return self._connection_pool.getconn()
            except Exception as retry_e:
                logger.error(f"Error getting connection after re-initialization: {retry_e}")
                raise
    
    def _return_connection(self, conn):
        """Return connection to pool"""
        if self._connection_pool and conn:
            try:
                self._connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Error returning connection to pool: {e}")
        
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
                df = pd.read_csv(csv_path, encoding=encoding, quoting=1)  # quoting=1 handles multiline fields
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
        """Read data from PostgreSQL database using connection pool"""
        conn = None
        try:
            # Get connection from pool
            conn = self._get_connection()
            
            # Read data (suppress pandas warning about psycopg2 connection)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                query = f"SELECT * FROM {table_name}"
                df = pd.read_sql(query, conn)
            
            logger.info(f"Loaded {len(df)} rows from PostgreSQL table {table_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading from PostgreSQL {table_name}: {e}")
            return pd.DataFrame()
        finally:
            # Always return connection to pool
            if conn:
                self._return_connection(conn)
    
    def _convert_jdbc_to_postgresql_url(self, jdbc_url: str) -> str:
        """Convert JDBC URL to PostgreSQL connection string format"""
        try:
            import re
            from urllib.parse import urlparse, parse_qs
            
            # Remove jdbc: prefix
            url_without_jdbc = jdbc_url.replace("jdbc:", "")
            
            # Parse the URL
            parsed = urlparse(url_without_jdbc)
            
            # Get components
            host = parsed.hostname
            port = parsed.port or 5432
            
            # Remove leading / from path to get database name
            database = parsed.path.lstrip('/')
            
            # Parse query parameters
            params = parse_qs(parsed.query)
            username = params.get('user', [''])[0] or params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            
            # Build PostgreSQL URL
            postgresql_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            
            logger.info(f"Converted JDBC URL successfully")
            return postgresql_url
              
        except Exception as e:
            logger.error(f"Error converting JDBC URL: {e}")
            raise
    
    def _save_postgres_data(self, table_name: str, data: Dict) -> bool:
        """Save data to PostgreSQL database using connection pool"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get existing data to get column names
            df = self._get_postgres_data(table_name)
            if not df.empty:
                columns = list(df.columns)
            else:
                # If table is empty, use the keys from data
                columns = list(data.keys())
            
            # Build INSERT query
            valid_columns = [col for col in columns if col in data]
            placeholders = ', '.join(['%s'] * len(valid_columns))
            column_names = ', '.join([f'"{col}"' for col in valid_columns])
            
            query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            values = [data[col] for col in valid_columns]
            
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            
            logger.info(f"Saved data to PostgreSQL table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data to PostgreSQL {table_name}: {e}")
            return False
        finally:
            # Always return connection to pool
            if conn:
                self._return_connection(conn)
    
    def _update_postgres_data(self, table_name: str, key_column: str, key_value: str, data: Dict) -> bool:
        """Update data in PostgreSQL database using connection pool"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build UPDATE query
            set_clauses = []
            values = []
            for key, value in data.items():
                if key != key_column:  # Don't update the key column itself
                    set_clauses.append(f'"{key}" = %s')
                    values.append(value)
            
            if not set_clauses:
                logger.warning("No fields to update")
                return False
            
            query = f'UPDATE {table_name} SET {", ".join(set_clauses)} WHERE "{key_column}" = %s'
            values.append(key_value)
            
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            
            logger.info(f"Updated data in PostgreSQL table {table_name} where {key_column}={key_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating data in PostgreSQL {table_name}: {e}")
            return False
        finally:
            # Always return connection to pool
            if conn:
                self._return_connection(conn)
    
    def _delete_postgres_data(self, table_name: str, key_column: str, key_value: str) -> bool:
        """Delete data from PostgreSQL database using connection pool"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = f'DELETE FROM {table_name} WHERE "{key_column}" = %s'
            cursor.execute(query, (key_value,))
            conn.commit()
            cursor.close()
            
            logger.info(f"Deleted data from PostgreSQL table {table_name} where {key_column}={key_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting data from PostgreSQL {table_name}: {e}")
            return False
        finally:
            # Always return connection to pool
            if conn:
                self._return_connection(conn)
    
    def _save_csv_data(self, table_name: str, data: Union[Dict, List[Dict]]) -> bool:
        """Save data to CSV file"""
        try:
            if table_name not in self.csv_paths:
                logger.error(f"Unknown table: {table_name}")
                return False
            
            csv_path = self.csv_paths[table_name]
            
            # Get existing data
            df = self._get_csv_data(table_name)
            
            # Convert to DataFrame
            if isinstance(data, list):
                new_df = pd.DataFrame(data)
            else:
                new_df = pd.DataFrame([data])
            
            # Append
            updated_df = pd.concat([df, new_df], ignore_index=True)
            
            # Save
            updated_df.to_csv(csv_path, index=False)
            logger.info(f"Saved data to CSV {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving CSV data {table_name}: {e}")
            return False
    
    def _update_csv_data(self, table_name: str, key_column: str, key_value: str, data: Dict) -> bool:
        """Update data in CSV file"""
        try:
            if table_name not in self.csv_paths:
                logger.error(f"Unknown table: {table_name}")
                return False
            
            csv_path = self.csv_paths[table_name]
            
            # Get existing data
            df = self._get_csv_data(table_name)
            
            # Find the row to update
            mask = df[key_column] == key_value
            if not mask.any():
                logger.error(f"Row not found in {table_name} where {key_column}={key_value}")
                return False
            
            # Update the row
            for key, value in data.items():
                if key in df.columns:
                    df.loc[mask, key] = value
            
            # Save
            df.to_csv(csv_path, index=False)
            logger.info(f"Updated CSV {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV data {table_name}: {e}")
            return False
    
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
    
    def get_isv_by_id(self, isv_id: str) -> Dict:
        """Get ISV by ID"""
        try:
            isv_df = self.get_table_data("isv")
            isv_row = isv_df[isv_df['isv_id'] == isv_id]
            if not isv_row.empty:
                return isv_row.iloc[0].to_dict()
            return {}
        except Exception as e:
            logger.error(f"Error getting ISV by ID {isv_id}: {str(e)}")
            return {}
    
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
        """Save new ISV data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("isv", isv_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("isv", isv_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving ISV data: {e}")
            return False
    
    def save_auth_data(self, auth_data: Dict) -> bool:
        """Save new auth data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("auth", auth_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("auth", auth_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
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
        """Update existing ISV data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("isv", "isv_id", isv_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("isv", "isv_id", isv_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
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
        """Save new reseller data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("reseller", reseller_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("reseller", reseller_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving reseller data: {e}")
            return False
    
    def update_reseller_data(self, reseller_id: str, updated_data: Dict) -> bool:
        """Update existing reseller data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("reseller", "reseller_id", reseller_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("reseller", "reseller_id", reseller_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
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
        """Save new agent data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("agents", agent_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("agents", agent_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving agent data: {e}")
            return False
    
    def save_capabilities_mapping_data(self, capabilities_data: List[Dict]) -> bool:
        """Save capabilities mapping data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("capabilities_mapping", capabilities_data)
            elif self.data_source == "postgres":
                # For list data, save each item individually
                for item in capabilities_data:
                    if not self._save_postgres_data("capabilities_mapping", item):
                        return False
                logger.info(f"Saved {len(capabilities_data)} capability mappings")
                return True
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving capabilities mapping data: {e}")
            return False
    
    def save_demo_assets_data(self, demo_assets_data: List[Dict]) -> bool:
        """Save demo assets data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("demo_assets", demo_assets_data)
            elif self.data_source == "postgres":
                # For list data, save each item individually
                for item in demo_assets_data:
                    if not self._save_postgres_data("demo_assets", item):
                        return False
                logger.info(f"Saved {len(demo_assets_data)} demo assets")
                return True
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving demo assets data: {e}")
            return False
    
    def save_docs_data(self, docs_data: Dict) -> bool:
        """Save documentation data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("docs", docs_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("docs", docs_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving docs data: {e}")
            return False
    
    def save_deployments_data(self, deployments_data: List[Dict]) -> bool:
        """Save deployments data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("deployments", deployments_data)
            elif self.data_source == "postgres":
                # For list data, save each item individually
                for item in deployments_data:
                    if not self._save_postgres_data("deployments", item):
                        return False
                logger.info(f"Saved {len(deployments_data)} deployments")
                return True
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving deployments data: {e}")
            return False
    
    def update_agent_data(self, agent_id: str, updated_data: Dict) -> bool:
        """Update existing agent data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("agents", "agent_id", agent_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("agents", "agent_id", agent_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating agent data: {e}")
            return False
    
    def update_docs_data(self, agent_id: str, updated_data: Dict) -> bool:
        """Update existing docs data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("docs", "agent_id", agent_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("docs", "agent_id", agent_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating docs data: {e}")
            return False
    
    def update_deployments_data(self, by_capability_id: str, updated_data: Dict) -> bool:
        """Update existing deployments data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("deployments", "by_capability_id", by_capability_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("deployments", "by_capability_id", by_capability_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating deployments data: {e}")
            return False
    
    def update_demo_assets_data(self, demo_asset_id: str, updated_data: Dict) -> bool:
        """Update existing demo assets data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("demo_assets", "demo_asset_id", demo_asset_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("demo_assets", "demo_asset_id", demo_asset_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating demo assets data: {e}")
            return False
    
    def get_chat_history(self) -> pd.DataFrame:
        """Load chat history data from CSV file or PostgreSQL"""
        return self.get_table_data("chat_history")
    
    def save_chat_history_data(self, chat_data: Dict) -> bool:
        """Save new chat history data to CSV file or PostgreSQL"""
        try:
            # Add timestamps
            chat_data['created_at'] = datetime.now().isoformat()
            chat_data['updated_at'] = datetime.now().isoformat()
            chat_data['status'] = 'active'
            
            if self.data_source == "csv":
                return self._save_csv_data("chat_history", chat_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("chat_history", chat_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving chat history: {str(e)}")
            return False
    
    def update_chat_history_data(self, session_id: str, updated_data: Dict) -> bool:
        """Update existing chat history data in CSV file or PostgreSQL"""
        try:
            updated_data['updated_at'] = datetime.now().isoformat()
            
            if self.data_source == "csv":
                return self._update_csv_data("chat_history", "session_id", session_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("chat_history", "session_id", session_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating chat history: {e}")
            return False
    
    def delete_chat_history_data(self, session_id: str) -> bool:
        """Delete chat history data from CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                chat_history_df = self.get_chat_history()
                mask = chat_history_df['session_id'] == session_id
                if not mask.any():
                    logger.error(f"Chat history not found for session: {session_id}")
                    return False
                chat_history_df = chat_history_df[~mask]
                csv_path = self.csv_paths["chat_history"]
                chat_history_df.to_csv(csv_path, index=False)
                logger.info(f"Deleted chat history for session: {session_id}")
                return True
            elif self.data_source == "postgres":
                return self._delete_postgres_data("chat_history", "session_id", session_id)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error deleting chat history: {e}")
            return False
    
    def get_enquiries(self) -> pd.DataFrame:
        """Get all enquiries"""
        return self.get_table_data("enquiries")
    
    def save_enquiries_data(self, enquiry_data: Dict) -> bool:
        """Save new enquiry data to CSV file or PostgreSQL"""
        try:
            # Generate enquiry ID
            enquiries_df = self.get_enquiries()
            if enquiries_df.empty:
                enquiry_id = "enquiry_001"
            else:
                max_id = int(enquiries_df['enquiry_id'].str.replace('enquiry_', '').astype(int).max())
                enquiry_id = f"enquiry_{max_id + 1:03d}"
            
            # Add required fields
            enquiry_data['enquiry_id'] = enquiry_id
            enquiry_data['created_at'] = datetime.now().isoformat()
            enquiry_data['status'] = 'new'
            
            if self.data_source == "csv":
                return self._save_csv_data("enquiries", enquiry_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("enquiries", enquiry_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving enquiry: {str(e)}")
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
                # Test database connection using pool
                conn = self._get_connection()
                self._return_connection(conn)
                
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
    
    def close_connection_pool(self):
        """Close the connection pool"""
        if self._connection_pool:
            try:
                self._connection_pool.closeall()
                logger.info("Connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

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
        """Save new agent requirements data to CSV file or PostgreSQL"""
        try:
            # Add requirement ID and timestamps
            requirements_data['requirement_id'] = self.get_next_requirement_id()
            requirements_data['created_at'] = datetime.now().isoformat()
            requirements_data['updated_at'] = datetime.now().isoformat()
            requirements_data['status'] = 'discovered'
            
            if self.data_source == "csv":
                return self._save_csv_data("agent_requirements", requirements_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("agent_requirements", requirements_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving agent requirements: {str(e)}")
            return False
    
    def update_agent_requirements_data(self, requirement_id: str, updated_data: Dict) -> bool:
        """Update existing agent requirements data in CSV file or PostgreSQL"""
        try:
            updated_data['updated_at'] = datetime.now().isoformat()
            
            if self.data_source == "csv":
                return self._update_csv_data("agent_requirements", "requirement_id", requirement_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("agent_requirements", "requirement_id", requirement_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating agent requirements: {str(e)}")
            return False
    
    # Client methods
    def get_clients(self) -> pd.DataFrame:
        """Get all clients"""
        return self.get_table_data("client")
    
    def get_next_client_id(self) -> str:
        """Generate next sequential client ID"""
        try:
            clients_df = self.get_clients()
            if clients_df.empty:
                return "client_001"
            
            # Extract numeric part from client IDs
            client_ids = clients_df['client_id'].tolist()
            max_num = 0
            
            for client_id in client_ids:
                if client_id.startswith('client_'):
                    try:
                        num = int(client_id.split('_')[1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue
            
            next_num = max_num + 1
            return f"client_{next_num:03d}"
            
        except Exception as e:
            logger.error(f"Error generating next client ID: {str(e)}")
            return "client_001"
    
    def save_client_data(self, client_data: Dict) -> bool:
        """Save new client data to CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._save_csv_data("client", client_data)
            elif self.data_source == "postgres":
                return self._save_postgres_data("client", client_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error saving client data: {str(e)}")
            return False
    
    def update_client_data(self, client_id: str, updated_data: Dict) -> bool:
        """Update existing client data in CSV file or PostgreSQL"""
        try:
            if self.data_source == "csv":
                return self._update_csv_data("client", "client_id", client_id, updated_data)
            elif self.data_source == "postgres":
                return self._update_postgres_data("client", "client_id", client_id, updated_data)
            else:
                logger.error(f"Unknown data source: {self.data_source}")
                return False
        except Exception as e:
            logger.error(f"Error updating client data: {str(e)}")
            return False

# Global data source instance
data_source = DataSource()
