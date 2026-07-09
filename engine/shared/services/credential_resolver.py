import logging
from uuid import UUID
from typing import Optional
from sqlalchemy import select
from engine.shared.models.credential_model import Credential
from engine.shared.security.encryption import decrypt_value
from engine.shared.config.settings import get_settings

logger = logging.getLogger(__name__)

class CredentialResolver:
    @staticmethod
    async def get_embedding_credential(org_id: Optional[UUID], db=None) -> dict:
        """
        Retrieves the first API key credential (ordered by created_at ASC) for the org.
        This determines the embedding provider and API key.
        Returns: {
            "provider": "gemini" | "openai",
            "api_key": str,
            "model": str,
            "dimensions": int,
            "credential_id": UUID or None
        }
        """
        if not org_id:
            logger.warning("[CredentialResolver] No organization_id provided, falling back to system default key.")
            return CredentialResolver._get_fallback_embedding_config()

        # Helper to query the DB
        async def _query_db(session):
            stmt = select(Credential).where(
                Credential.organization_id == org_id,
                Credential.provider.in_(["Google API Key", "OpenAI API Key"]),
                Credential.status == "Active"
            ).order_by(Credential.created_at.asc())
            res = await session.execute(stmt)
            return res.scalars().first()

        cred = None
        if db is not None:
            cred = await _query_db(db)
        else:
            from engine.shared.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                cred = await _query_db(session)

        if cred:
            try:
                encrypted_key = cred.auth_data.get("api_key") or ""
                decrypted_key = decrypt_value(encrypted_key)
                
                if not decrypted_key:
                    raise ValueError("Decrypted API key is empty")

                if cred.provider == "Google API Key":
                    provider = "gemini"
                    model = "gemini-embedding-2"
                else:
                    provider = "openai"
                    model = "text-embedding-3-small"
                    
                logger.info(
                    f"[CredentialResolver] Resolved dynamic embedding key for Org: {org_id} "
                    f"using credential: {cred.name} (Provider: {provider}, Model: {model})"
                )
                return {
                    "provider": provider,
                    "api_key": decrypted_key,
                    "model": model,
                    "dimensions": 1536,
                    "credential_id": cred.id
                }
            except Exception as e:
                logger.error(
                    f"[CredentialResolver] Failed to decrypt dynamic embedding key for Org: {org_id}. "
                    f"Credential ID: {cred.id}. Error: {e}. Falling back to system defaults."
                )

        logger.warning(
            f"[CredentialResolver] Client API key is not configured for Org: {org_id}. "
            "Falling back to host system API key."
        )
        return CredentialResolver._get_fallback_embedding_config()

    @staticmethod
    def _get_fallback_embedding_config() -> dict:
        settings = get_settings()
        import os
        
        provider = (
            os.getenv("EMBEDDING_PROVIDER")
            or os.getenv("DEFAULT_EMBEDDING_PROVIDER")
            or getattr(settings, "embedding_provider", "")
            or getattr(settings, "default_embedding_provider", "")
            or "gemini"
        ).strip().lower()
        
        if provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY") or getattr(settings, "google_api_key", "")
            model = "gemini-embedding-2"
        else:
            api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "openai_api_key", "")
            model = "text-embedding-3-small"
            
        return {
            "provider": provider,
            "api_key": api_key,
            "model": model,
            "dimensions": 1536,
            "credential_id": None
        }

    @staticmethod
    async def get_llm_credential(org_id: Optional[UUID], provider: str, db=None) -> dict:
        """
        Retrieves the client's API key for LLM calls based on provider ('google' or 'openai').
        Returns: {
            "api_key": str,
            "credential_id": UUID or None
        }
        """
        if not org_id:
            logger.warning("[CredentialResolver] No organization_id provided for LLM key resolution, falling back to system defaults.")
            return CredentialResolver._get_fallback_llm_config(provider)

        cred_provider = "Google API Key" if provider.lower() in ["google", "gemini"] else "OpenAI API Key"
        
        async def _query_db(session):
            stmt = select(Credential).where(
                Credential.organization_id == org_id,
                Credential.provider == cred_provider,
                Credential.status == "Active"
            ).order_by(Credential.created_at.asc())
            res = await session.execute(stmt)
            return res.scalars().first()

        cred = None
        if db is not None:
            cred = await _query_db(db)
        else:
            from engine.shared.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                cred = await _query_db(session)

        if cred:
            try:
                encrypted_key = cred.auth_data.get("api_key") or ""
                decrypted_key = decrypt_value(encrypted_key)
                
                if not decrypted_key:
                    raise ValueError("Decrypted API key is empty")
                
                logger.info(
                    f"[CredentialResolver] Resolved dynamic LLM key for Org: {org_id} "
                    f"using credential: {cred.name} (Provider: {provider})"
                )
                return {
                    "api_key": decrypted_key,
                    "credential_id": cred.id
                }
            except Exception as e:
                logger.error(
                    f"[CredentialResolver] Failed to decrypt dynamic LLM key for Org: {org_id}. "
                    f"Credential ID: {cred.id}. Error: {e}. Falling back to system defaults."
                )

        logger.warning(
            f"[CredentialResolver] Client {provider.upper()} API key is not configured for Org: {org_id}. "
            "Falling back to host system API key."
        )
        return CredentialResolver._get_fallback_llm_config(provider)

    @staticmethod
    def _get_fallback_llm_config(provider: str) -> dict:
        settings = get_settings()
        import os
        
        p_lower = provider.lower()
        if p_lower in ["google", "gemini"]:
            api_key = os.getenv("GOOGLE_API_KEY") or getattr(settings, "google_api_key", "")
        elif p_lower == "openai":
            api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "openai_api_key", "")
        elif p_lower == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "anthropic_api_key", "")
        elif p_lower == "groq":
            api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "groq_api_key", "")
        else:
            api_key = ""
            
        return {
            "api_key": api_key,
            "credential_id": None
        }

    @staticmethod
    def get_llm_credential_sync(org_id: Optional[UUID], provider: str) -> dict:
        """
        Synchronous version of get_llm_credential. Used in synchronous LLM initialization.
        """
        if not org_id:
            logger.warning("[CredentialResolver] No organization_id provided for LLM key resolution, falling back to system defaults.")
            return CredentialResolver._get_fallback_llm_config(provider)

        cred_provider = "Google API Key" if provider.lower() in ["google", "gemini"] else "OpenAI API Key"
        
        from engine.shared.db.session import SessionLocal
        try:
            with SessionLocal() as session:
                stmt = select(Credential).where(
                    Credential.organization_id == org_id,
                    Credential.provider == cred_provider,
                    Credential.status == "Active"
                ).order_by(Credential.created_at.asc())
                cred = session.execute(stmt).scalars().first()

            if cred:
                encrypted_key = cred.auth_data.get("api_key") or ""
                decrypted_key = decrypt_value(encrypted_key)
                if decrypted_key:
                    logger.info(
                        f"[CredentialResolver] Resolved dynamic LLM key (sync) for Org: {org_id} "
                        f"using credential: {cred.name} (Provider: {provider})"
                    )
                    return {
                        "api_key": decrypted_key,
                        "credential_id": cred.id
                    }
        except Exception as e:
            logger.error(
                f"[CredentialResolver] Failed to resolve/decrypt dynamic LLM key (sync) for Org: {org_id}. Error: {e}"
            )

        logger.warning(
            f"[CredentialResolver] Client {provider.upper()} API key is not configured for Org: {org_id}. "
            "Falling back to host system API key."
        )
        return CredentialResolver._get_fallback_llm_config(provider)

    @staticmethod
    def get_embedding_credential_sync(org_id: Optional[UUID]) -> dict:
        """
        Synchronous version of get_embedding_credential.
        """
        if not org_id:
            return CredentialResolver._get_fallback_embedding_config()

        from engine.shared.db.session import SessionLocal
        try:
            with SessionLocal() as session:
                stmt = select(Credential).where(
                    Credential.organization_id == org_id,
                    Credential.provider.in_(["Google API Key", "OpenAI API Key"]),
                    Credential.status == "Active"
                ).order_by(Credential.created_at.asc())
                cred = session.execute(stmt).scalars().first()

            if cred:
                encrypted_key = cred.auth_data.get("api_key") or ""
                decrypted_key = decrypt_value(encrypted_key)
                if decrypted_key:
                    if cred.provider == "Google API Key":
                        provider = "gemini"
                        model = "gemini-embedding-2"
                    else:
                        provider = "openai"
                        model = "text-embedding-3-small"
                        
                    logger.info(
                        f"[CredentialResolver] Resolved dynamic embedding key (sync) for Org: {org_id} "
                        f"using credential: {cred.name} (Provider: {provider}, Model: {model})"
                    )
                    return {
                        "provider": provider,
                        "api_key": decrypted_key,
                        "model": model,
                        "dimensions": 1536,
                        "credential_id": cred.id
                    }
        except Exception as e:
            logger.error(
                f"[CredentialResolver] Failed to resolve/decrypt dynamic embedding key (sync) for Org: {org_id}. Error: {e}"
            )

        logger.warning(
            f"[CredentialResolver] Client API key is not configured for Org: {org_id}. "
            "Falling back to host system API key."
        )
        return CredentialResolver._get_fallback_embedding_config()

