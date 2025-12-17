# main.py

from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pymongo.database import Database
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os

load_dotenv()



MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://mukul:1010@nodecluster0.hurza.mongodb.net/?retryWrites=true&w=majority&appName=NodeCluster0")
DATABASE_NAME = os.getenv("DATABASE_NAME", "rfp_platform")

# Import Database stuff from database.py
from database import (
    async_db, get_db,
    users_collection, rfps_collection, qualification_rules_collection,
    product_prices_collection, test_prices_collection,
    notifications_collection, cron_jobs_collection,
    demo_centers_collection, demo_requests_collection
)
from models import User, RFP, QualificationRule, ProductPrice, TestPrice, Notification, CronJobConfig, DemoCenter, DemoRequest

# Import schemas (Ensure file is named schemas.py)
from schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    RFPCreate, RFPUpdate, RFPResponse, RFPList,
    QualificationRuleResponse, ProductPriceResponse, TestPriceResponse,
    DemoCenterResponse, DemoRequestCreate, DemoRequestResponse
)

from auth import authenticate_user, create_access_token, get_current_user
from ai_engine import orchestrator
from cron_scheduler import startup_event, shutdown_event

# ======================================================
# UTILITY FUNCTIONS
# ======================================================
async def send_notification(db: Database, user_id: str, rfp_id: str, message: str, notification_type: str = "ai_result"):
    """Send notification to user about AI results"""
    notification = Notification(
        user_id=user_id,
        rfp_id=rfp_id,
        message=message,
        type=notification_type
    )
    await db.notifications.insert_one(notification.dict(by_alias=True))

async def run_ai_on_pending_rfps(db: Database):
    """Run AI analysis on all pending RFPs"""
    pending_rfps = db.rfps.find({"agent_status": {"$in": ["idle", "pending"]}})
    count = 0
    async for rfp_doc in pending_rfps:
        rfp = RFP(**rfp_doc)
        try:
            # Update status
            await db.rfps.update_one({"_id": rfp.id}, {"$set": {"agent_status": "processing"}})

            # Run AI
            results = orchestrator.run_analysis({
                "title": rfp.title,
                "description": rfp.description,
                "budget": rfp.approximate_budget
            })

            # Update with results
            update_data = {
                "spec_match_score": results.get("spec_match_score", 0),
                "win_probability": results.get("win_probability", 0),
                "extracted_specs": results.get("extracted_specs", {}),
                "financial_analysis": results.get("financial_analysis", {}),
                "recommendation": results.get("recommendation", ""),
                "recommendation_reason": results.get("recommendation_reason", ""),
                "suggestions": results.get("suggestions", []),
                "agent_status": "completed"
            }
            await db.rfps.update_one({"_id": rfp.id}, {"$set": update_data})

            # Send notification
            await send_notification(db, rfp.user_id, str(rfp.id), f"AI analysis completed for RFP: {rfp.title}", "ai_result")
            count += 1

        except Exception as e:
            print(f"Error processing RFP {rfp.id}: {e}")
            await db.rfps.update_one({"_id": rfp.id}, {"$set": {"agent_status": "failed"}})

    return count

# ======================================================
# APP INIT
# ======================================================
# Create Tables
# Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    try:
        await async_db.command("ping")
        print("✅ Connected to MongoDB successfully")
        print(f"📊 Database: {DATABASE_NAME}")
        
        # Create unique index on email
        await async_db.users.create_index("email", unique=True)
        print("✅ Database indexes created")

        # Seed demo centers if none exist
        demo_count = await async_db.demo_centers.count_documents({})
        if demo_count == 0:
            from seed_data import demo_centers_seed
            for center_data in demo_centers_seed:
                await async_db.demo_centers.insert_one(center_data)
            print(f"✅ Seeded {len(demo_centers_seed)} demo centers")
        
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        print(f"MongoDB URL: {MONGODB_URL}")
        raise
    
    yield  # Application runs here
    
    # Shutdown (if needed)
    print("👋 Shutting down...")

app = FastAPI(
    title="RFP-Optimize AI API",
    lifespan=lifespan
)

@app.get("/health")
async def health_check(db: Database = Depends(get_db)):
    """Health check endpoint"""
    try:
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "message": "MongoDB is accessible"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
        
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add startup and shutdown events for cron scheduler
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# ======================================================
# GLOBAL ERROR HANDLER
# ======================================================
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     # Print error to terminal so you can see what happened
#     print(f"❌ Server Error: {exc}") 
#     return JSONResponse(
#         status_code=500,
#         content={"detail": str(exc)} # Send error details to frontend
#     )
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Print full error with traceback
    import traceback
    print(f"❌ Server Error on {request.url.path}")
    print(f"Error: {exc}")
    print("Full traceback:")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )
# ======================================================
# DEPENDENCIES
# ======================================================
async def get_current_user_dep(token: str = Depends(oauth2_scheme), db: Database = Depends(get_db)):
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user


async def require_client(user: User = Depends(get_current_user_dep)):
    if user.role != "client":
        raise HTTPException(status_code=403, detail="Client access required")
    return user


async def require_admin(user: User = Depends(get_current_user_dep)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
# ======================================================
# AUTH ROUTES
# ======================================================
@app.post("/register", response_model=UserResponse, status_code=201)
async def register(user: UserCreate, db: Database = Depends(get_db)):
    print(f"DEBUG: Registering user: {user.email}, role: {user.role}")
    
    try:
        # Check if user exists
        existing_user = await db.users.find_one({"email": user.email})
        if existing_user:
            print(f"DEBUG: User already exists: {user.email}")
            raise HTTPException(status_code=409, detail="Email already registered")

        # Create new user document for MongoDB
        user_doc = {
            "email": user.email,
            "password": user.password,
            "role": user.role,
            "created_at": datetime.utcnow()
        }
        
        # Insert into MongoDB
        result = await db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        print(f"DEBUG: User registered successfully: {user.email} with ID: {user_id}")
        
        # ✅ FIX: Return UserResponse with proper field mapping
        return UserResponse(
            _id=user_id,
            email=user.email,
            role=user.role,
            created_at=user_doc["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Registration error: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full stack trace
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
@app.get('/')
def hello_world():
    """Handles GET requests to the root URL."""
    return 'Hello, World! This is a GET request.'

@app.post("/login", response_model=Token)
async def login(data: UserLogin, db: Database = Depends(get_db)):
    print(f"DEBUG: Login attempt for: {data.email}")
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        print(f"DEBUG: Login failed for: {data.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(subject=user.email)
    print(f"DEBUG: Login successful for: {data.email}, token created")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    }
# ======================================================
# RFP ROUTES (CLIENT)
# ======================================================
@app.post("/rfps", response_model=RFPResponse)
async def create_rfp(rfp: RFPCreate, current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    db_rfp = RFP(**rfp.dict(), user_id=current_user.id)
    result = await db.rfps.insert_one(db_rfp.dict(by_alias=True))
    db_rfp.id = str(result.inserted_id)
    return db_rfp

@app.get("/rfps", response_model=RFPList)
async def list_rfps(current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    rfps_cursor = db.rfps.find({"user_id": current_user.id})
    rfps = []
    async for rfp_doc in rfps_cursor:
        rfps.append(RFP(**rfp_doc))
    return {"rfps": rfps}

@app.put("/rfps/{rfp_id}", response_model=RFPResponse)
async def update_rfp(rfp_id: str, rfp_update: RFPUpdate, current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    rfp_doc = await db.rfps.find_one({"_id": rfp_id, "user_id": current_user.id})
    if not rfp_doc:
        raise HTTPException(status_code=404, detail="RFP not found")

    update_data = rfp_update.dict(exclude_unset=True)
    await db.rfps.update_one({"_id": rfp_id}, {"$set": update_data})

    updated_doc = await db.rfps.find_one({"_id": rfp_id})
    return RFP(**updated_doc)

# ======================================================
# AI ANALYSIS
# ======================================================
@app.post("/rfps/{rfp_id}/analyze", response_model=RFPResponse)
async def analyze_rfp(rfp_id: str, current_user: User = Depends(get_current_user_dep), db: Database = Depends(get_db), background_tasks: BackgroundTasks = None):
    # Allow access if user owns the RFP (client) or is admin
    if current_user.role == "admin":
        rfp_doc = await db.rfps.find_one({"_id": rfp_id})
    else:
        rfp_doc = await db.rfps.find_one({"_id": rfp_id, "user_id": current_user.id})

    if not rfp_doc:
        raise HTTPException(status_code=404, detail="RFP not found")

    rfp = RFP(**rfp_doc)

    try:
        # Update status to processing
        await db.rfps.update_one({"_id": ObjectId(rfp_id)}, {"$set": {"agent_status": "processing"}})

        # Run AI
        results = orchestrator.run_analysis({
            "title": rfp.title,
            "description": rfp.description,
            "budget": rfp.approximate_budget
        })

        # Update DB
        update_data = {
            "spec_match_score": results.get("spec_match_score", 0),
            "win_probability": results.get("win_probability", 0),
            "extracted_specs": results.get("extracted_specs", {}),
            "financial_analysis": results.get("financial_analysis", {}),
            "recommendation": results.get("recommendation", ""),
            "recommendation_reason": results.get("recommendation_reason", ""),
            "suggestions": results.get("suggestions", []),
            "agent_status": "completed"
        }

        await db.rfps.update_one({"_id": ObjectId(rfp_id)}, {"$set": update_data})

        # Automatically create demo request for positive recommendations
        recommendation = results.get("recommendation", "")
        if recommendation.startswith("SELECT") or recommendation.startswith("CONSIDER"):
            try:
                # Get first available demo center
                center_doc = await db.demo_centers.find_one({"is_active": True})
                if center_doc:
                    center = DemoCenter(**center_doc)
                    preferred_location = center.name

                    # Create demo request
                    demo_req = DemoRequest(
                        rfp_id=rfp_id,
                        user_id=rfp.user_id,
                        preferred_location=preferred_location,
                        preferred_date=None,
                        special_requirements="Auto-generated from AI recommendation"
                    )
                    result = await db.demo_requests.insert_one(demo_req.dict(by_alias=True))
                    demo_req.id = str(result.inserted_id)

                    # Update RFP demo status
                    await db.rfps.update_one({"_id": ObjectId(rfp_id)}, {"$set": {"demo_status": "requested"}})

                    # Send demo notification
                    if background_tasks:
                        background_tasks.add_task(send_notification, db, rfp.user_id, rfp_id, f"Demo request auto-created for RFP: {rfp.title}", "demo_request")
            except Exception as e:
                print(f"Error creating auto demo request: {e}")

        # Send notification to user
        if background_tasks:
            background_tasks.add_task(send_notification, db, rfp.user_id, rfp_id, "AI analysis completed", "ai_result")

    except Exception as e:
        print(f"AI Error: {e}")
        # Use fallback values when AI fails
        fallback_data = {
            "spec_match_score": 50.0,
            "win_probability": 45.0,
            "extracted_specs": {
                "product_type": "Analysis Failed",
                "voltage_rating": "Analysis Failed",
                "material": "Analysis Failed",
                "durability_rating": "Analysis Failed",
                "compliance_standards": "Analysis Failed"
            },
            "financial_analysis": {
                "breakdown": {"material_cost": 0, "service_fees": 0, "applied_fees_list": []},
                "total_cost_internal": 0,
                "total_bid_value": 0,
                "margin": 20.0,
                "currency": "USD"
            },
            "recommendation": "REVIEW - Low confidence",
            "recommendation_reason": "AI analysis failed, using fallback values. Manual review recommended.",
            "suggestions": ["Re-run AI analysis when service is available", "Manually review RFP requirements against company capabilities"],
            "agent_status": "completed"  # Mark as completed with fallback data
        }
        await db.rfps.update_one({"_id": ObjectId(rfp_id)}, {"$set": fallback_data})

    updated_doc = await db.rfps.find_one({"_id": ObjectId(rfp_id)})
    return RFP(**updated_doc)

# ======================================================
# ADMIN ROUTES
# ======================================================
@app.get("/admin/rfps", response_model=RFPList)
async def admin_rfps(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    rfps_cursor = db.rfps.find({})
    rfps = []
    async for rfp_doc in rfps_cursor:
        rfps.append(RFP(**rfp_doc))
    return {"rfps": rfps}

@app.get("/admin/rules", response_model=List[QualificationRuleResponse])
async def admin_rules(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    rules_cursor = db.qualification_rules.find({})
    rules = []
    async for rule_doc in rules_cursor:
        if rule_doc.get("_id") is None:
            continue  # Skip invalid documents
        rules.append(QualificationRule(**rule_doc))
    return rules

@app.get("/admin/product-prices", response_model=List[ProductPriceResponse])
async def admin_product_prices(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    prices_cursor = db.product_prices.find({})
    prices = []
    async for price_doc in prices_cursor:
        prices.append(ProductPrice(**price_doc))
    return prices

@app.get("/admin/test-prices", response_model=List[TestPriceResponse])
async def admin_test_prices(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    prices_cursor = db.test_prices.find({})
    prices = []
    async for price_doc in prices_cursor:
        prices.append(TestPrice(**price_doc))
    return prices

# ======================================================
# NEW ADMIN FEATURES
# ======================================================

# Start AI Engine on all pending RFPs
@app.post("/admin/start-ai-engine")
async def start_ai_engine(current_user: User = Depends(require_admin), db: Database = Depends(get_db), background_tasks: BackgroundTasks = None):
    """Start AI analysis on all pending RFPs"""
    if background_tasks:
        background_tasks.add_task(run_ai_on_pending_rfps, db)
        return {"message": "AI engine started in background", "status": "processing"}

    # Run synchronously if no background tasks
    count = await run_ai_on_pending_rfps(db)
    return {"message": f"AI analysis completed on {count} RFPs", "processed_count": count}

# Manage Qualification Rules (Constraints)
@app.post("/admin/rules", response_model=QualificationRuleResponse)
async def create_qualification_rule(rule: QualificationRule, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    data = rule.dict(by_alias=True)
    if '_id' in data:
        del data['_id']
    result = await db.qualification_rules.insert_one(data)
    rule.id = str(result.inserted_id)
    return rule

@app.put("/admin/rules/{rule_id}", response_model=QualificationRuleResponse)
async def update_qualification_rule(rule_id: str, rule_update: QualificationRule, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    update_data = rule_update.dict(exclude_unset=True)
    await db.qualification_rules.update_one({"_id": ObjectId(rule_id)}, {"$set": update_data})
    updated_doc = await db.qualification_rules.find_one({"_id": ObjectId(rule_id)})
    return QualificationRule(**updated_doc)

@app.delete("/admin/rules/{rule_id}")
async def delete_qualification_rule(rule_id: str, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    await db.qualification_rules.delete_one({"_id": ObjectId(rule_id)})
    return {"message": "Rule deleted"}

# Manage Product Prices Repository
@app.post("/admin/product-prices", response_model=ProductPriceResponse)
async def create_product_price(price: ProductPrice, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    # Use sku_id as _id
    price_dict = price.dict(by_alias=True)
    await db.product_prices.insert_one(price_dict)
    return price

@app.put("/admin/product-prices/{sku_id}", response_model=ProductPriceResponse)
async def update_product_price(sku_id: str, price_update: ProductPrice, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    update_data = price_update.dict(exclude_unset=True)
    await db.product_prices.update_one({"_id": sku_id}, {"$set": update_data})
    updated_doc = await db.product_prices.find_one({"_id": sku_id})
    return ProductPrice(**updated_doc)

@app.delete("/admin/product-prices/{sku_id}")
async def delete_product_price(sku_id: str, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    await db.product_prices.delete_one({"_id": sku_id})
    return {"message": "Product price deleted"}

# Manage Test Prices Repository
@app.post("/admin/test-prices", response_model=TestPriceResponse)
async def create_test_price(price: TestPrice, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    price_dict = price.dict(by_alias=True)
    await db.test_prices.insert_one(price_dict)
    return price

@app.put("/admin/test-prices/{test_code}", response_model=TestPriceResponse)
async def update_test_price(test_code: str, price_update: TestPrice, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    update_data = price_update.dict(exclude_unset=True)
    await db.test_prices.update_one({"_id": test_code}, {"$set": update_data})
    updated_doc = await db.test_prices.find_one({"_id": test_code})
    return TestPrice(**updated_doc)

@app.delete("/admin/test-prices/{test_code}")
async def delete_test_price(test_code: str, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    await db.test_prices.delete_one({"_id": test_code})
    return {"message": "Test price deleted"}

# Cron Job Management
@app.get("/admin/cron-jobs")
async def get_cron_jobs(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    jobs_cursor = db.cron_jobs.find({})
    jobs = []
    async for job_doc in jobs_cursor:
        if job_doc.get("_id") is None:
            continue  # Skip invalid documents
        jobs.append(CronJobConfig(**job_doc))
    return jobs

@app.post("/admin/cron-jobs")
async def create_cron_job(job: CronJobConfig, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    data = job.dict(by_alias=True)
    if '_id' in data:
        del data['_id']
    result = await db.cron_jobs.insert_one(data)
    job.id = str(result.inserted_id)
    return job

@app.put("/admin/cron-jobs/{job_id}")
async def update_cron_job(job_id: str, job_update: CronJobConfig, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    update_data = job_update.dict(exclude_unset=True)
    await db.cron_jobs.update_one({"_id": ObjectId(job_id)}, {"$set": update_data})
    return {"message": "Cron job updated"}

# Notifications for users
@app.get("/notifications")
async def get_user_notifications(current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    notifications_cursor = db.notifications.find({"user_id": current_user.id}).sort("created_at", -1)
    notifications = []
    async for notif_doc in notifications_cursor:
        notifications.append(Notification(**notif_doc))
    return notifications

@app.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    await db.notifications.update_one(
        {"_id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    return {"message": "Notification marked as read"}

# ======================================================
# DEMO/SAMPLE ROUTES
# ======================================================

# Get available demo centers
@app.get("/demo-centers", response_model=List[DemoCenterResponse])
async def get_demo_centers(current_user: User = Depends(get_current_user_dep), db: Database = Depends(get_db)):
    centers_cursor = db.demo_centers.find({"is_active": True})
    centers = []
    async for center_doc in centers_cursor:
        # Convert ObjectId to string for Pydantic
        center_data = dict(center_doc)
        center_data["_id"] = str(center_data["_id"])
        centers.append(DemoCenter(**center_data))
    return centers

# Request demo for accepted RFP
@app.post("/rfps/{rfp_id}/request-demo", response_model=DemoRequestResponse)
async def request_demo(rfp_id: str, demo_request: DemoRequestCreate, current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    # Check if RFP exists and user has access
    if current_user.role == "admin":
        rfp_doc = await db.rfps.find_one({"_id": ObjectId(rfp_id)})
    else:
        rfp_doc = await db.rfps.find_one({"_id": ObjectId(rfp_id), "user_id": current_user.id})
    if not rfp_doc:
        raise HTTPException(status_code=404, detail="RFP not found")

    rfp = RFP(**rfp_doc)

    # Check if RFP is accepted
    if not rfp.recommendation.startswith("SELECT") and not rfp.recommendation.startswith("CONSIDER"):
        raise HTTPException(status_code=400, detail="Demo can only be requested for accepted RFPs")

    # Check if demo already requested
    existing_demo = await db.demo_requests.find_one({"rfp_id": rfp_id})
    if existing_demo:
        raise HTTPException(status_code=400, detail="Demo already requested for this RFP")

    # Create demo request
    demo_req = DemoRequest(
        rfp_id=rfp_id,
        user_id=current_user.id,
        **demo_request.dict()
    )
    result = await db.demo_requests.insert_one(demo_req.dict(by_alias=True))
    demo_req.id = str(result.inserted_id)

    # Update RFP demo status
    await db.rfps.update_one({"_id": ObjectId(rfp_id)}, {"$set": {"demo_status": "requested"}})

    # Send notification
    await send_notification(db, current_user.id, rfp_id, f"Demo request submitted for RFP: {rfp.title}", "demo_request")

    return demo_req


# Create a new demo request
@app.post("/demo-requests", response_model=DemoRequestResponse)
async def create_demo_request(demo_request: DemoRequestCreate, current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    """
    Create a new demo request.
    """
    demo_req = DemoRequest(
        user_id=current_user.id,
        rfp_id=None,  # This demo request is not tied to an RFP
        **demo_request.dict()
    )
    result = await db.demo_requests.insert_one(demo_req.dict(by_alias=True))
    demo_req.id = str(result.inserted_id)

    # Send notification
    await send_notification(db, current_user.id, None, "New demo request created", "demo_request")

    return demo_req

# Get demo requests for user
@app.get("/demo-requests", response_model=List[DemoRequestResponse])
async def get_demo_requests(current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    requests_cursor = db.demo_requests.find({"user_id": current_user.id}).sort("created_at", -1)
    requests = []
    async for req_doc in requests_cursor:
        req_data = dict(req_doc)
        req_data["_id"] = str(req_data["_id"])
        requests.append(DemoRequest(**req_data))
    return requests


# Update demo decision (accept/reject after demo)
@app.put("/demo-requests/{request_id}/decision")
async def update_demo_decision(request_id: str, final_decision: str, feedback: Optional[str] = None, current_user: User = Depends(require_client), db: Database = Depends(get_db)):
    if final_decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Decision must be 'accept' or 'reject'")

    # Update demo request
    update_data = {
        "final_decision": final_decision,
        "client_feedback": feedback,
        "status": "completed"
    }
    await db.demo_requests.update_one(
        {"_id": request_id, "user_id": current_user.id},
        {"$set": update_data}
    )

    # Update RFP demo status
    demo_req_doc = await db.demo_requests.find_one({"_id": request_id})
    if demo_req_doc:
        rfp_status = "accepted" if final_decision == "accept" else "rejected"
        await db.rfps.update_one(
            {"_id": demo_req_doc["rfp_id"]},
            {"$set": {"demo_status": rfp_status}}
        )

    return {"message": f"Demo {final_decision}ed successfully"}

# ======================================================
# ADMIN DEMO MANAGEMENT
# ======================================================

# Get all demo requests (admin)
@app.get("/admin/demo-requests", response_model=List[DemoRequestResponse])
async def admin_get_demo_requests(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    requests_cursor = db.demo_requests.find({}).sort("created_at", -1)
    requests = []
    async for req_doc in requests_cursor:
        req_data = dict(req_doc)
        req_data["_id"] = str(req_data["_id"])
        requests.append(DemoRequest(**req_data))
    return requests

# Schedule demo
@app.put("/admin/demo-requests/{request_id}/schedule")
async def schedule_demo(request_id: str, center_id: str, scheduled_datetime: datetime, admin_notes: Optional[str] = None, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    # Check if center exists and has availability
    center_doc = await db.demo_centers.find_one({"_id": center_id, "is_active": True})
    if not center_doc:
        raise HTTPException(status_code=404, detail="Demo center not found")

    center = DemoCenter(**center_doc)
    slot_str = scheduled_datetime.strftime("%Y-%m-%d %H:%M")
    if slot_str not in center.available_slots:
        raise HTTPException(status_code=400, detail="Selected time slot not available")

    # Update demo request
    update_data = {
        "status": "scheduled",
        "scheduled_center_id": center_id,
        "scheduled_datetime": scheduled_datetime,
        "admin_notes": admin_notes
    }
    await db.demo_requests.update_one({"_id": request_id}, {"$set": update_data})

    # Update RFP status
    demo_req_doc = await db.demo_requests.find_one({"_id": request_id})
    if demo_req_doc:
        await db.rfps.update_one(
            {"_id": demo_req_doc["rfp_id"]},
            {"$set": {"demo_status": "scheduled"}}
        )

    # Send notification to client
    await send_notification(db, demo_req_doc["user_id"], demo_req_doc["rfp_id"],
                          f"Demo scheduled at {center.name} on {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}", "demo_scheduled")

    return {"message": "Demo scheduled successfully"}

# Manage demo centers (admin)
@app.get("/admin/demo-centers", response_model=List[DemoCenterResponse])
async def admin_get_demo_centers(current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    centers_cursor = db.demo_centers.find({})
    centers = []
    async for center_doc in centers_cursor:
        center_data = dict(center_doc)
        center_data["_id"] = str(center_data["_id"])
        centers.append(DemoCenter(**center_data))
    return centers

@app.post("/admin/demo-centers", response_model=DemoCenterResponse)
async def create_demo_center(center: DemoCenter, current_user: User = Depends(require_admin), db: Database = Depends(get_db)):
    data = center.dict(by_alias=True)
    if '_id' in data:
        del data['_id']
    result = await db.demo_centers.insert_one(data)
    center.id = str(result.inserted_id)
    return center