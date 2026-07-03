import asyncio
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.credential_model import Credential
from engine.shared.schemas.credential_schema import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialTestRequest,
    CredentialTestResponse,
    OAuthGenerateUrlRequest,
    OAuthGenerateUrlResponse,
    OAuthExchangeRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _auto_bind_and_sync(db: AsyncSession, credential: Credential, background_tasks: BackgroundTasks):
    from engine.shared.models.connector_model import Connector
    provider_lower = credential.provider.lower()
    
    # Find the connector for this organization and provider (Google maps to google_drive, others are 1:1)
    if provider_lower == "google":
        stmt = select(Connector).where(
            Connector.organization_id == credential.organization_id,
            Connector.connector_id == "google_drive"
        )
    else:
        stmt = select(Connector).where(
            Connector.organization_id == credential.organization_id,
            Connector.provider.ilike(credential.provider)
        )
        
    conn_res = await db.execute(stmt)
    connector = conn_res.scalars().first()
    
    if connector:
        connector.credential_id = credential.id
        connector.status = "enabled"
        connector.sync_status = "syncing"
        await db.commit()
        
        if connector.connector_id == "google_drive":
            from engine.shared.workers.drive_sync_worker import _sync_drive_for_workspace
            
            async def run_drive_sync_bg():
                from engine.shared.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    conn_res2 = await session.execute(select(Connector).where(Connector.id == connector.id))
                    fresh_conn = conn_res2.scalars().first()
                    cred_res2 = await session.execute(select(Credential).where(Credential.id == credential.id))
                    fresh_cred = cred_res2.scalars().first()
                    if fresh_conn and fresh_cred:
                        await _sync_drive_for_workspace(session, fresh_conn, fresh_cred)
                        
            background_tasks.add_task(run_drive_sync_bg)
        else:
            from engine.modules.database_connector.tasks import schedule_sync_schema
            schedule_sync_schema(connector.id, connector.organization_id, background_tasks=background_tasks)


async def _attach_sync_status(db: AsyncSession, credential: Credential):
    from engine.shared.models.connector_model import Connector
    conn_res = await db.execute(select(Connector).where(Connector.credential_id == credential.id))
    connector = conn_res.scalars().first()
    if connector:
        credential.sync_status = connector.sync_status
    else:
        credential.sync_status = None




async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/test", response_model=CredentialTestResponse)
async def test_credential(test_req: CredentialTestRequest):
    try:
        if test_req.provider == "Google":
            from engine.shared.integrations.google_drive_client import GoogleDriveClient

            client = GoogleDriveClient(auth_data=test_req.auth_data)
            # Try to list 1 file to verify token works
            await asyncio.to_thread(client.list_files, page_size=1)
            return CredentialTestResponse(
                success=True, message="Connection to Google Drive successful!"
            )

        elif test_req.provider in ["PostgreSQL", "MySQL"]:
            auth_data = test_req.auth_data
            host = auth_data.get("host")
            port = auth_data.get("port")
            username = auth_data.get("username")
            password = auth_data.get("password")
            database = auth_data.get("database")

            if not all([host, port, username, password, database]):
                return CredentialTestResponse(
                    success=False, message="Missing required database configuration."
                )

            if test_req.provider == "PostgreSQL":
                db_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
            else:
                db_url = (
                    f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}"
                )

            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text

            try:
                engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return CredentialTestResponse(
                    success=True,
                    message=f"Connection to {test_req.provider} successful!",
                )
            except Exception as e:
                return CredentialTestResponse(
                    success=False, message=f"Failed to connect: {str(e)}"
                )

        else:
            return CredentialTestResponse(
                success=False,
                message=f"Provider '{test_req.provider}' is not supported for testing.",
            )

    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        return CredentialTestResponse(success=False, message=str(e))


import os
from google_auth_oauthlib.flow import Flow
import json

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@router.post("/oauth/google/generate-url", response_model=OAuthGenerateUrlResponse)
async def generate_google_oauth_url(
    req: OAuthGenerateUrlRequest, db: AsyncSession = Depends(get_db)
):
    try:
        # Create a pending credential
        new_cred = Credential(
            organization_id=req.organization_id,
            name=req.name,
            provider="Google",
            status="pending",
            auth_data={
                "client_id": req.client_id,
                "client_secret": req.client_secret,
                "redirect_uri": req.redirect_uri,
            },
        )
        db.add(new_cred)
        await db.commit()
        await db.refresh(new_cred)

        state = str(new_cred.id)

        client_config = {
            "web": {
                "client_id": req.client_id,
                "project_id": "enterpriseiq-ai",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": req.client_secret,
                "redirect_uris": [req.redirect_uri],
            }
        }

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
        flow.redirect_uri = req.redirect_uri

        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        # Save the PKCE code_verifier generated by the flow
        new_auth_data = dict(new_cred.auth_data)
        new_auth_data["code_verifier"] = flow.code_verifier
        new_cred.auth_data = new_auth_data

        await db.commit()

        return OAuthGenerateUrlResponse(auth_url=auth_url, state=state)

    except Exception as e:
        logger.error(f"Failed to generate Google OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/oauth/google/{credential_id}/regenerate-url", response_model=OAuthGenerateUrlResponse)
async def regenerate_google_oauth_url(credential_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Credential).where(Credential.id == credential_id))
        cred = result.scalars().first()
        
        if not cred or cred.status != "pending":
            raise HTTPException(status_code=400, detail="Credential is not pending")
            
        client_id = cred.auth_data.get("client_id")
        client_secret = cred.auth_data.get("client_secret")
        redirect_uri = cred.auth_data.get("redirect_uri")
        
        client_config = {
            "web": {
                "client_id": client_id,
                "project_id": "enterpriseiq-ai",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
        flow.redirect_uri = redirect_uri
        
        auth_url, _ = flow.authorization_url(
            state=str(cred.id),
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        
        # Save the new PKCE code_verifier generated by the flow
        new_auth_data = dict(cred.auth_data)
        new_auth_data["code_verifier"] = flow.code_verifier
        cred.auth_data = new_auth_data
        
        await db.commit()
        return OAuthGenerateUrlResponse(auth_url=auth_url, state=str(cred.id))

    except Exception as e:
        logger.error(f"Failed to regenerate Google OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/oauth/google/exchange", response_model=CredentialResponse)
async def exchange_google_oauth_code(
    req: OAuthExchangeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        credential_id = UUID(req.state)
        result = await db.execute(
            select(Credential).where(Credential.id == credential_id)
        )
        cred = result.scalars().first()

        if not cred or cred.status != "pending":
            raise HTTPException(status_code=404, detail="Pending credential not found")

        client_id = cred.auth_data.get("client_id")
        client_secret = cred.auth_data.get("client_secret")
        redirect_uri = cred.auth_data.get("redirect_uri")

        client_config = {
            "web": {
                "client_id": client_id,
                "project_id": "enterpriseiq-ai",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
            }
        }

        # Allow insecure transport for localhost redirects
        if redirect_uri and "localhost" in redirect_uri:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
        flow.redirect_uri = redirect_uri

        if "code_verifier" in cred.auth_data:
            flow.code_verifier = cred.auth_data["code_verifier"]

        await asyncio.to_thread(flow.fetch_token, code=req.code)
        credentials = flow.credentials

        # Fetch the user's email address from Google Drive
        user_email = None
        try:
            from googleapiclient.discovery import build
            service = build('drive', 'v3', credentials=credentials)
            about_info = await asyncio.to_thread(service.about().get(fields="user").execute)
            user_email = about_info.get("user", {}).get("emailAddress")
        except Exception as e:
            logger.warning(f"Could not fetch user email during Google OAuth: {e}")

        # Store all tokens in auth_data
        cred.auth_data = {
            "email": user_email,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "json_content": {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
            },
        }
        cred.status = "Active"

        await db.commit()
        await db.refresh(cred)

        # Auto-map active credentials to the organization's connector and start sync
        await _auto_bind_and_sync(db, cred, background_tasks)
        await _attach_sync_status(db, cred)

        return cred

    except Exception as e:
        logger.error(f"Failed to exchange Google OAuth code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CredentialResponse)
async def create_credential(
    cred_in: CredentialCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_cred = Credential(
            organization_id=cred_in.organization_id,
            name=cred_in.name,
            provider=cred_in.provider,
            status=cred_in.status,
            auth_data=cred_in.auth_data,
        )
        db.add(new_cred)
        await db.commit()
        await db.refresh(new_cred)

        # Auto-map to connector and start sync immediately!
        if new_cred.status == "Active":
            await _auto_bind_and_sync(db, new_cred, background_tasks)
        await _attach_sync_status(db, new_cred)

        return new_cred
    except Exception as e:
        logger.error(f"Failed to create credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to create credential")


@router.get("/organization/{organization_id}", response_model=List[CredentialResponse])
async def list_credentials_by_org(
    organization_id: UUID, db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Credential).where(Credential.organization_id == organization_id)
        )
        creds = result.scalars().all()
        for cred in creds:
            await _attach_sync_status(db, cred)
        return creds
    except Exception as e:
        logger.error(f"Failed to fetch credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credentials")


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(credential_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Credential).where(Credential.id == credential_id)
        )
        cred = result.scalars().first()
        if not cred:
            raise HTTPException(status_code=404, detail="Credential not found")

        await db.delete(cred)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete credential")
