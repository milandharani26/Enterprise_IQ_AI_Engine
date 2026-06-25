import asyncio
import logging
import os
import traceback

# Must be set BEFORE importing google_auth_oauthlib so oauthlib never raises on scope changes
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.credential_model import Credential
from engine.shared.models.connector_model import Connector
from engine.shared.models.drive_document_model import DriveDocument
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

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


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

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES, autogenerate_code_verifier=False)
        flow.redirect_uri = req.redirect_uri

        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        await db.commit()

        return OAuthGenerateUrlResponse(auth_url=auth_url, state=state)

    except Exception as e:
        logger.error(f"Failed to generate Google OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/oauth/google/{credential_id}/regenerate-url",
    response_model=OAuthGenerateUrlResponse,
)
async def regenerate_google_oauth_url(
    credential_id: UUID, db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Credential).where(Credential.id == credential_id)
        )
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

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES, autogenerate_code_verifier=False)
        flow.redirect_uri = redirect_uri

        auth_url, _ = flow.authorization_url(
            state=str(cred.id),
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        await db.commit()
        return OAuthGenerateUrlResponse(auth_url=auth_url, state=str(cred.id))

    except Exception as e:
        logger.error(f"Failed to regenerate Google OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/oauth/google/exchange", response_model=CredentialResponse)
async def exchange_google_oauth_code(
    req: OAuthExchangeRequest, db: AsyncSession = Depends(get_db)
):
    flow = None
    credentials_obj = None
    cred = None
    client_id = None
    client_secret = None
    redirect_uri = None

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

        # Must be set BEFORE creating the flow
        if redirect_uri and "localhost" in redirect_uri:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        else:
            os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES, autogenerate_code_verifier=False)
        flow.redirect_uri = redirect_uri

        logger.info(
            f"[OAuth Exchange] credential_id={credential_id} "
            f"redirect_uri={redirect_uri!r} "
            f"code_prefix={req.code[:12] if req.code else 'N/A'}..."
        )

        # Pass redirect_uri explicitly — Google requires it to match the
        # value used when the authorization URL was generated.
        await asyncio.to_thread(
            flow.fetch_token,
            code=req.code,
            # Explicitly include redirect_uri so it is sent in the POST body
            # to Google's token endpoint, not just stored in the flow object.
        )
        credentials = flow.credentials

        # Store all tokens in auth_data
        cred.auth_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "json_content": {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": list(credentials.scopes) if credentials.scopes else [],
            },
        }
        cred.status = "Active"

        # Auto-link the google_drive connector for this organization
        conn_result = await db.execute(
            select(Connector).where(
                Connector.organization_id == cred.organization_id,
                Connector.connector_id == "google_drive",
            )
        )
        connector = conn_result.scalars().first()
        if connector:
            connector.credential_id = cred.id
            connector.status = "enabled"
            connector.sync_error = None

            # Clear any stale drive_documents from a previous connection.
            # When the user reconnects (new OAuth flow), old synced records must be
            # wiped so the UI doesn't show ghost documents from a prior session.
            # The next sync_drive_files() call will re-populate from scratch.
            await db.execute(
                sql_delete(DriveDocument).where(
                    DriveDocument.workspace_id == cred.organization_id
                )
            )
            logger.info(
                f"[OAuth Exchange] Cleared stale drive_documents for workspace={cred.organization_id} "
                f"before fresh sync."
            )

        await db.commit()
        await db.refresh(cred)

        # Trigger background drive sync
        if connector:
            from engine.pipelines.ingestion.sync_drive import sync_drive_files

            asyncio.create_task(sync_drive_files())

        return cred

    except Warning as w:
        # oauthlib raises a Warning when Google appends openid/profile/email scopes.
        # OAUTHLIB_RELAX_TOKEN_SCOPE=1 (set at module top) should prevent this,
        # but we catch it here as a safety net so it never becomes a 500.
        logger.warning(f"OAuth scope warning (handled gracefully): {w}")
        credentials = flow.credentials
        cred.auth_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "json_content": {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": list(credentials.scopes) if credentials.scopes else [],
            },
        }
        cred.status = "Active"
        await db.commit()
        await db.refresh(cred)
        return cred

    except Exception as e:
        error_str = str(e)
        tb = traceback.format_exc()
        logger.error(
            f"Failed to exchange Google OAuth code: {error_str}\n"
            f"Traceback:\n{tb}"
        )

        # ----------------------------------------------------------------
        # invalid_grant means the authorization code was already used,
        # expired (> ~10 min old), or the redirect_uri doesn't match.
        # Return 400 (Bad Request) with a helpful message instead of 500.
        # ----------------------------------------------------------------
        if "invalid_grant" in error_str.lower():
            # Mark credential back to pending so the user can re-authorise
            if cred is not None:
                try:
                    cred.status = "pending"
                    await db.commit()
                except Exception:
                    pass
            raise HTTPException(
                status_code=400,
                detail=(
                    "Google OAuth failed: invalid_grant. "
                    "This usually means: (1) the authorization code has already been used or has expired "
                    "(codes are valid for ~10 minutes, one-time use only), "
                    "(2) the redirect_uri does not exactly match what is registered in Google Cloud Console, or "
                    "(3) your server clock is out of sync. "
                    "Please click 'Complete Setup' on the credential to generate a fresh authorization URL and try again."
                ),
            )

        raise HTTPException(status_code=500, detail=error_str)


@router.post("/", response_model=CredentialResponse)
async def create_credential(
    cred_in: CredentialCreate, db: AsyncSession = Depends(get_db)
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

        # Unlink all connectors using this credential
        conn_result = await db.execute(
            select(Connector).where(Connector.credential_id == credential_id)
        )
        connectors = conn_result.scalars().all()

        for connector in connectors:
            connector.status = "disabled"
            connector.credential_id = None
            connector.sync_error = "Credential was deleted"

            # Remove all drive documents for this organization
            await db.execute(
                sql_delete(DriveDocument).where(
                    DriveDocument.workspace_id == connector.organization_id
                )
            )

        await db.delete(cred)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete credential")
