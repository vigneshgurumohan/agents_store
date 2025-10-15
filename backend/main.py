"""
FastAPI application for Agents Marketplace
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import Dict, List, Optional
import pandas as pd
from data_source import data_source
from config import API_CONFIG

# Create FastAPI app
app = FastAPI(
    title=API_CONFIG["title"],
    version=API_CONFIG["version"],
    description=API_CONFIG["description"]
)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def root():
    """Root endpoint - redirect to agents page"""
    return {"message": "Agents Marketplace API", "docs": "/docs"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return data_source.health_check()

@app.get("/api/agents")
async def get_all_agents():
    """Get all agents with basic info"""
    try:
        agents_df = data_source.get_agents()
        agents_list = agents_df.to_dict('records')
        
        # Replace NaN values with "na"
        for agent in agents_list:
            for key, value in agent.items():
                if pd.isna(value):
                    agent[key] = "na"
        
        return {"agents": agents_list, "total": len(agents_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agents: {str(e)}")

@app.get("/api/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed agent information with all joined data"""
    try:
        # Get basic agent info
        agent = data_source.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        # Replace NaN values with "na"
        for key, value in agent.items():
            if pd.isna(value):
                agent[key] = "na"
        
        # Get capabilities for this agent
        capabilities_df = data_source.get_capabilities_by_agent(agent_id)
        capabilities = capabilities_df.to_dict('records') if not capabilities_df.empty else []
        
        # Get all deployments for this agent's capabilities
        all_deployments = []
        for cap in capabilities:
            cap_id = cap.get('by_capability_id')
            if cap_id:
                deployments = data_source.get_deployments_by_capability(cap_id)
                deployments_list = deployments.to_dict('records') if not deployments.empty else []
                # Add capability info to each deployment
                for dep in deployments_list:
                    dep['capability_name'] = cap.get('by_capability', 'na')
                all_deployments.extend(deployments_list)
        
        # Replace NaN values in deployments
        for dep in all_deployments:
            for key, value in dep.items():
                if pd.isna(value):
                    dep[key] = "na"
        
        # Get demo assets
        demo_assets_df = data_source.get_demo_assets_by_agent(agent_id)
        demo_assets = demo_assets_df.to_dict('records') if not demo_assets_df.empty else []
        
        # Replace NaN values in demo assets
        for asset in demo_assets:
            for key, value in asset.items():
                if pd.isna(value):
                    asset[key] = "na"
        
        # Get documentation for this specific agent
        docs_df = data_source.get_docs_by_agent(agent_id)
        docs = docs_df.to_dict('records') if not docs_df.empty else []
        
        # Replace NaN values in docs
        for doc in docs:
            for key, value in doc.items():
                if pd.isna(value):
                    doc[key] = "na"
        
        # Get ISV info
        isv_id = agent.get('isv_id', 'na')
        isvs_df = data_source.get_isvs()
        isv_info = None
        if isv_id != 'na':
            isv_match = isvs_df[isvs_df['isv_id'] == isv_id]
            if not isv_match.empty:
                isv_info = isv_match.iloc[0].to_dict()
                # Replace NaN values
                for key, value in isv_info.items():
                    if pd.isna(value):
                        isv_info[key] = "na"
        
        return {
            "agent": agent,
            "capabilities": capabilities,
            "deployments": all_deployments,
            "demo_assets": demo_assets,
            "documentation": docs,
            "isv_info": isv_info or {"isv_name": "na"}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agent details: {str(e)}")

@app.get("/api/capabilities")
async def get_all_capabilities():
    """Get all unique capabilities"""
    try:
        mapping_df = data_source.get_capabilities_mapping()
        capabilities = mapping_df[['by_capability_id', 'by_capability']].drop_duplicates()
        capabilities_list = capabilities.to_dict('records')
        
        # Replace NaN values
        for cap in capabilities_list:
            for key, value in cap.items():
                if pd.isna(value):
                    cap[key] = "na"
        
        return {"capabilities": capabilities_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching capabilities: {str(e)}")

@app.get("/agents", response_class=HTMLResponse)
async def agents_listing():
    """Serve the agents listing page"""
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agents listing page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading agents page: {str(e)}")

@app.get("/agent/{agent_name}", response_class=HTMLResponse)
async def agent_page(agent_name: str):
    """Serve the agent page HTML"""
    try:
        # Read the HTML file
        with open("../frontend/agent.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace placeholder with actual agent name
        html_content = html_content.replace("{{agent_name}}", agent_name)
        
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent page template not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading agent page: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_CONFIG["host"], port=API_CONFIG["port"])
