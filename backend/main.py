"""
FastAPI application for Agents Marketplace
"""
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import uuid
import logging
from datetime import datetime
from s3_utils import s3_manager

# Configure logging
logger = logging.getLogger(__name__)
from data_source import data_source
from config import API_CONFIG
from unified_chat import unified_chat_agent

# Request models for API documentation
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    mode: str = "explore"
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "I wanna build an agent for HR so that they can filter through applications easily",
                "session_id": "chat_1234567890_abc123",
                "mode": "create"
            }
        }

class ClearChatRequest(BaseModel):
    session_id: str
    mode: Optional[str] = "explore"
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "chat_1234567890_abc123",
                "mode": "create"
            }
        }

# Create FastAPI app
app = FastAPI(
    title=API_CONFIG["title"],
    version=API_CONFIG["version"],
    description=API_CONFIG["description"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods including OPTIONS
    allow_headers=["*"],
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

@app.get("/config")
async def get_config():
    """Get application configuration"""
    return {
        "app_name": "Agents Marketplace",
        "version": "1.0.0",
        "status": "running",
        "features": ["agents", "chat", "isv", "reseller", "client", "admin"]
    }

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
            "redirect": f"/isv/profile/{user['user_id']}" if user["role"] == "isv" else f"/reseller/profile/{user['user_id']}" if user["role"] == "reseller" else f"/client/profile/{user['user_id']}" if user["role"] == "client" else "/admin/isv"
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
    mou_file: UploadFile = File(None),
    # Reseller specific fields
    reseller_name: str = Form(""),
    reseller_address: str = Form(""),
    reseller_domain: str = Form(""),
    reseller_mob_no: str = Form(""),
    whitelisted_domain: str = Form(""),
    # Client specific fields
    client_name: str = Form(""),
    client_company: str = Form(""),
    client_mob_no: str = Form("")
):
    """Registration endpoint for ISV, Reseller, and Client"""
    try:
        # Check if email already exists
        existing_user = data_source.get_user_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate role
        if role not in ["isv", "reseller", "client"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'isv', 'reseller', or 'client'")
        
        # Generate new IDs following the existing pattern
        auth_id = data_source.get_next_auth_id()
        
        if role == "isv":
            # ISV registration
            if not isv_name:
                raise HTTPException(status_code=400, detail="Company name is required for ISV registration")
            
            user_id = data_source.get_next_isv_id()
            
            # Handle MOU file upload
            mou_file_path = ""
            if mou_file and mou_file.filename:
                try:
                    file_content = await mou_file.read()
                    success, message, s3_url = s3_manager.upload_file(
                        file_content, 
                        mou_file.filename, 
                        "mou", 
                        user_id
                    )
                    if success:
                        mou_file_path = s3_url
                        logger.info(f"MOU file uploaded successfully for ISV {user_id}: {s3_url}")
                    else:
                        logger.warning(f"MOU file upload failed for ISV {user_id}: {message}")
                except Exception as e:
                    logger.error(f"Error uploading MOU file for ISV {user_id}: {str(e)}")
            
            # Create ISV record
            isv_data = {
                "isv_id": user_id,
                "isv_name": isv_name,
                "isv_address": isv_address,
                "isv_domain": isv_domain,
                "isv_mob_no": isv_mob_no,
                "isv_email_no": email,
                "mou_file_path": mou_file_path,
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
        
        elif role == "client":
            # Generate client ID
            user_id = data_source.get_next_client_id()
            
            # Create client record (no admin approval needed)
            client_data = {
                "client_id": user_id,
                "client_name": client_name,
                "client_company": client_company,
                "client_mob_no": client_mob_no,
                "client_email_no": email
            }
            
            # Save client data
            data_saved = data_source.save_client_data(client_data)
            redirect_url = "/client/login"
        
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
# CLIENT APIs
# ============================================================================

@app.get("/api/client/profile/{client_id}")
async def get_client_profile(client_id: str):
    """Get client profile"""
    try:
        clients_df = data_source.get_clients()
        client = clients_df[clients_df['client_id'] == client_id]
        
        if client.empty:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client_data = client.iloc[0].to_dict()
        
        return {
            "success": True,
            "client": client_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching client profile: {str(e)}")

@app.put("/api/client/profile/{client_id}")
async def update_client_profile(
    client_id: str,
    client_name: str = Form(...),
    client_company: str = Form(...),
    client_mob_no: str = Form(...),
    client_email_no: str = Form(...)
):
    """Update client profile"""
    try:
        updated_data = {
            "client_name": client_name,
            "client_company": client_company,
            "client_mob_no": client_mob_no,
            "client_email_no": client_email_no
        }
        
        success = data_source.update_client_data(client_id, updated_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Client not found")
        
        return {
            "success": True,
            "message": "Client profile updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating client profile: {str(e)}")

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
        
        # Generate signed URL for MOU file if it exists
        if isv_data.get("mou_file_path") and isv_data["mou_file_path"] != "na":
            try:
                signed_url = s3_manager.generate_signed_url(isv_data["mou_file_path"])
                isv_data["mou_file_signed_url"] = signed_url
            except Exception as e:
                logger.error(f"Error generating signed URL for ISV {isv_id}: {str(e)}")
                # Keep the original URL if signing fails
                isv_data["mou_file_signed_url"] = isv_data["mou_file_path"]
        
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
    isv_email: str = Form(...),
    mou_file: UploadFile = File(None)
):
    """Update ISV profile"""
    try:
        # Handle MOU file upload if provided
        if mou_file and mou_file.filename:
            try:
                # Get existing ISV data to check for old MOU file
                existing_isv = data_source.get_isv_by_id(isv_id)
                old_mou_path = existing_isv.get("mou_file_path", "") if existing_isv else ""
                
                # Upload new MOU file
                file_content = await mou_file.read()
                success, message, s3_url = s3_manager.upload_file(
                    file_content, 
                    mou_file.filename, 
                    "mou", 
                    isv_id
                )
                if success:
                    # Delete old MOU file if it exists
                    if old_mou_path:
                        s3_manager.delete_file(old_mou_path)
                    
                    # Update with new MOU file path
                    update_data = {
                        "isv_name": isv_name,
                        "isv_address": isv_address,
                        "isv_domain": isv_domain,
                        "isv_mob_no": isv_mob_no,
                        "isv_email_no": isv_email,
                        "mou_file_path": s3_url
                    }
                    logger.info(f"MOU file updated successfully for ISV {isv_id}: {s3_url}")
                else:
                    logger.warning(f"MOU file upload failed for ISV {isv_id}: {message}")
                    # Continue with update without MOU file
                    update_data = {
                        "isv_name": isv_name,
                        "isv_address": isv_address,
                        "isv_domain": isv_domain,
                        "isv_mob_no": isv_mob_no,
                        "isv_email_no": isv_email
                    }
            except Exception as e:
                logger.error(f"Error uploading MOU file for ISV {isv_id}: {str(e)}")
                # Continue with update without MOU file
                update_data = {
                    "isv_name": isv_name,
                    "isv_address": isv_address,
                    "isv_domain": isv_domain,
                    "isv_mob_no": isv_mob_no,
                    "isv_email_no": isv_email
                }
        else:
            # No MOU file provided, update other fields only
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
    deployments: str = Form(""),
    
    # Demo asset files (multiple files)
    demo_files: List[UploadFile] = File([]),
    
    # README file upload
    readme_file: UploadFile = File(None)
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
            
            # Get existing capabilities to find next available ID
            existing_capabilities_df = data_source.get_capabilities_mapping()
            existing_capability_ids = set()
            if not existing_capabilities_df.empty:
                existing_capability_ids = set(existing_capabilities_df['by_capability_id'].dropna().tolist())
            
            # Find next available capability ID
            next_cap_id = 1
            while f"capa_{next_cap_id:03d}" in existing_capability_ids:
                next_cap_id += 1
            
            for i, capability in enumerate(capabilities_list):
                capabilities_data.append({
                    "agent_id": agent_id,
                    "by_capability_id": f"capa_{next_cap_id + i:03d}",  # Generate unique capability ID
                    "by_capability": capability
                })
        
        if capabilities_data:
            data_source.save_capabilities_mapping_data(capabilities_data)
        
        # Process demo assets: handle both single links and bulk file uploads
        demo_assets_data = []
        
        # Handle single demo links from form data
        if demo_link and demo_link.strip():
            demo_assets_data.append({
                "demo_asset_id": f"demo_{agent_id}_001",
                "agent_id": agent_id,
                "demo_asset_type": "External Link",
                "demo_asset_name": "Demo Link",
                "demo_link": demo_link.strip()
            })
            logger.info(f"Added single demo link for agent {agent_id}: {demo_link}")
        
        # Handle bulk file uploads
        if demo_files:
            logger.info(f"Processing {len(demo_files)} demo files for bulk upload")
            file_counter = len(demo_assets_data) + 1  # Start counter after single links
            
            for file in demo_files:
                if file.filename:  # Only process files with names
                    try:
                        logger.info(f"Processing bulk file: {file.filename}")
                        file_content = await file.read()
                        logger.info(f"File content size: {len(file_content)} bytes")
                        
                        success, message, s3_url = s3_manager.upload_file(
                            file_content, 
                            file.filename, 
                            "demo_assets", 
                            agent_id
                        )
                        
                        if success:
                            demo_assets_data.append({
                                "demo_asset_id": f"demo_{agent_id}_{file_counter:03d}",
                                "agent_id": agent_id,
                                "demo_asset_type": "Uploaded File",
                                "demo_asset_name": file.filename,
                                "demo_link": s3_url  # Save S3 URL in demo_link field
                            })
                            logger.info(f"Bulk file uploaded successfully for agent {agent_id}: {s3_url}")
                            file_counter += 1
                        else:
                            logger.warning(f"Bulk file upload failed for agent {agent_id}: {message}")
                            
                    except Exception as e:
                        logger.error(f"Error uploading bulk file {file.filename} for agent {agent_id}: {str(e)}")
        
        # Handle legacy demo_assets JSON (for backward compatibility)
        if demo_assets:
            try:
                import json
                demo_assets_list = json.loads(demo_assets) if demo_assets else []
                
                for asset in demo_assets_list:
                    # Only process if it's a valid asset with a link
                    if asset.get("demo_link") and asset["demo_link"].strip():
                        demo_assets_data.append({
                            "demo_asset_id": f"demo_{agent_id}_{len(demo_assets_data) + 1:03d}",
                            "agent_id": agent_id,
                            "demo_asset_type": asset.get("demo_asset_type", "External Link"),
                            "demo_asset_name": asset.get("demo_asset_name", "Demo Asset"),
                            "demo_link": asset["demo_link"].strip()
                        })
                        logger.info(f"Added legacy demo asset for agent {agent_id}: {asset['demo_link']}")
            except json.JSONDecodeError:
                pass  # Skip if invalid JSON
        
        # Save all demo assets
        if demo_assets_data:
            data_source.save_demo_assets_data(demo_assets_data)
            logger.info(f"Saved {len(demo_assets_data)} demo assets for agent {agent_id}")
        
        # Handle README file upload
        readme_file_url = ""
        if readme_file and readme_file.filename:
            try:
                logger.info(f"Processing README file upload: {readme_file.filename}")
                file_content = await readme_file.read()
                logger.info(f"README file content size: {len(file_content)} bytes")
                
                success, message, s3_url = s3_manager.upload_file(
                    file_content, 
                    readme_file.filename, 
                    "agent_docs", 
                    agent_id
                )
                
                if success:
                    readme_file_url = s3_url
                    logger.info(f"README file uploaded successfully for agent {agent_id}: {s3_url}")
                else:
                    logger.warning(f"README file upload failed for agent {agent_id}: {message}")
                    
            except Exception as e:
                logger.error(f"Error uploading README file {readme_file.filename} for agent {agent_id}: {str(e)}")
        
        # Combine related_files with README file URL
        related_files_combined = related_files
        if readme_file_url:
            if related_files_combined:
                related_files_combined += f", {readme_file_url}"
            else:
                related_files_combined = readme_file_url
        
        # Save documentation
        docs_data = {
            "doc_id": f"doc_{agent_id}",
            "agent_id": agent_id,
            "sdk_details": sdk_details,
            "swagger_details": swagger_details,
            "sample_input": sample_input,
            "sample_output": sample_output,
            "security_details": security_details,
            "related_files": related_files_combined
        }
        
        data_source.save_docs_data(docs_data)
        
        # Process deployments
        if deployments:
            try:
                import json
                deployments_list = json.loads(deployments) if deployments else []
                deployments_data = []
                
                # Get agent's existing capabilities to link deployments properly
                agent_capabilities_df = data_source.get_capabilities_by_agent(agent_id)
                agent_capabilities = {}
                if not agent_capabilities_df.empty:
                    for _, cap in agent_capabilities_df.iterrows():
                        capability_name = cap.get('by_capability', '')
                        capability_id = cap.get('by_capability_id', '')
                        if capability_name and capability_id:
                            agent_capabilities[capability_name.lower()] = capability_id
                
                logger.info(f"Agent {agent_id} capabilities: {agent_capabilities}")
                
                for i, deployment in enumerate(deployments_list):
                    # Try to match deployment capability with agent's existing capabilities
                    deployment_capability = deployment.get("by_capability", "").lower()
                    matched_capability_id = agent_capabilities.get(deployment_capability, "")
                    
                    if not matched_capability_id:
                        # If no exact match, try to find a similar capability
                        for cap_name, cap_id in agent_capabilities.items():
                            if deployment_capability in cap_name or cap_name in deployment_capability:
                                matched_capability_id = cap_id
                                logger.info(f"Matched '{deployment_capability}' with '{cap_name}' -> {cap_id}")
                                break
                    
                    if not matched_capability_id:
                        logger.warning(f"No matching capability found for '{deployment.get('by_capability', '')}' in agent {agent_id}")
                        # Skip this deployment if no matching capability found
                        continue
                    
                    deployments_data.append({
                        "by_capability_id": matched_capability_id,  # Foreign key to capabilities
                        "service_id": f"serv_{agent_id}_{i + 1:03d}",  # Generate service ID
                        "by_capability": deployment.get("by_capability", ""),
                        "service_provider": deployment.get("service_provider", ""),
                        "service_name": deployment.get("service_name", ""),
                        "deployment": deployment.get("deployment", ""),
                        "cloud_region": deployment.get("cloud_region", "")
                    })
                
                if deployments_data:
                    data_source.save_deployments_data(deployments_data)
                    logger.info(f"Saved {len(deployments_data)} deployments for agent {agent_id}")
                else:
                    logger.warning(f"No valid deployments to save for agent {agent_id}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in deployments data: {e}")
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
    """Get all agents with basic info including by_capability, service_provider, and demo_preview"""
    try:
        agents_df = data_source.get_agents()
        capabilities_mapping_df = data_source.get_capabilities_mapping()
        deployments_df = data_source.get_deployments()
        demo_assets_df = data_source.get_demo_assets()
        
        # Get unique capabilities and service providers for each agent
        agent_capabilities = {}
        agent_service_providers = {}
        agent_demo_previews = {}
        
        # First, map agent_id to capabilities through capabilities_mapping
        if not capabilities_mapping_df.empty:
            for _, mapping in capabilities_mapping_df.iterrows():
                agent_id = mapping.get('agent_id', '')
                by_capability = mapping.get('by_capability', '')
                by_capability_id = mapping.get('by_capability_id', '')
                
                if agent_id and by_capability:
                    if agent_id not in agent_capabilities:
                        agent_capabilities[agent_id] = set()
                    agent_capabilities[agent_id].add(by_capability)
        
        # Then, map capabilities to service providers through deployments
        if not deployments_df.empty:
            capability_service_providers = {}
            for _, deployment in deployments_df.iterrows():
                by_capability_id = deployment.get('by_capability_id', '')
                by_capability = deployment.get('by_capability', '')
                service_provider = deployment.get('service_provider', '')
                
                if by_capability_id and service_provider:
                    if by_capability_id not in capability_service_providers:
                        capability_service_providers[by_capability_id] = set()
                    capability_service_providers[by_capability_id].add(service_provider)
        
        # Get demo previews from demo_assets table
        if not demo_assets_df.empty:
            for _, demo_asset in demo_assets_df.iterrows():
                agent_id = str(demo_asset.get('agent_id', ''))
                demo_link = str(demo_asset.get('demo_link', ''))
                demo_asset_name = str(demo_asset.get('demo_asset_name', ''))
                demo_file_path = str(demo_asset.get('demo_file_path', ''))
                
                if agent_id and agent_id != 'nan':
                    if agent_id not in agent_demo_previews:
                        agent_demo_previews[agent_id] = set()
                    
                    # Use demo_link as the preview, or demo_asset_name if available
                    preview_text = demo_link if demo_link != 'nan' and demo_link else demo_asset_name
                    if preview_text and preview_text != 'nan':
                        agent_demo_previews[agent_id].add(preview_text)
                    
                    # Check if demo_link contains an S3 URL (file-based demo asset)
                    if demo_link and demo_link != 'nan' and 's3.amazonaws.com' in demo_link:
                        try:
                            signed_url = s3_manager.generate_signed_url(demo_link)
                            agent_demo_previews[agent_id].add(signed_url)
                        except Exception as e:
                            logger.error(f"Error generating signed URL for demo asset {agent_id}: {str(e)}")
                            # Fallback to original URL
                            agent_demo_previews[agent_id].add(demo_link)
        
        # Map capabilities to service providers for each agent
        for agent_id, capabilities in agent_capabilities.items():
            for capability in capabilities:
                # Find capability_id for this capability
                capability_mapping = capabilities_mapping_df[
                    (capabilities_mapping_df['agent_id'] == agent_id) & 
                    (capabilities_mapping_df['by_capability'] == capability)
                ]
                
                if not capability_mapping.empty:
                    capability_id = capability_mapping.iloc[0].get('by_capability_id', '')
                    
                    # Get service providers for this capability
                    deployment_mapping = deployments_df[deployments_df['by_capability_id'] == capability_id]
                    if not deployment_mapping.empty:
                        if agent_id not in agent_service_providers:
                            agent_service_providers[agent_id] = set()
                        
                        for _, deployment in deployment_mapping.iterrows():
                            service_provider = deployment.get('service_provider', '')
                            if service_provider:
                                agent_service_providers[agent_id].add(service_provider)
        
        agents_list = agents_df.to_dict('records')
        
        # Add by_capability, service_provider, and demo_preview fields to each agent
        for agent in agents_list:
            agent_id = agent.get('agent_id', '')
            
            # Replace NaN values with "na" and remove demo_preview from original data
            for key, value in agent.items():
                if pd.isna(value):
                    agent[key] = "na"
            
            # Remove the original demo_preview field from agents table
            if 'demo_preview' in agent:
                del agent['demo_preview']
            
            # Add by_capability (comma-separated list)
            capabilities = agent_capabilities.get(agent_id, set())
            agent['by_capability'] = ', '.join(sorted(capabilities)) if capabilities else "na"
            
            # Add service_provider (comma-separated list)
            providers = agent_service_providers.get(agent_id, set())
            agent['service_provider'] = ', '.join(sorted(providers)) if providers else "na"
            
            # Add demo_preview from demo_assets (comma-separated list)
            demo_previews = agent_demo_previews.get(agent_id, set())
            agent['demo_preview'] = ', '.join(sorted(demo_previews)) if demo_previews else "na"
        
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
        
        # Add by_capability, service_provider, and demo_preview fields to agent
        agent_capabilities = set()
        agent_service_providers = set()
        agent_demo_previews = set()
        
        if capabilities:
            for cap in capabilities:
                capability_name = cap.get('by_capability', '')
                capability_id = cap.get('by_capability_id', '')
                
                if capability_name:
                    agent_capabilities.add(capability_name)
                
                # Get service providers for this capability
                if capability_id:
                    deployments = data_source.get_deployments_by_capability(capability_id)
                    if not deployments.empty:
                        for _, deployment in deployments.iterrows():
                            service_provider = deployment.get('service_provider', '')
                            if service_provider:
                                agent_service_providers.add(service_provider)
        
        
        # Remove the original demo_preview field from agents table
        if 'demo_preview' in agent:
            del agent['demo_preview']
        
        # Add the new fields to agent (demo_preview will be added after demo_assets are processed)
        agent['by_capability'] = ', '.join(sorted(agent_capabilities)) if agent_capabilities else "na"
        agent['service_provider'] = ', '.join(sorted(agent_service_providers)) if agent_service_providers else "na"
        
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
        
        # Get demo previews from demo_assets for this agent
        if demo_assets:
            for demo_asset in demo_assets:
                demo_link = str(demo_asset.get('demo_link', ''))
                demo_asset_name = str(demo_asset.get('demo_asset_name', ''))
                
                if demo_link and demo_link != 'nan':
                    agent_demo_previews.add(demo_link)
                elif demo_asset_name and demo_asset_name != 'nan':
                    agent_demo_previews.add(demo_asset_name)
        
        # Add demo_preview field to agent
        agent['demo_preview'] = ', '.join(sorted(agent_demo_previews)) if agent_demo_previews else "na"
        
        # Get documentation for this specific agent
        docs_df = data_source.get_docs_by_agent(agent_id)
        docs = docs_df.to_dict('records') if not docs_df.empty else []
        
        # Replace NaN values in docs and generate signed URLs for S3 links
        for doc in docs:
            for key, value in doc.items():
                if pd.isna(value):
                    doc[key] = "na"
                elif key == 'related_files' and value and value != 'na':
                    # Check if related_files contains S3 URLs and generate signed URLs
                    related_files_list = [f.strip() for f in str(value).split(',') if f.strip()]
                    signed_files = []
                    for file_url in related_files_list:
                        if 's3.amazonaws.com' in file_url:
                            try:
                                signed_url = s3_manager.generate_signed_url(file_url)
                                signed_files.append(signed_url)
                                logger.info(f"Generated signed URL for README file: {file_url}")
                            except Exception as e:
                                logger.error(f"Error generating signed URL for README file {file_url}: {str(e)}")
                                signed_files.append(file_url)  # Fallback to original URL
                        else:
                            signed_files.append(file_url)  # Keep non-S3 URLs as-is
                    doc[key] = ', '.join(signed_files)
        
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
    """Get all unique capabilities with grouped deployment combinations"""
    try:
        # Get capabilities from capabilities_mapping
        mapping_df = data_source.get_capabilities_mapping()
        capabilities = mapping_df[['by_capability_id', 'by_capability']].drop_duplicates()
        capabilities_list = capabilities.to_dict('records')
        
        # Get deployments data for grouping
        deployments_df = data_source.get_deployments()
        
        # Group deployments by service_provider and by_capability
        grouped_deployments = {}
        
        for _, deployment in deployments_df.iterrows():
            service_provider = deployment.get('service_provider', '')
            by_capability = deployment.get('by_capability', '')
            service_name = deployment.get('service_name', '')
            deployment_type = deployment.get('deployment', '')
            cloud_region = deployment.get('cloud_region', '')
            
            # Skip if any key field is empty or NaN
            if pd.isna(service_provider) or pd.isna(by_capability) or service_provider == '' or by_capability == '':
                continue
                
            # Create group key
            group_key = f"{service_provider}_{by_capability}"
            
            if group_key not in grouped_deployments:
                grouped_deployments[group_key] = {
                    "service_provider": service_provider,
                    "by_capability": by_capability,
                    "services": [],
                    "deployments": set(),
                    "cloud_regions": set()
                }
            
            # Add service details
            service_info = {
                "service_name": service_name,
                "deployment": deployment_type,
                "cloud_region": cloud_region
            }
            
            # Check if this service combination already exists
            service_exists = False
            for existing_service in grouped_deployments[group_key]["services"]:
                if (existing_service["service_name"] == service_name and 
                    existing_service["deployment"] == deployment_type):
                    service_exists = True
                    break
            
            if not service_exists:
                grouped_deployments[group_key]["services"].append(service_info)
            
            # Add to deployments and cloud_regions sets
            if deployment_type and deployment_type != 'na':
                grouped_deployments[group_key]["deployments"].add(deployment_type)
            
            if cloud_region and cloud_region != 'na':
                # Handle comma-separated regions
                regions = [r.strip() for r in str(cloud_region).split(',') if r.strip()]
                grouped_deployments[group_key]["cloud_regions"].update(regions)
        
        # Convert sets to sorted lists and prepare final response
        grouped_list = []
        for group_key, group_data in grouped_deployments.items():
            grouped_list.append({
                "service_provider": group_data["service_provider"],
                "by_capability": group_data["by_capability"],
                "services": group_data["services"],
                "deployments": sorted(list(group_data["deployments"])),
                "cloud_regions": sorted(list(group_data["cloud_regions"]))
            })
        
        # Sort by service_provider and by_capability
        grouped_list.sort(key=lambda x: (x["service_provider"], x["by_capability"]))
        
        # Replace NaN values in capabilities
        for cap in capabilities_list:
            for key, value in cap.items():
                if pd.isna(value):
                    cap[key] = "na"
        
        return {
            "capabilities": capabilities_list,
            "grouped_deployments": grouped_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching capabilities: {str(e)}")

@app.get("/api/values")
async def get_unique_values():
    """Get all unique values from categorical fields across all tables"""
    try:
        values = {}
        
        # Agents table categorical fields
        agents_df = data_source.get_agents()
        if not agents_df.empty:
            values["agents"] = {
                "by_persona": sorted([str(v) for v in agents_df['by_persona'].dropna().unique() if str(v) != 'nan']),
                "asset_type": sorted([str(v) for v in agents_df['asset_type'].dropna().unique() if str(v) != 'nan']),
                "by_value": sorted([str(v) for v in agents_df['by_value'].dropna().unique() if str(v) != 'nan'])
            }
        
        # Capabilities mapping categorical fields
        capabilities_df = data_source.get_capabilities_mapping()
        if not capabilities_df.empty:
            values["capabilities"] = {
                "by_capability": sorted([str(v) for v in capabilities_df['by_capability'].dropna().unique() if str(v) != 'nan'])
            }
        
        # Deployments table categorical fields
        deployments_df = data_source.get_deployments()
        if not deployments_df.empty:
            values["deployments"] = {
                "service_provider": sorted([str(v) for v in deployments_df['service_provider'].dropna().unique() if str(v) != 'nan']),
                "service_name": sorted([str(v) for v in deployments_df['service_name'].dropna().unique() if str(v) != 'nan']),
                "deployment": sorted([str(v) for v in deployments_df['deployment'].dropna().unique() if str(v) != 'nan'])
            }

        # Client table categorical fields
        client_df = data_source.get_clients()
        if not client_df.empty:
            # For client table, we might want to extract company names or other categorical data
            values["client"] = {
                "companies": sorted([str(v) for v in client_df['client_company'].dropna().unique() if str(v) != 'nan'])
            }
        
        # Auth table categorical fields
        auth_df = data_source.get_auth()
        if not auth_df.empty:
            values["auth"] = {
                "role": sorted([str(v) for v in auth_df['role'].dropna().unique() if str(v) != 'nan'])
            }
        
        # Agent requirements table categorical fields
        agent_requirements_df = data_source.get_agent_requirements()
        if not agent_requirements_df.empty:
            values["agent_requirements"] = {
                "applicable_industry": sorted([str(v) for v in agent_requirements_df['applicable_industry'].dropna().unique() if str(v) != 'nan'])
            }
        
        return {"values": values}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching unique values: {str(e)}")

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

# Unified Chat API endpoint
@app.post("/api/chat")
async def unified_chat(chat_request: ChatRequest):
    """Unified chat endpoint that handles both explore and create modes"""
    try:
        user_query = chat_request.query.strip()
        session_id = chat_request.session_id or ""
        mode = chat_request.mode
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Use unified chat agent
        response = unified_chat_agent.chat(user_query, mode, session_id)
        
        return {
            "success": True,
            "data": response,
            "mode": mode
        }
        
    except Exception as e:
        logger.error(f"Unified chat API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/chat/clear")
async def clear_chat_session(clear_request: ClearChatRequest):
    """Clear conversation history for a session"""
    try:
        session_id = clear_request.session_id
        mode = clear_request.mode
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        # Clear conversation using unified chat agent
        result = unified_chat_agent.clear_conversation(session_id)
        
        return {
            "success": True,
            "data": result,
            "mode": mode
        }
        
    except Exception as e:
        logger.error(f"Clear chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Clear chat error: {str(e)}")

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

@app.get("/chat", response_class=HTMLResponse)
async def simple_chat_page():
    """Simple AI Agent Chat page"""
    try:
        with open("../frontend/simple_chat.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading chat page: {str(e)}")

# ============================================================================
# CLIENT HTML PAGES
# ============================================================================

@app.get("/client/login", response_class=HTMLResponse)
async def client_login_page():
    """Client login page"""
    try:
        with open("../frontend/client_login.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Client login page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading client login page: {str(e)}")

@app.get("/client/signup", response_class=HTMLResponse)
async def client_signup_page():
    """Client signup page"""
    try:
        with open("../frontend/client_signup.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Client signup page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading client signup page: {str(e)}")

@app.get("/client/profile/{client_id}", response_class=HTMLResponse)
async def client_profile_page(client_id: str):
    """Client profile page"""
    try:
        with open("../frontend/client_profile.html", "r", encoding="utf-8") as f:
            html_content = f.read().replace("{{client_id}}", client_id)
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Client profile page not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading client profile page: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_CONFIG["host"], port=API_CONFIG["port"])
