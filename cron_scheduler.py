import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from database import get_sync_db, async_db
from ai_engine import orchestrator
from models import Notification, DemoRequest
import os

class CronScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db = async_db

    async def run_ai_on_pending_rfps_job(self):
        """Job to run AI analysis on pending RFPs"""
        print(f"[{datetime.now()}] Running scheduled AI analysis job")

        try:
            # Get pending RFPs
            pending_rfps = self.db.rfps.find({"agent_status": {"$in": ["idle", "pending"]}})
            count = 0

            async for rfp_doc in pending_rfps:
                try:
                    # Run AI analysis
                    results = orchestrator.run_analysis({
                        "title": rfp_doc.get("title", ""),
                        "description": rfp_doc.get("description", ""),
                        "budget": rfp_doc.get("approximate_budget", 0)
                    })

                    # Update RFP with results
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

                    await self.db.rfps.update_one({"_id": rfp_doc["_id"]}, {"$set": update_data})

                    # Send notification to user
                    await self.send_notification(
                        rfp_doc["user_id"],
                        str(rfp_doc["_id"]),
                        f"AI analysis completed for RFP: {rfp_doc.get('title', 'Unknown')}",
                        "ai_result"
                    )

                    count += 1
                    print(f"Processed RFP: {rfp_doc.get('title', 'Unknown')}")

                except Exception as e:
                    print(f"Error processing RFP {rfp_doc.get('_id')}: {e}")
                    await self.db.rfps.update_one({"_id": rfp_doc["_id"]}, {"$set": {"agent_status": "failed"}})

            print(f"[{datetime.now()}] Completed scheduled AI analysis: {count} RFPs processed")

        except Exception as e:
            print(f"Error in scheduled AI job: {e}")

    async def send_notification(self, user_id: str, rfp_id: str, message: str, notification_type: str = "ai_result"):
        """Send notification to user"""
        notification = Notification(
            user_id=user_id,
            rfp_id=rfp_id,
            message=message,
            type=notification_type
        )
        await self.db.notifications.insert_one(notification.dict(by_alias=True))

    async def check_and_run_jobs(self):
        """Check enabled cron jobs and run them if conditions are met"""
        try:
            cron_jobs = self.db.cron_jobs.find({"enabled": True})

            async for job_doc in cron_jobs:
                job = job_doc
                job_id = str(job["_id"])

                # Check if job should run based on type
                should_run = False

                if job["schedule_type"] == "interval":
                    # Check time-based interval
                    last_run = job.get("last_run")
                    interval_minutes = job.get("interval_minutes", 60)

                    if not last_run:
                        should_run = True
                    else:
                        time_diff = (datetime.now() - last_run).total_seconds() / 60
                        if time_diff >= interval_minutes:
                            should_run = True

                elif job["schedule_type"] == "count_based":
                    # Check pending RFP count
                    min_pending = job.get("min_pending_rfps", 5)
                    pending_count = await self.db.rfps.count_documents({"agent_status": {"$in": ["idle", "pending"]}})
                    if pending_count >= min_pending:
                        should_run = True

                if should_run:
                    print(f"[{datetime.now()}] Running cron job: {job['name']}")
                    await self.run_ai_on_pending_rfps_job()
                    
                    await self.db.cron_jobs.update_one(
                        {"_id": job["_id"]},
                        {"$set": {"last_run": datetime.now()}}
                    )

        except Exception as e:
            print(f"Error checking cron jobs: {e}")

    def start_scheduler(self):
        """Start the APScheduler"""
        # Add interval job to check for cron jobs every 5 minutes
        self.scheduler.add_job(
            self.check_and_run_jobs,
            trigger=IntervalTrigger(minutes=5),
            id="cron_checker",
            name="Cron Job Checker",
            replace_existing=True
        )

        self.scheduler.start()
        print("Cron scheduler started")

    async def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Cron scheduler stopped")

# Global scheduler instance
scheduler = CronScheduler()

async def startup_event():
    """Called when FastAPI app starts"""
    scheduler.start_scheduler()

async def shutdown_event():
    """Called when FastAPI app shuts down"""
    await scheduler.stop_scheduler()
