import httpx
import asyncio
from app.db import SessionLocal
from sqlalchemy import text

async def test_ai_orchestrator():
    print("Testing AI Orchestrator E2E Flow via Internal HTTP...")
    
    # Extract real IDs from our fresh test DB
    async with SessionLocal() as db:
        res = await db.execute(text("SELECT id, org_id FROM projects LIMIT 1"))
        row = res.fetchone()
        if not row:
            print("No projects exist in DB yet. Please seed the DB or run a login flow first.")
            return
        project_id, org_id = row[0], row[1]
        
        # Check for user
        res_u = await db.execute(text(f"SELECT id FROM users WHERE org_id = '{org_id}' LIMIT 1"))
        row_u = res_u.fetchone()
        if not row_u:
            print("No users exist for org in DB yet.")
            return
        user_id = row_u[0]
        
        # Fetching auth token logic or just force unauthenticated endpoint internally
        # As it stands there's no easy bypass without auth tokens for external routes.
        # But we can call the service layer natively here because we have the genuine IDs!
        
        from app.ai_orchestrator.service import AIOrchestratorService
        from app.ai_orchestrator.schemas import CreateAIRunRequest
        from app.ai_orchestrator.models import TaskTypeEnum
        from app.deps import UserContext
        
        user = UserContext(
            user_id=user_id,
            org_id=org_id,
            email="test@audity.com",
            scopes=["admin"],
            session_id="mock",
            sub="mock",
            role="admin",
            iss="mock",
            exp=9999999999
        )
        
        request = CreateAIRunRequest(
            project_id=project_id,
            task_type=TaskTypeEnum.audit_fix,
            target_ref="main",
            repo_commit="abc123def456",
            instructions="Audita la capa de Auth."
        )
        
        service = AIOrchestratorService(db)
        run = await service.create_run(request, user)
        print(f"Created AI Run: {run.id}")
        print(f"Status: {run.status}")

if __name__ == "__main__":
    asyncio.run(test_ai_orchestrator())
