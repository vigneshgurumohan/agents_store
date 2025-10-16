"""
FastAPI application for Agents Marketplace
"""
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, List, Optional
import pandas as pd
import uuid
from datetime import datetime
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

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """ISV login endpoint"""
    try:
        user = data_source.authenticate_user(email, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        return {
            "success": True,
            "user": {
                "auth_id": user["auth_id"],
                "user_id": user["user_id"],
                "email": user["email"],
                "role": user["role"]
            },
            "redirect": f"/isv/profile/{user['user_id']}" if user["role"] == "isv" else f"/reseller/profile/{user['user_id']}" if user["role"] == "reseller" else "/admin/isv"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.post("/api/auth/signup")
async def signup(
    # Common fields
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    # ISV specific fields
    isv_name: str = Form(""),
    isv_address: str = Form(""),
    isv_domain: str = Form(""),
    isv_mob_no: str = Form(""),
    # Reseller specific fields
    reseller_name: str = Form(""),
    reseller_address: str = Form(""),
    reseller_domain: str = Form(""),
    reseller_mob_no: str = Form(""),
    whitelisted_domain: str = Form("")
):
    """Registration endpoint for ISV and Reseller"""
    try:
        # Check if email already exists
        existing_user = data_source.get_user_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate role
        if role not in ["isv", "reseller"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'isv' or 'reseller'")
        
        # Generate new IDs following the existing pattern
        auth_id = data_source.get_next_auth_id()
        
        if role == "isv":
            # ISV registration
            if not isv_name:
                raise HTTPException(status_code=400, detail="Company name is required for ISV registration")
            
            user_id = data_source.get_next_isv_id()
            
            # Create ISV record
            isv_data = {
                "isv_id": user_id,
                "isv_name": isv_name,
                "isv_address": isv_address,
                "isv_domain": isv_domain,
                "isv_mob_no": isv_mob_no,
                "isv_email_no": email,
                "admin_approved": "no"
            }
            
            # Save ISV data
            data_saved = data_source.save_isv_data(isv_data)
            redirect_url = "/isv/login"
            
        elif role == "reseller":
            # Reseller registration
            if not reseller_name:
                raise HTTPException(status_code=400, detail="Company name is required for reseller registration")
            
            user_id = data_source.get_next_reseller_id()
            
            # Create reseller record
            reseller_data = {
                "reseller_id": user_id,
                "reseller_name": reseller_name,
                "reseller_address": reseller_address,
                "reseller_domain": reseller_domain,
                "reseller_mob_no": reseller_mob_no,
                "reseller_email_no": email,
                "whitelisted_domain": whitelisted_domain,
                "admin_approved": "no"
            }
            
            # Save reseller data
            data_saved = data_source.save_reseller_data(reseller_data)
            redirect_url = "/reseller/login"
        
        # Create auth record
        auth_data = {
            "auth_id": auth_id,
            "user_id": user_id,
            "email": email,
            "password": password,
            "role": role,
            "is_active": "yes",
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Save auth data
        auth_saved = data_source.save_auth_data(auth_data)
        
        if not (data_saved and auth_saved):
            raise HTTPException(status_code=500, detail="Failed to save registration data")
        
        return {
            "success": True,
            "message": f"{role.upper()} registration successful! Please wait for admin approval.",
            "user_id": user_id,
            "role": role,
            "redirect": redirect_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup error: {str(e)}")

# ============================================================================
# ISV ENDPOINTS
# ============================================================================

@app.get("/api/isv/profile/{isv_id}")
async def get_isv_profile(isv_id: str):
    """Get ISV profile with agents and statistics"""
    try:
        # Get ISV data
        isvs_df = data_source.get_isvs()
        isv = isvs_df[isvs_df['isv_id'] == isv_id]
        
        if isv.empty:
            raise HTTPException(status_code=404, detail="ISV not found")
        
        isv_data = isv.iloc[0].to_dict()
        
        # Replace NaN values
        for key, value in isv_data.items():
            if pd.isna(value):
                isv_data[key] = "na"
        
        # Get agents for this ISV
        agents_df = data_source.get_agents_by_isv(isv_id)
        agents = agents_df.to_dict('records') if not agents_df.empty else []
        
        # Replace NaN values in agents
        for agent in agents:
            for key, value in agent.items():
                if pd.isna(value):
                    agent[key] = "na"
        
        # Calculate statistics
        stats = {
            "total_agents": len(agents),
            "approved_agents": len([a for a in agents if a.get('admin_approved') == 'yes']),
            "total_capabilities": len(set([cap for agent in agents for cap in str(agent.get('by_capability', '')).split(',') if cap.strip()])),
            "isv_approved": isv_data.get('admin_approved', 'no') == 'yes'
        }
        
        return {
            "isv": isv_data,
            "agents": agents,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ISV profile: {str(e)}")

@app.put("/api/isv/profile/{isv_id}")
async def update_isv_profile(
    isv_id: str,
    isv_name: str = Form(...),
    isv_address: str = Form(""),
    isv_domain: str = Form(""),
    isv_mob_no: str = Form(""),
    isv_email: str = Form(...)
):
    """Update ISV profile"""
    try:
        # Prepare update data
        update_data = {
            "isv_name": isv_name,
            "isv_address": isv_address,
            "isv_domain": isv_domain,
            "isv_mob_no": isv_mob_no,
            "isv_email_no": isv_email
        }
        
        # Update the CSV file
        success = data_source.update_isv_data(isv_id, update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update profile")
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "isv_id": isv_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/api/admin/isvs")
async def get_all_isvs():
    """Admin: Get all ISVs with statistics"""
    try:
        isvs_df = data_source.get_isvs()
        isvs = isvs_df.to_dict('records')
        
        # Replace NaN values
        for isv in isvs:
            for key, value in isv.items():
                if pd.isna(value):
                    isv[key] = "na"
        
        # Add statistics for each ISV
        for isv in isvs:
            agents_df = data_source.get_agents_by_isv(isv['isv_id'])
            isv['agent_count'] = len(agents_df)
            isv['approved_agent_count'] = len(agents_df[agents_df['admin_approved'] == 'yes'])
        
        return {"isvs": isvs, "total": len(isvs)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ISVs: {str(e)}")

@app.put("/api/admin/isvs/{isv_id}")
async def admin_update_isv(
    isv_id: str,
    isv_name: str = Form(...),
    isv_address: str = Form(""),
    isv_domain: str = Form(""),
    isv_mob_no: str = Form(""),
    isv_email: str = Form(...),
    admin_approved: str = Form("no")
):
    """Admin: Update any ISV"""
    try:
        # Prepare update data
        update_data = {
            "isv_name": isv_name,
            "isv_address": isv_address,
            "isv_domain": isv_domain,
            "isv_mob_no": isv_mob_no,
            "isv_email_no": isv_email,
            "admin_approved": admin_approved
        }
        
        # Update the CSV file
        success = data_source.update_isv_data(isv_id, update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update ISV")
        
        return {
            "success": True,
            "message": "ISV updated successfully",
            "isv_id": isv_id,
            "admin_approved": admin_approved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating ISV: {str(e)}")

# ============================================================================
# RESELLER ENDPOINTS
# ============================================================================

@app.get("/api/reseller/profile/{reseller_id}")
async def get_reseller_profile(reseller_id: str):
    """Get reseller profile with statistics"""
    try:
        # Get reseller data
        reseller = data_source.get_reseller_by_id(reseller_id)
        
        if not reseller:
            raise HTTPException(status_code=404, detail="Reseller not found")
        
        # Replace NaN values
        for key, value in reseller.items():
            if pd.isna(value):
                reseller[key] = "na"
        
        # Calculate statistics (resellers don't have agents, so basic stats)
        stats = {
            "is_reseller_approved": reseller.get('admin_approved', 'no') == 'yes',
            "whitelisted_domain": reseller.get('whitelisted_domain', 'na')
        }
        
        return {
            "reseller": reseller,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reseller profile: {str(e)}")

@app.put("/api/reseller/profile/{reseller_id}")
async def update_reseller_profile(
    reseller_id: str,
    reseller_name: str = Form(...),
    reseller_address: str = Form(""),
    reseller_domain: str = Form(""),
    reseller_mob_no: str = Form(""),
    reseller_email: str = Form(...),
    whitelisted_domain: str = Form("")
):
    """Update reseller profile"""
    try:
        # Prepare update data
        update_data = {
            "reseller_name": reseller_name,
            "reseller_address": reseller_address,
            "reseller_domain": reseller_domain,
            "reseller_mob_no": reseller_mob_no,
            "reseller_email_no": reseller_email,
            "whitelisted_domain": whitelisted_domain
        }
        
        # Update the CSV file
        success = data_source.update_reseller_data(reseller_id, update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update profile")
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "reseller_id": reseller_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")

# ============================================================================
# ADMIN RESELLER ENDPOINTS
# ============================================================================

@app.get("/api/admin/resellers")
async def get_all_resellers():
    """Admin: Get all resellers"""
    try:
        resellers_df = data_source.get_resellers()
        resellers = resellers_df.to_dict('records')
        
        # Replace NaN values
        for reseller in resellers:
            for key, value in reseller.items():
                if pd.isna(value):
                    reseller[key] = "na"
        
        return {"resellers": resellers, "total": len(resellers)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resellers: {str(e)}")

@app.put("/api/admin/resellers/{reseller_id}")
async def admin_update_reseller(
    reseller_id: str,
    reseller_name: str = Form(...),
    reseller_address: str = Form(""),
    reseller_domain: str = Form(""),
    reseller_mob_no: str = Form(""),
    reseller_email: str = Form(...),
    whitelisted_domain: str = Form(""),
    admin_approved: str = Form("no")
):
    """Admin: Update any reseller"""
    try:
        # Prepare update data
        update_data = {
            "reseller_name": reseller_name,
            "reseller_address": reseller_address,
            "reseller_domain": reseller_domain,
            "reseller_mob_no": reseller_mob_no,
            "reseller_email_no": reseller_email,
            "whitelisted_domain": whitelisted_domain,
            "admin_approved": admin_approved
        }
        
        # Update the CSV file
        success = data_source.update_reseller_data(reseller_id, update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update reseller")
        
        return {
            "success": True,
            "message": "Reseller updated successfully",
            "reseller_id": reseller_id,
            "admin_approved": admin_approved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating reseller: {str(e)}")

# ============================================================================
# AGENT ONBOARDING ENDPOINTS
# ============================================================================

@app.post("/api/agent/onboard")
async def onboard_agent(
    # Agent details
    agent_name: str = Form(""),
    asset_type: str = Form(""),
    by_persona: str = Form(""),
    by_value: str = Form(""),
    description: str = Form(""),
    features: str = Form(""),
    roi: str = Form(""),
    tags: str = Form(""),
    demo_link: str = Form(""),
    isv_id: str = Form(...),
    
    # Capabilities (comma-separated)
    capabilities: str = Form(""),
    
    # Demo assets (JSON string)
    demo_assets: str = Form(""),
    
    # Documentation
    sdk_details: str = Form(""),
    swagger_details: str = Form(""),
    sample_input: str = Form(""),
    sample_output: str = Form(""),
    security_details: str = Form(""),
    related_files: str = Form(""),
    
    # Deployments (JSON string)
    deployments: str = Form("")
):
    """ISV: Create new agent with all related data"""
    try:
        # Generate new agent ID
        agent_id = data_source.get_next_agent_id()
        
        # Create agent data
        agent_data = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "asset_type": asset_type,
            "by_persona": by_persona,
            "by_value": by_value,
            "description": description,
            "features": features,
            "roi": roi,
            "tags": tags,
            "demo_link": demo_link,
            "isv_id": isv_id,
            "admin_approved": "no"  # Requires admin approval
        }
        
        # Save agent data
        agent_saved = data_source.save_agent_data(agent_data)
        
        if not agent_saved:
            raise HTTPException(status_code=500, detail="Failed to save agent data")
        
        # Process capabilities
        if capabilities:
            capabilities_list = [cap.strip() for cap in capabilities.split(",") if cap.strip()]
            capabilities_data = []
            
            for capability in capabilities_list:
                capabilities_data.append({
                    "agent_id": agent_id,
                    "by_capability_id": f"cap_{len(capabilities_data) + 1:03d}",  # Generate capability ID
                    "by_capability": capability
                })
            
            if capabilities_data:
                data_source.save_capabilities_mapping_data(capabilities_data)
        
        # Process demo assets
        if demo_assets:
            try:
                import json
                demo_assets_list = json.loads(demo_assets) if demo_assets else []
                demo_assets_data = []
                
                for i, asset in enumerate(demo_assets_list):
                    demo_assets_data.append({
                        "demo_asset_id": f"demo_{agent_id}_{i + 1:03d}",
                        "agent_id": agent_id,
                        "demo_asset_type": asset.get("demo_asset_type", ""),
                        "demo_asset_name": asset.get("demo_asset_name", ""),
                        "demo_link": asset.get("demo_link", "")
                    })
                
                if demo_assets_data:
                    data_source.save_demo_assets_data(demo_assets_data)
            except json.JSONDecodeError:
                pass  # Skip if invalid JSON
        
        # Save documentation
        docs_data = {
            "doc_id": f"doc_{agent_id}",
            "agent_id": agent_id,
            "sdk_details": sdk_details,
            "swagger_details": swagger_details,
            "sample_input": sample_input,
            "sample_output": sample_output,
            "security_details": security_details,
            "related_files": related_files
        }
        
        data_source.save_docs_data(docs_data)
        
        # Process deployments
        if deployments:
            try:
                import json
                deployments_list = json.loads(deployments) if deployments else []
                deployments_data = []
                
                for i, deployment in enumerate(deployments_list):
                    deployments_data.append({
                        "deployment_id": f"deploy_{agent_id}_{i + 1:03d}",
                        "service_provider": deployment.get("service_provider", ""),
                        "service_name": deployment.get("service_name", ""),
                        "deployment": deployment.get("deployment", ""),
                        "cloud_region": deployment.get("cloud_region", ""),
                        "by_capability": deployment.get("by_capability", "")
                    })
                
                if deployments_data:
                    data_source.save_deployments_data(deployments_data)
            except json.JSONDecodeError:
                pass  # Skip if invalid JSON
        
        return {
            "success": True,
            "message": "Agent created successfully! Pending admin approval.",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "redirect": f"/agent/{agent_name.lower().replace(' ', '-')}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating agent: {str(e)}")

# ============================================================================
# ADMIN AGENT ENDPOINTS
# ============================================================================

@app.get("/api/admin/agents")
async def get_all_agents_admin():
    """Admin: Get all agents with approval status"""
    try:
        agents_df = data_source.get_agents()
        agents_list = agents_df.to_dict('records')
        
        # Replace NaN values and add approval status
        for agent in agents_list:
            for key, value in agent.items():
                if pd.isna(value):
                    agent[key] = "na"
            
            # Add approval status
            agent['is_approved'] = agent.get('admin_approved', 'no') == 'yes'
        
        return {"agents": agents_list, "total": len(agents_list)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching agents: {str(e)}")

@app.put("/api/admin/agents/{agent_id}")
async def admin_update_agent_approval(
    agent_id: str,
    admin_approved: str = Form("no")
):
    """Admin: Update agent approval status"""
    try:
        # Update the agent's approval status in the CSV file
        update_data = {
            "admin_approved": admin_approved
        }
        
        success = data_source.update_agent_data(agent_id, update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update agent approval status")
        
        return {
            "success": True,
            "message": f"Agent {'approved' if admin_approved == 'yes' else 'rejected'} successfully",
            "agent_id": agent_id,
            "admin_approved": admin_approved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating agent approval: {str(e)}")

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

# ============================================================================
# ISV FRONTEND PAGES
# ============================================================================

@app.get("/isv/login", response_class=HTMLResponse)
async def isv_login_page():
    """Serve the ISV login page"""
    try:
        with open("../frontend/isv_login.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="ISV login page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading ISV login page: {str(e)}")

@app.get("/isv/signup", response_class=HTMLResponse)
async def isv_signup_page():
    """Serve the ISV signup page"""
    try:
        with open("../frontend/isv_signup.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="ISV signup page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading ISV signup page: {str(e)}")

@app.get("/isv/profile/{isv_id}", response_class=HTMLResponse)
async def isv_profile_page(isv_id: str):
    """Serve the ISV profile page"""
    try:
        with open("../frontend/isv_profile.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace placeholder with actual ISV ID
        html_content = html_content.replace("{{isv_id}}", isv_id)
        
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="ISV profile page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading ISV profile page: {str(e)}")

# ============================================================================
# ADMIN FRONTEND PAGES
# ============================================================================

@app.get("/admin/isv", response_class=HTMLResponse)
async def admin_isv_page():
    """Serve the admin ISV management page"""
    try:
        with open("../frontend/admin_isv.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin ISV page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading admin ISV page: {str(e)}")

# ============================================================================
# RESELLER HTML PAGES
# ============================================================================

@app.get("/reseller/login", response_class=HTMLResponse)
async def reseller_login_page():
    """Reseller login page"""
    try:
        with open("../frontend/reseller_login.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Reseller login page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading reseller login page: {str(e)}")

@app.get("/reseller/signup", response_class=HTMLResponse)
async def reseller_signup_page():
    """Reseller signup page"""
    try:
        with open("../frontend/reseller_signup.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Reseller signup page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading reseller signup page: {str(e)}")

@app.get("/reseller/profile/{reseller_id}", response_class=HTMLResponse)
async def reseller_profile_page(reseller_id: str):
    """Reseller profile page"""
    try:
        with open("../frontend/reseller_profile.html", "r", encoding="utf-8") as f:
            html_content = f.read().replace("{{reseller_id}}", reseller_id)
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Reseller profile page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading reseller profile page: {str(e)}")

@app.get("/admin/reseller", response_class=HTMLResponse)
async def admin_reseller_page():
    """Admin reseller management page"""
    try:
        with open("../frontend/admin_reseller.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin reseller page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading admin reseller page: {str(e)}")

# ============================================================================
# AGENT ONBOARDING HTML PAGES
# ============================================================================

@app.get("/isv/profile/{isv_id}/onboard-agent", response_class=HTMLResponse)
async def agent_onboard_page(isv_id: str):
    """Agent onboarding page for ISV"""
    try:
        with open("../frontend/agent_onboard.html", "r", encoding="utf-8") as f:
            html_content = f.read().replace("{{isv_id}}", isv_id)
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent onboard page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading agent onboard page: {str(e)}")

@app.get("/admin/agents", response_class=HTMLResponse)
async def admin_agents_page():
    """Admin agent management page"""
    try:
        with open("../frontend/admin_agents.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin agents page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading admin agents page: {str(e)}")

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page():
    """Admin login page"""
    try:
        with open("../frontend/admin_login.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin login page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading admin login page: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_CONFIG["host"], port=API_CONFIG["port"])
